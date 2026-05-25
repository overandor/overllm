#pragma once
#include <cstddef>
#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    int vocab_size;
    int d_model;
    int n_heads;
    int n_layers;
    int d_ff;
    int max_seq_len;
    float temperature;
} OverLLMConfig;

typedef struct OverLLMModel OverLLMModel;

// Lifecycle
OverLLMModel* overllm_load_model(const char* weights_path, const OverLLMConfig* config);
void overllm_free_model(OverLLMModel* model);

// Inference
int overllm_forward(OverLLMModel* model, const int* tokens, int n_tokens, float* logits);
int overllm_backward(OverLLMModel* model, const int* tokens, int n_tokens, const float* dlogits);
int overllm_sample_argmax(const float* logits, int vocab_size);
int overllm_sample_temperature(const float* logits, int vocab_size, float temp);

// DPO Training
float overllm_dpo_step(OverLLMModel* model,
                       const int* chosen_tokens, int chosen_len,
                       const int* rejected_tokens, int rejected_len,
                       float beta);

// Reinforcement Learning (PPO/A2C)
float overllm_rl_step(OverLLMModel* model,
                      const int* state_tokens, int state_len,
                      int action, float reward,
                      const int* next_state_tokens, int next_state_len,
                      float gamma, float lr);
float overllm_get_action_prob(OverLLMModel* model, const int* tokens, int n_tokens, int action);
void overllm_set_epsilon(OverLLMModel* model, float epsilon);

// Optimizer
void overllm_adamw_step(OverLLMModel* model, float lr, float beta1, float beta2, float eps, float weight_decay);
void overllm_zero_grad(OverLLMModel* model);

// Weights
int overllm_save_weights(OverLLMModel* model, const char* path);
int overllm_load_vector_index(OverLLMModel* model, const char* path);

// Config
OverLLMConfig overllm_default_config(void);

#ifdef __cplusplus
}
#endif
