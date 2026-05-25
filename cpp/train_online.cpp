#include "overllm.h"
#include <iostream>
#include <vector>
#include <random>
#include <chrono>

// Simple online training loop using DPO
void train_dpo_online(OverLLMModel* model, int num_steps, float lr) {
    std::cout << "Starting online DPO training..." << std::endl;
    std::cout << "Steps: " << num_steps << ", LR: " << lr << std::endl;
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> token_dist(1, 100);
    std::uniform_int_distribution<> seq_len_dist(3, 10);
    
    float total_loss = 0.0f;
    
    for (int step = 0; step < num_steps; ++step) {
        // Generate random sequences
        int seq_len = seq_len_dist(gen);
        std::vector<int> chosen(seq_len);
        std::vector<int> rejected(seq_len);
        
        for (int i = 0; i < seq_len; ++i) {
            chosen[i] = token_dist(gen);
            rejected[i] = token_dist(gen);
        }
        // Make rejected different from chosen
        rejected[seq_len-1] = token_dist(gen);
        
        // DPO step
        float loss = overllm_dpo_step(model, chosen.data(), seq_len, 
                                      rejected.data(), seq_len, 0.1f);
        
        // AdamW update
        overllm_adamw_step(model, lr, 0.9f, 0.999f, 1e-8f, 0.01f);
        
        total_loss += loss;
        
        if (step % 100 == 0) {
            std::cout << "Step " << step << "/" << num_steps 
                      << " | Loss: " << loss 
                      << " | Avg Loss: " << total_loss / (step + 1) << std::endl;
        }
    }
    
    std::cout << "Training complete. Final avg loss: " << total_loss / num_steps << std::endl;
}

// Simple online training loop using RL
void train_rl_online(OverLLMModel* model, int num_steps, float lr) {
    std::cout << "Starting online RL training..." << std::endl;
    std::cout << "Steps: " << num_steps << ", LR: " << lr << std::endl;
    
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> token_dist(1, 100);
    std::uniform_int_distribution<> seq_len_dist(3, 10);
    std::uniform_real_distribution<> reward_dist(-1.0f, 1.0f);
    
    float total_td_error = 0.0f;
    
    for (int step = 0; step < num_steps; ++step) {
        // Generate random sequences
        int seq_len = seq_len_dist(gen);
        std::vector<int> state(seq_len);
        std::vector<int> next_state(seq_len);
        
        for (int i = 0; i < seq_len; ++i) {
            state[i] = token_dist(gen);
            next_state[i] = token_dist(gen);
        }
        
        int action = token_dist(gen);
        float reward = reward_dist(gen);
        
        // RL step
        float td_error = overllm_rl_step(model, state.data(), seq_len, action, reward,
                                        next_state.data(), seq_len, 0.99f, lr);
        
        // AdamW update
        overllm_adamw_step(model, lr, 0.9f, 0.999f, 1e-8f, 0.01f);
        
        total_td_error += td_error;
        
        if (step % 100 == 0) {
            std::cout << "Step " << step << "/" << num_steps 
                      << " | TD Error: " << td_error 
                      << " | Avg TD Error: " << total_td_error / (step + 1) << std::endl;
        }
    }
    
    std::cout << "Training complete. Final avg TD error: " << total_td_error / num_steps << std::endl;
}

// Generate text using the model
void generate_text(OverLLMModel* model, int max_tokens, float temperature) {
    std::cout << "Generating text..." << std::endl;
    
    std::vector<int> tokens = {1, 2, 3};  // Start with some tokens
    int vocab_size = 32000;
    
    for (int i = 0; i < max_tokens; ++i) {
        std::vector<float> logits(vocab_size);
        overllm_forward(model, tokens.data(), tokens.size(), logits.data());
        
        int next_token;
        if (temperature > 0.0f) {
            next_token = overllm_sample_temperature(logits.data(), vocab_size, temperature);
        } else {
            next_token = overllm_sample_argmax(logits.data(), vocab_size);
        }
        
        tokens.push_back(next_token);
        
        if (next_token == 0) break;  // EOS token
    }
    
    std::cout << "Generated " << tokens.size() << " tokens" << std::endl;
    std::cout << "Token sequence: ";
    for (size_t i = 0; i < std::min(tokens.size(), (size_t)20); ++i) {
        std::cout << tokens[i] << " ";
    }
    if (tokens.size() > 20) std::cout << "...";
    std::cout << std::endl;
}

int main() {
    std::cout << "========================================" << std::endl;
    std::cout << "  OverLLM Online Training" << std::endl;
    std::cout << "========================================" << std::endl;
    std::cout << std::endl;
    
    // Load model
    OverLLMConfig cfg = overllm_default_config();
    OverLLMModel* model = overllm_load_model(nullptr, &cfg);
    
    if (!model) {
        std::cout << "Failed to create model" << std::endl;
        return 1;
    }
    
    std::cout << "Model loaded successfully" << std::endl;
    std::cout << "Vocab size: " << cfg.vocab_size << std::endl;
    std::cout << "Model dim: " << cfg.d_model << std::endl;
    std::cout << "Layers: " << cfg.n_layers << std::endl;
    std::cout << std::endl;
    
    // Generate some text before training
    std::cout << "--- Before Training ---" << std::endl;
    generate_text(model, 10, 0.8f);
    std::cout << std::endl;
    
    // Train with DPO
    std::cout << "--- DPO Training ---" << std::endl;
    train_dpo_online(model, 500, 0.001f);
    std::cout << std::endl;
    
    // Generate text after DPO training
    std::cout << "--- After DPO Training ---" << std::endl;
    generate_text(model, 10, 0.8f);
    std::cout << std::endl;
    
    // Train with RL
    std::cout << "--- RL Training ---" << std::endl;
    train_rl_online(model, 500, 0.001f);
    std::cout << std::endl;
    
    // Generate text after RL training
    std::cout << "--- After RL Training ---" << std::endl;
    generate_text(model, 10, 0.8f);
    std::cout << std::endl;
    
    // Save trained weights
    const char* save_path = "/tmp/overllm_trained.bin";
    int save_result = overllm_save_weights(model, save_path);
    if (save_result == 0) {
        std::cout << "Model saved to " << save_path << std::endl;
    } else {
        std::cout << "Failed to save model" << std::endl;
    }
    
    overllm_free_model(model);
    
    std::cout << std::endl;
    std::cout << "Training complete!" << std::endl;
    
    return 0;
}
