#ifndef TOKENIZER_H
#define TOKENIZER_H

#include <string>
#include <vector>
#include <unordered_map>

namespace overllm {

// Real byte-level BPE (the algorithm GPT-2/3.5/4, Llama, and other
// production tokenizers use): base vocabulary is the 256 possible raw
// bytes, and encoding applies a learned, ranked sequence of adjacent-symbol
// merges. This is OverLLM's own tokenizer, trained on OverLLM's own text
// (see tools/bpe_tokenizer.py, the Python trainer and reference
// implementation this class mirrors byte-for-byte). Vocabulary and merges
// are loaded from data files (vocab.txt, merges.txt), not hardcoded, so
// retraining tools/bpe_tokenizer.py and re-running load() picks up a new
// model without touching this code.
class BPETokenizer {
public:
    BPETokenizer();
    ~BPETokenizer();

    // Load vocab.txt + merges.txt from a directory (as produced by
    // tools/bpe_tokenizer.py's `train` command).
    bool load(const std::string& tokenizer_data_dir);

    // Load vocabulary from default locations.
    bool load_default();

    // Encode text to token IDs.
    std::vector<int> encode(const std::string& text) const;

    // Decode token IDs back to text (exact round-trip for any input, since
    // the base vocabulary covers all 256 byte values).
    std::string decode(const std::vector<int>& tokens) const;

    // Get vocabulary size.
    int get_vocab_size() const;

    // Get token string by ID.
    std::string get_token(int id) const;

    // Get token ID by string.
    int get_id(const std::string& token) const;

private:
    std::unordered_map<std::string, int> vocab_;
    std::unordered_map<int, std::string> inverse_vocab_;
    std::unordered_map<std::string, int> merge_rank_;  // "left\x1fright" -> rank
    int vocab_size_;
    bool loaded_;

    std::vector<std::string> pretokenize(const std::string& text) const;
    std::vector<std::string> word_to_byte_symbols(const std::string& word) const;
    std::vector<std::string> apply_merges(std::vector<std::string> symbols) const;
};

} // namespace overllm

#endif // TOKENIZER_H
