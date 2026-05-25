#include "tokenizer.h"
#include <fstream>
#include <sstream>
#include <algorithm>
#include <unordered_map>
#include <iostream>

namespace overllm {

BPETokenizer::BPETokenizer() : vocab_size_(0) {}

BPETokenizer::~BPETokenizer() {}

bool BPETokenizer::load(const std::string& vocab_path) {
    std::ifstream f(vocab_path);
    if (!f.is_open()) {
        std::cerr << "Failed to open vocab file: " << vocab_path << std::endl;
        return false;
    }
    
    std::string line;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        
        // Parse line: format could be "token id" or just "token"
        std::istringstream iss(line);
        std::string token;
        int id = vocab_size_;
        
        iss >> token;
        if (iss >> id) {
            // Format: "token id"
        } else {
            // Format: just token, use current vocab_size_ as id
            id = vocab_size_;
        }
        
        vocab_[token] = id;
        inverse_vocab_[id] = token;
        vocab_size_ = std::max(vocab_size_, id + 1);
    }
    
    std::cout << "Loaded " << vocab_size_ << " tokens from " << vocab_path << std::endl;
    return true;
}

std::vector<int> BPETokenizer::encode(const std::string& text) {
    std::vector<int> tokens;
    
    // Simple character-level encoding as fallback
    // In a full implementation, this would use BPE merge rules
    for (char c : text) {
        std::string token_str(1, c);
        auto it = vocab_.find(token_str);
        if (it != vocab_.end()) {
            tokens.push_back(it->second);
        } else {
            // Use unknown token (0)
            tokens.push_back(0);
        }
    }
    
    return tokens;
}

std::string BPETokenizer::decode(const std::vector<int>& tokens) {
    std::string result;
    
    for (int token_id : tokens) {
        auto it = inverse_vocab_.find(token_id);
        if (it != inverse_vocab_.end()) {
            result += it->second;
        } else {
            result += "<UNK>";
        }
    }
    
    return result;
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
    return 0;  // Unknown token
}

} // namespace overllm
