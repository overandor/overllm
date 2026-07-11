#include "overllm.h"
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>
#include <fstream>

static std::vector<std::string> vocab;

static std::vector<int> encode(const std::string& text) {
    std::vector<int> tokens;
    std::string cur;
    for (char c : text) {
        if (c == ' ' || c == '\n' || c == '\t' || c == '.' || c == ',' || c == '!' || c == '?') {
            if (!cur.empty()) {
                auto it = std::find(vocab.begin(), vocab.end(), cur);
                tokens.push_back(it != vocab.end() ? it - vocab.begin() : 1);
                cur.clear();
            }
            std::string punct(1, c);
            auto it = std::find(vocab.begin(), vocab.end(), punct);
            if (it != vocab.end()) tokens.push_back(it - vocab.begin());
        } else {
            cur += c;
        }
    }
    if (!cur.empty()) {
        auto it = std::find(vocab.begin(), vocab.end(), cur);
        tokens.push_back(it != vocab.end() ? it - vocab.begin() : 1);
    }
    return tokens;
}

static void load_vocab(const char* path) {
    vocab.clear();
    vocab.push_back("<pad>"); vocab.push_back("<unk>"); vocab.push_back("<s>"); vocab.push_back("</s>");
    std::ifstream f(path);
    std::string word;
    while (f >> word) {
        if (std::find(vocab.begin(), vocab.end(), word) == vocab.end()) vocab.push_back(word);
    }
    printf("Loaded vocab: %zu tokens\n", vocab.size());
}

int main(int argc, char** argv) {
    if (argc < 3) {
        printf("Usage: %s <vocab.txt> <weights.bin> [prompt]\n", argv[0]);
        return 1;
    }
    load_vocab(argv[1]);
    OverLLMConfig cfg = overllm_default_config();
    cfg.vocab_size = (int)vocab.size();
    OverLLMModel* model = overllm_load_model(argv[2], &cfg);
    if (!model) { printf("Failed to load model\n"); return 1; }
    std::string prompt = argc > 3 ? argv[3] : "hello world";
    std::vector<int> tokens = encode(prompt);
    printf("Prompt: %s\nGenerating...\n", prompt.c_str());
    for (int i = 0; i < 50; ++i) {
        if (tokens.size() > (size_t)cfg.max_seq_len) tokens.erase(tokens.begin());
        std::vector<float> logits(cfg.vocab_size);
        overllm_forward(model, tokens.data(), (int)tokens.size(), logits.data());
        int next = overllm_sample_temperature(logits.data(), cfg.vocab_size, cfg.temperature);
        if (next == 3) break;
        tokens.push_back(next);
        printf("%s ", vocab[next].c_str());
        fflush(stdout);
    }
    printf("\n");
    overllm_free_model(model);
    return 0;
}
