#include "overllm.h"
#include <cmath>
#include <vector>
#include <algorithm>
#include <random>

namespace overllm {

struct TokenOptimizer {
    std::vector<float> token_confidence;
    std::vector<float> token_history;
    std::vector<int> token_selection_counts;
    float learning_rate;
    float exploration_rate;
    int vocab_size;
    
    TokenOptimizer(int vs, float lr = 0.01f, float eps = 0.1f) 
        : vocab_size(vs), learning_rate(lr), exploration_rate(eps) {
        token_confidence.resize(vs, 0.5f);
        token_history.resize(vs, 0.0f);
        token_selection_counts.resize(vs, 0);
    }
    
    void update_confidence(int token_id, float reward) {
        if (token_id < 0 || token_id >= vocab_size) return;
        
        // Update confidence using exponential moving average
        token_confidence[token_id] = (1.0f - learning_rate) * token_confidence[token_id] 
                                    + learning_rate * reward;
        token_history[token_id] = token_confidence[token_id];
        token_selection_counts[token_id]++;
    }
    
    int select_token(const float* logits, bool use_exploration = true) {
        // Apply confidence bias to logits
        std::vector<float> adjusted_logits(vocab_size);
        for (int i = 0; i < vocab_size; ++i) {
            adjusted_logits[i] = logits[i] + 2.0f * (token_confidence[i] - 0.5f);
        }
        
        if (use_exploration && (float)rand() / RAND_MAX < exploration_rate) {
            // Epsilon-greedy exploration
            return rand() % vocab_size;
        }
        
        // Select argmax from adjusted logits
        int best_token = 0;
        float max_logit = adjusted_logits[0];
        for (int i = 1; i < vocab_size; ++i) {
            if (adjusted_logits[i] > max_logit) {
                max_logit = adjusted_logits[i];
                best_token = i;
            }
        }
        return best_token;
    }
    
    void decay_exploration(float decay = 0.995f) {
        exploration_rate *= decay;
        exploration_rate = std::max(0.01f, exploration_rate);
    }
    
    float get_token_confidence(int token_id) const {
        if (token_id >= 0 && token_id < vocab_size) {
            return token_confidence[token_id];
        }
        return 0.5f;
    }
};

} // namespace overllm
