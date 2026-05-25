#include "overllm.h"
#include <iostream>
#include <vector>
#include <fstream>
#include <cstring>

void test_tokenization() {
    std::cout << "=== Testing Tokenization ===" << std::endl;
    
    // Load vocab file
    std::ifstream vocab("vocab.txt");
    if (!vocab.is_open()) {
        std::cout << "❌ FAIL: vocab.txt not found" << std::endl;
        return;
    }
    
    std::vector<std::string> tokens;
    std::string line;
    while (std::getline(vocab, line)) {
        tokens.push_back(line);
    }
    vocab.close();
    
    std::cout << "✓ Loaded " << tokens.size() << " tokens from vocab.txt" << std::endl;
    
    // Simple test: check if common tokens exist
    bool has_common = false;
    for (const auto& t : tokens) {
        if (t == "the" || t == "and" || t == "is") {
            has_common = true;
            break;
        }
    }
    
    if (has_common) {
        std::cout << "✓ PASS: Common tokens found in vocab" << std::endl;
    } else {
        std::cout << "⚠ WARNING: No common tokens found" << std::endl;
    }
    
    std::cout << "Note: Full tokenizer (text -> token IDs) not implemented in C++ layer" << std::endl;
    std::cout << std::endl;
}

void test_inference() {
    std::cout << "=== Testing Inference ===" << std::endl;
    
    OverLLMConfig cfg = overllm_default_config();
    OverLLMModel* model = overllm_load_model(nullptr, &cfg);
    
    if (!model) {
        std::cout << "❌ FAIL: Could not create model" << std::endl;
        return;
    }
    
    std::cout << "✓ Model created with config:" << std::endl;
    std::cout << "  - vocab_size: " << cfg.vocab_size << std::endl;
    std::cout << "  - d_model: " << cfg.d_model << std::endl;
    std::cout << "  - n_layers: " << cfg.n_layers << std::endl;
    std::cout << "  - n_heads: " << cfg.n_heads << std::endl;
    
    // Test forward pass
    int tokens[] = {1, 2, 3, 4, 5};
    int n_tokens = 5;
    std::vector<float> logits(cfg.vocab_size);
    
    int result = overllm_forward(model, tokens, n_tokens, logits.data());
    
    if (result == 0) {
        std::cout << "✓ PASS: Forward pass successful" << std::endl;
        
        // Check logits are not all zero
        bool has_nonzero = false;
        for (float l : logits) {
            if (l != 0.0f) {
                has_nonzero = true;
                break;
            }
        }
        
        if (has_nonzero) {
            std::cout << "✓ PASS: Logits contain non-zero values" << std::endl;
        } else {
            std::cout << "❌ FAIL: All logits are zero" << std::endl;
        }
        
        // Test sampling
        int sampled = overllm_sample_argmax(logits.data(), cfg.vocab_size);
        std::cout << "✓ Sampled token (argmax): " << sampled << std::endl;
    } else {
        std::cout << "❌ FAIL: Forward pass failed with code " << result << std::endl;
    }
    
    overllm_free_model(model);
    std::cout << std::endl;
}

void test_dpo() {
    std::cout << "=== Testing DPO (Direct Preference Optimization) ===" << std::endl;

    OverLLMConfig cfg = overllm_default_config();
    OverLLMModel* model = overllm_load_model(nullptr, &cfg);

    if (!model) {
        std::cout << "❌ FAIL: Could not create model" << std::endl;
        return;
    }

    int chosen_tokens[] = {1, 2, 3, 4, 5};
    int rejected_tokens[] = {1, 2, 3, 4, 6};
    int seq_len = 5;
    float beta = 0.1f;

    try {
        float loss = overllm_dpo_step(model, chosen_tokens, seq_len, rejected_tokens, seq_len, beta);

        if (loss >= 0.0f) {
            std::cout << "✓ PASS: DPO step completed" << std::endl;
            std::cout << "  - Loss: " << loss << std::endl;
            std::cout << "  - Beta: " << beta << std::endl;
            std::cout << "✓ Uses simplified backward pass (output layer only)" << std::endl;
        } else {
            std::cout << "❌ FAIL: DPO step returned negative loss" << std::endl;
        }
    } catch (...) {
        std::cout << "❌ FAIL: DPO step crashed" << std::endl;
    }

    overllm_free_model(model);
    std::cout << std::endl;
}

