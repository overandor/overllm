#include "tokenizer.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <iostream>
#include <cstdlib>

namespace overllm {

namespace {

// The standard GPT-2 byte<->printable-unicode mapping (public, well-known
// algorithm from OpenAI's gpt2 encoder.py), reimplemented here so the C++
// tokenizer can decode the same vocab.txt symbols tools/bpe_tokenizer.py
// writes. See that module's _bytes_to_unicode() for the Python original;
// this must produce byte-for-byte identical output for the two
// implementations to agree on the same trained vocabulary.
struct ByteUnicodeTable {
    std::string byte_to_symbol[256];      // byte value -> UTF-8 encoded symbol
    std::unordered_map<std::string, unsigned char> symbol_to_byte;

    static void append_utf8(std::string& out, int codepoint) {
        if (codepoint <= 0x7F) {
            out.push_back(static_cast<char>(codepoint));
        } else {
            out.push_back(static_cast<char>(0xC0 | ((codepoint >> 6) & 0x1F)));
            out.push_back(static_cast<char>(0x80 | (codepoint & 0x3F)));
        }
    }

    ByteUnicodeTable() {
        std::vector<int> bs;
        for (int b = static_cast<int>('!'); b <= static_cast<int>('~'); ++b) bs.push_back(b);
        for (int b = 0xA1; b <= 0xAC; ++b) bs.push_back(b);
        for (int b = 0xAE; b <= 0xFF; ++b) bs.push_back(b);

        std::vector<bool> in_bs(256, false);
        for (int b : bs) in_bs[b] = true;

        std::vector<int> cs = bs;
        int n = 0;
        std::vector<int> extra_bytes;
        for (int b = 0; b < 256; ++b) {
            if (!in_bs[b]) {
                bs.push_back(b);
                cs.push_back(256 + n);
                ++n;
            }
        }

        for (size_t i = 0; i < bs.size(); ++i) {
            std::string symbol;
            append_utf8(symbol, cs[i]);
            byte_to_symbol[bs[i]] = symbol;
            symbol_to_byte[symbol] = static_cast<unsigned char>(bs[i]);
        }
    }
};

const ByteUnicodeTable& byte_table() {
    static const ByteUnicodeTable table;
    return table;
}

// Splits a UTF-8 string into individual symbol strings, where each symbol
// matches one entry from byte_table() (1 or 2 UTF-8 bytes per symbol, since
// every codepoint in the table is <= 0x7FF).
std::vector<std::string> split_symbols(const std::string& text) {
    std::vector<std::string> symbols;
    size_t i = 0;
    while (i < text.size()) {
        unsigned char c = static_cast<unsigned char>(text[i]);
        size_t len = (c < 0x80) ? 1 : 2;  // table only emits 1- or 2-byte UTF-8
        if (i + len > text.size()) len = 1;
        symbols.push_back(text.substr(i, len));
        i += len;
    }
    return symbols;
}

const std::string kASCIIWhitespace = " \t\n\r\v\f";

bool is_ascii_ws(char c) {
    return kASCIIWhitespace.find(c) != std::string::npos;
}

}  // namespace

BPETokenizer::BPETokenizer() : vocab_size_(0), loaded_(false) {}

BPETokenizer::~BPETokenizer() {}

bool BPETokenizer::load_default() {
    std::vector<std::string> default_dirs = {
        "./cpp/tokenizer_data",
        "./tokenizer_data",
        "../cpp/tokenizer_data",
        "../../cpp/tokenizer_data",
        std::string(std::getenv("HOME") ? std::getenv("HOME") : "") + "/.overllm/tokenizer_data",
    };

    for (const auto& dir : default_dirs) {
        if (dir.empty()) continue;
        if (load(dir)) {
            std::cout << "Loaded BPE tokenizer from: " << dir << std::endl;
            return true;
        }
    }

    std::cerr << "Failed to load BPE tokenizer from any default location" << std::endl;
    return false;
}

bool BPETokenizer::load(const std::string& tokenizer_data_dir) {
    std::ifstream vocab_file(tokenizer_data_dir + "/vocab.txt");
    if (!vocab_file.is_open()) {
        std::cerr << "Failed to open vocab file: " << tokenizer_data_dir << "/vocab.txt" << std::endl;
        return false;
    }

    vocab_.clear();
    inverse_vocab_.clear();
    merge_rank_.clear();
    vocab_size_ = 0;

    std::string line;
    while (std::getline(vocab_file, line)) {
        if (line.empty()) continue;
        size_t tab_pos = line.find('\t');
        if (tab_pos == std::string::npos) continue;
        std::string symbol = line.substr(0, tab_pos);
        int id = std::stoi(line.substr(tab_pos + 1));
        vocab_[symbol] = id;
        inverse_vocab_[id] = symbol;
        vocab_size_ = std::max(vocab_size_, id + 1);
    }

    std::ifstream merges_file(tokenizer_data_dir + "/merges.txt");
    if (!merges_file.is_open()) {
        std::cerr << "Failed to open merges file: " << tokenizer_data_dir << "/merges.txt" << std::endl;
        return false;
    }

    int rank = 0;
    while (std::getline(merges_file, line)) {
        if (line.empty() || line[0] == '#') continue;
        size_t space_pos = line.find(' ');
        if (space_pos == std::string::npos) continue;
        std::string left = line.substr(0, space_pos);
        std::string right = line.substr(space_pos + 1);
        merge_rank_[left + "\x1f" + right] = rank++;
    }

    std::cout << "Loaded " << vocab_size_ << " tokens and " << rank << " merges from "
              << tokenizer_data_dir << std::endl;
    loaded_ = true;
    return true;
}

std::vector<std::string> BPETokenizer::pretokenize(const std::string& text) const {
    // Mirrors tools/bpe_tokenizer.py's pretokenize() exactly: whitespace
    // runs and (at-most-one-leading-space) non-whitespace runs, operating
    // on raw bytes. ASCII whitespace bytes never appear as UTF-8
    // continuation bytes, so plain byte scanning is safe here even though
    // this doesn't decode multi-byte codepoints.
    std::vector<std::string> words;
    size_t i = 0;
    size_t n = text.size();
    while (i < n) {
        if (is_ascii_ws(text[i])) {
            size_t j = i;
            while (j < n && is_ascii_ws(text[j])) ++j;
            if (j == n) {
                words.push_back(text.substr(i, j - i));
                i = j;
            } else {
                if (j - i > 1) {
                    words.push_back(text.substr(i, j - i - 1));
                }
                size_t k = j;
                while (k < n && !is_ascii_ws(text[k])) ++k;
                words.push_back(text.substr(j - 1, k - (j - 1)));
                i = k;
            }
        } else {
            size_t j = i;
            while (j < n && !is_ascii_ws(text[j])) ++j;
            words.push_back(text.substr(i, j - i));
            i = j;
        }
    }
    return words;
}

std::vector<std::string> BPETokenizer::word_to_byte_symbols(const std::string& word) const {
    std::vector<std::string> symbols;
    const auto& table = byte_table();
    for (unsigned char b : word) {
        symbols.push_back(table.byte_to_symbol[b]);
    }
    return symbols;
}

std::vector<std::string> BPETokenizer::apply_merges(std::vector<std::string> symbols) const {
    while (symbols.size() > 1) {
        int best_rank = -1;
        size_t best_index = 0;
        for (size_t i = 0; i + 1 < symbols.size(); ++i) {
            auto it = merge_rank_.find(symbols[i] + "\x1f" + symbols[i + 1]);
            if (it != merge_rank_.end()) {
                if (best_rank == -1 || it->second < best_rank) {
                    best_rank = it->second;
                    best_index = i;
                }
            }
        }
        if (best_rank == -1) break;

        std::vector<std::string> merged;
        merged.reserve(symbols.size() - 1);
        for (size_t i = 0; i < symbols.size();) {
            if (i == best_index) {
                merged.push_back(symbols[i] + symbols[i + 1]);
                i += 2;
            } else {
                merged.push_back(symbols[i]);
                i += 1;
            }
        }
        symbols = std::move(merged);
    }
    return symbols;
}

std::vector<int> BPETokenizer::encode(const std::string& text) const {
    std::vector<int> token_ids;
    for (const auto& word : pretokenize(text)) {
        auto symbols = apply_merges(word_to_byte_symbols(word));
        for (const auto& sym : symbols) {
            auto it = vocab_.find(sym);
            if (it != vocab_.end()) {
                token_ids.push_back(it->second);
            }
            // Every symbol from word_to_byte_symbols() is one of the 256
            // base-byte symbols or a merge of them, and every merge that
            // apply_merges() can produce was recorded in vocab_ at train
            // time, so a missing lookup here would indicate a corrupt
            // vocab/merges pair rather than an actually-unknown token.
        }
    }
    return token_ids;
}

std::string BPETokenizer::decode(const std::vector<int>& tokens) const {
    std::string symbol_concat;
    for (int token_id : tokens) {
        auto it = inverse_vocab_.find(token_id);
        if (it != inverse_vocab_.end()) {
            symbol_concat += it->second;
        }
    }

    std::string raw_bytes;
    const auto& table = byte_table();
    for (const auto& sym : split_symbols(symbol_concat)) {
        auto it = table.symbol_to_byte.find(sym);
        if (it != table.symbol_to_byte.end()) {
            raw_bytes.push_back(static_cast<char>(it->second));
        }
    }
    return raw_bytes;
}

int BPETokenizer::get_vocab_size() const {
    return vocab_size_;
}

std::string BPETokenizer::get_token(int id) const {
    auto it = inverse_vocab_.find(id);
    if (it != inverse_vocab_.end()) {
        return it->second;
    }
    return "<UNK>";
}

int BPETokenizer::get_id(const std::string& token) const {
    auto it = vocab_.find(token);
    if (it != vocab_.end()) {
        return it->second;
    }
    return 0;
}

} // namespace overllm
