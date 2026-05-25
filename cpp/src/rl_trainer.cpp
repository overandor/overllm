#include "overllm.h"
#include <cmath>
#include <vector>
#include <algorithm>
#include <random>
#include <queue>

namespace overllm {

struct Experience {
    std::vector<int> state_tokens;
    int action;
    float reward;
    std::vector<int> next_state_tokens;
    bool done;
};

struct RLTrainer {
    std::queue<Experience> replay_buffer;
    int buffer_size;
    float gamma;
    float learning_rate;
    int batch_size;
    int total_steps;
    float epsilon;
    float epsilon_min;
    float epsilon_decay;
    
    RLTrainer(int buf_size = 10000, float lr = 0.001f, float eps = 0.1f)
        : buffer_size(buf_size), gamma(0.99f), learning_rate(lr), 
          batch_size(32), total_steps(0), epsilon(eps), 
          epsilon_min(0.01f), epsilon_decay(0.995f) {}
    
    void add_experience(const Experience& exp) {
        if (replay_buffer.size() >= buffer_size) {
            replay_buffer.pop();
        }
        replay_buffer.push(exp);
        total_steps++;
    }
    
    float compute_td_error(float current_value, float reward, float next_value, bool done) {
        if (done) {
            return reward - current_value;
        }
        return reward + gamma * next_value - current_value;
    }
    
    void update_epsilon() {
        epsilon *= epsilon_decay;
        epsilon = std::max(epsilon_min, epsilon);
    }
    
    bool should_explore() {
        return (float)rand() / RAND_MAX < epsilon;
    }
    
    float get_mistake_penalty(const std::vector<int>& tokens, int action, int correct_action) {
        // Penalize based on how wrong the action was
        if (action == correct_action) return 0.0f;
        return -1.0f; // Base penalty for wrong action
    }
    
    float compute_reward(const std::vector<int>& tokens, int action, 
                        const std::vector<int>& reference_tokens) {
        // Reward based on token selection quality
        float reward = 0.0f;
        
        // Check if action matches reference
        if (!reference_tokens.empty() && action == reference_tokens.back()) {
            reward += 1.0f;
        }
        
        // Penalize rare/unk tokens
        if (action < 10) { // Assuming low IDs are special tokens
            reward -= 0.5f;
        }
        
        return reward;
    }
    
    std::vector<Experience> sample_batch() {
        std::vector<Experience> batch;
        int n = std::min(batch_size, (int)replay_buffer.size());
        
        // Simple random sampling (in production, use proper reservoir sampling)
        std::vector<Experience> temp;
        while (!replay_buffer.empty()) {
            temp.push_back(replay_buffer.front());
            replay_buffer.pop();
        }
        
        std::random_shuffle(temp.begin(), temp.end());
        for (int i = 0; i < n; ++i) {
            batch.push_back(temp[i]);
        }
        
        // Put back remaining
        for (const auto& exp : temp) {
            replay_buffer.push(exp);
        }
        
        return batch;
    }
    
    float train_step(OverLLMModel* model, const std::vector<Experience>& batch) {
        float total_loss = 0.0f;
        
        for (const auto& exp : batch) {
            float td_error = overllm_rl_step(
                model,
                exp.state_tokens.data(), exp.state_tokens.size(),
                exp.action, exp.reward,
                exp.next_state_tokens.data(), exp.next_state_tokens.size(),
                gamma, learning_rate
            );
            total_loss += std::abs(td_error);
        }
        
        return total_loss / std::max((int)batch.size(), 1);
    }
};

} // namespace overllm
