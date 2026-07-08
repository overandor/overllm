// Standalone CLI for OverLLM's C++ BPE tokenizer mirror.
//
// This is the actual compiled artifact tools/bpe_parity_check.py invokes as
// a subprocess to verify the C++ implementation (cpp/src/tokenizer.cpp)
// produces byte-for-byte identical token IDs to the Python reference
// implementation (tools/bpe_tokenizer.py) on the same input, using the same
// trained vocab.txt/merges.txt.
//
// Usage:
//   bpe_cli encode --vocab-dir DIR --text "some text"
//   bpe_cli decode --vocab-dir DIR --ids "1,2,3"

#include "tokenizer.h"

#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {

std::vector<int> parse_ids(const std::string& csv) {
    std::vector<int> ids;
    std::stringstream ss(csv);
    std::string item;
    while (std::getline(ss, item, ',')) {
        if (!item.empty()) ids.push_back(std::stoi(item));
    }
    return ids;
}

void print_json_ids(const std::vector<int>& ids) {
    std::cout << "[";
    for (size_t i = 0; i < ids.size(); ++i) {
        if (i) std::cout << ",";
        std::cout << ids[i];
    }
    std::cout << "]" << std::endl;
}

}  // namespace

int main(int argc, char** argv) {
    std::string command;
    std::string vocab_dir;
    std::string text;
    std::string ids_csv;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (i == 1) {
            command = arg;
        } else if (arg == "--vocab-dir" && i + 1 < argc) {
            vocab_dir = argv[++i];
        } else if (arg == "--text" && i + 1 < argc) {
            text = argv[++i];
        } else if (arg == "--ids" && i + 1 < argc) {
            ids_csv = argv[++i];
        }
    }

    if (command.empty() || vocab_dir.empty()) {
        std::cerr << "Usage: bpe_cli encode --vocab-dir DIR --text TEXT" << std::endl;
        std::cerr << "       bpe_cli decode --vocab-dir DIR --ids 1,2,3" << std::endl;
        return 1;
    }

    overllm::BPETokenizer tokenizer;
    if (!tokenizer.load(vocab_dir)) {
        std::cerr << "Failed to load tokenizer data from " << vocab_dir << std::endl;
        return 1;
    }

    if (command == "encode") {
        auto ids = tokenizer.encode(text);
        print_json_ids(ids);
    } else if (command == "decode") {
        auto ids = parse_ids(ids_csv);
        std::cout << tokenizer.decode(ids) << std::endl;
    } else {
        std::cerr << "Unknown command: " << command << std::endl;
        return 1;
    }

    return 0;
}