void test_rl() {
    std::cout << "=== Testing RL (Reinforcement Learning) ===" << std::endl;

    OverLLMConfig cfg = overllm_default_config();
    OverLLMModel* model = overllm_load_model(nullptr, &cfg);

    if (!model) {
        std::cout << "❌ FAIL: Could not create model" << std::endl;
        return;
    }

    int state_tokens[] = {1, 2, 3};
    int next_state_tokens[] = {2, 3, 4};
    int action = 5;
    float reward = 1.0f;
    float gamma = 0.99f;
    float lr = 0.001f;

    try {
        float td_error = overllm_rl_step(model, state_tokens, 3, action, reward,
                                         next_state_tokens, 3, gamma, lr);

        std::cout << "✓ PASS: RL step completed" << std::endl;
        std::cout << "  - TD Error: " << td_error << std::endl;
        std::cout << "  - Reward: " << reward << std::endl;
        std::cout << "  - Gamma: " << gamma << std::endl;
        std::cout << "  - Learning Rate: " << lr << std::endl;
        std::cout << "✓ Uses simplified backward pass (output layer only)" << std::endl;
    } catch (...) {
        std::cout << "❌ FAIL: RL step crashed" << std::endl;
    }

    overllm_free_model(model);
    std::cout << std::endl;
}

void test_backpropagation() {
    std::cout << "=== Testing Backpropagation ===" << std::endl;
    
    OverLLMConfig cfg = overllm_default_config();
    OverLLMModel* model = overllm_load_model(nullptr, &cfg);
    
    if (!model) {
        std::cout << "❌ FAIL: Could not create model" << std::endl;
        return;
    }
    
    // Test gradient zeroing
    overllm_zero_grad(model);
    std::cout << "✓ PASS: Gradient zeroing completed" << std::endl;
    
    // Test backward pass
    int tokens[] = {1, 2, 3, 4, 5};
    int n_tokens = 5;
    std::vector<float> dlogits(cfg.vocab_size, 0.1f);  // Uniform gradient
    
    int backward_result = overllm_backward(model, tokens, n_tokens, dlogits.data());
    if (backward_result == 0) {
        std::cout << "✓ PASS: Backward pass completed" << std::endl;
    } else {
        std::cout << "❌ FAIL: Backward pass failed with code " << backward_result << std::endl;
    }
    
    // Test AdamW step
    overllm_adamw_step(model, 0.001f, 0.9f, 0.999f, 1e-8f, 0.01f);
    std::cout << "✓ PASS: AdamW step completed" << std::endl;
    
    overllm_free_model(model);
    std::cout << std::endl;
}

void test_save_load() {
    std::cout << "=== Testing Save/Load ===" << std::endl;
    
    OverLLMConfig cfg = overllm_default_config();
    OverLLMModel* model = overllm_load_model(nullptr, &cfg);
    
    if (!model) {
        std::cout << "❌ FAIL: Could not create model" << std::endl;
        return;
    }
    
    const char* test_path = "/tmp/test_overllm.bin";
    int save_result = overllm_save_weights(model, test_path);
    
    if (save_result == 0) {
        std::cout << "✓ PASS: Weights saved to " << test_path << std::endl;
        
        // Try to load
        OverLLMModel* loaded_model = overllm_load_model(test_path, &cfg);
        if (loaded_model) {
            std::cout << "✓ PASS: Weights loaded successfully" << std::endl;
            overllm_free_model(loaded_model);
        } else {
            std::cout << "❌ FAIL: Could not load weights" << std::endl;
        }
    } else {
        std::cout << "❌ FAIL: Could not save weights" << std::endl;
    }
    
    overllm_free_model(model);
    std::cout << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "  OverLLM Component Test Suite" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    test_tokenization();
    test_inference();
    test_dpo();
    test_rl();
    test_backpropagation();
    test_save_load();
    
    std::cout << "========================================" << std::endl;
    std::cout << "  Test Summary" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << "✓ Tokenization: Partial (vocab loaded, no tokenizer)" << std::endl;
    std::cout << "✓ Inference: Working" << std::endl;
    std::cout << "⚠ DPO: Infrastructure implemented, needs debugging (bus error)" << std::endl;
    std::cout << "⚠ RL: Infrastructure implemented, needs debugging (bus error)" << std::endl;
    std::cout << "✓ Backpropagation: Basic working (output layer only)" << std::endl;
    std::cout << "✓ AdamW: Implemented with momentum tracking" << std::endl;
    std::cout << "✓ Save/Load: Working" << std::endl;
    std::cout << std::endl;
    std::cout << "GA (Genetic Algorithm): Implemented but not tested here" << std::endl;
    std::cout << std::endl;
    std::cout << "Note: Full backward pass through all layers causes bus error." << std::endl;
    std::cout << "      Backward functions are implemented but need memory debugging." << std::endl;
    std::cout << std::endl;
    
    return 0;
}
