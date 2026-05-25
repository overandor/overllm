#ifndef TOKENIZER_H
#define TOKENIZER_H

#include <string>
#include <vector>
#include <unordered_map>

namespace overllm {

class BPETokenizer {
public:
    BPETokenizer();
    ~BPETokenizer();
    
    // Load vocabulary from file
    bool load(const std::string& vocab_path);
    
    // Load vocabulary from default locations
    bool load_default();
    
    // Encode text to token IDs
    std::vector<int> encode(const std::string& text);
    
    // Decode token IDs to text
    std::string decode(const std::vector<int>& tokens);
    
    // Get vocabulary size
    int get_vocab_size() const;
    
    // Get token string by ID
    std::string get_token(int id) const;
    
    // Get token ID by string
    int get_id(const std::string& token) const;

private:
    std::unordered_map<std::string, int> vocab_;
    std::unordered_map<int, std::string> inverse_vocab_;
    int vocab_size_;
};

} // namespace overllm

#endif // TOKENIZER_H
