#include "overllm.h"
#include "tensor_ops.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <string>
#include <fstream>
#include <random>
#include <algorithm>

namespace overllm {

struct Linear {
    std::vector<float> weight;
    std::vector<float> bias;
    int in_features, out_features;
    Linear(int in_f, int out_f) : in_features(in_f), out_features(out_f) {
        weight.resize(in_f * out_f);
        bias.resize(out_f);
        float scale = std::sqrt(2.0f / (in_f + out_f));
        std::mt19937 gen(42 + in_f * 1000 + out_f);
        std::normal_distribution<float> d(0.0f, scale);
        for (auto& w : weight) w = d(gen);
        for (auto& b : bias) b = 0.0f;
    }
};

struct Attention {
    int n_heads, d_model, d_head;
    Linear Wq, Wk, Wv, Wo;
    Attention(int dm, int nh) : n_heads(nh), d_model(dm), d_head(dm/nh),
        Wq(dm,dm), Wk(dm,dm), Wv(dm,dm), Wo(dm,dm) {}
};

struct FFN {
    Linear W1, W2;
    std::vector<float> hidden;
    FFN(int d_model, int d_ff) : W1(d_model, d_ff), W2(d_ff, d_model) {}
};

struct TransformerBlock {
    Attention attn;
    FFN ffn;
    std::vector<float> ln1_gamma, ln1_beta, ln2_gamma, ln2_beta;
    std::vector<float> attn_out, ffn_out, residual1, residual2;
    TransformerBlock(int d_model, int n_heads, int d_ff)
        : attn(d_model, n_heads), ffn(d_model, d_ff) {
        ln1_gamma.resize(d_model, 1.0f); ln1_beta.resize(d_model, 0.0f);
        ln2_gamma.resize(d_model, 1.0f); ln2_beta.resize(d_model, 0.0f);
    }
};

struct Model {
    OverLLMConfig config;
    std::vector<float> embedding, pos_embedding;
    std::vector<TransformerBlock> blocks;
    Linear output_proj;
    std::vector<float> ln_final_gamma, ln_final_beta;
    std::vector<float> grad_embedding, grad_pos_embedding;
    int t_step = 0;

    Model(const OverLLMConfig& cfg) : config(cfg), output_proj(cfg.d_model, cfg.vocab_size) {
        embedding.resize(cfg.vocab_size * cfg.d_model);
        pos_embedding.resize(cfg.max_seq_len * cfg.d_model);
        float emb_scale = 1.0f / std::sqrt(cfg.d_model);
        std::mt19937 gen(42);
        std::normal_distribution<float> d(0.0f, emb_scale);
        for (auto& e : embedding) e = d(gen);
        for (auto& e : pos_embedding) e = d(gen);
        for (int i = 0; i < cfg.n_layers; ++i) blocks.emplace_back(cfg.d_model, cfg.n_heads, cfg.d_ff);
        ln_final_gamma.resize(cfg.d_model, 1.0f); ln_final_beta.resize(cfg.d_model, 0.0f);
        grad_embedding.resize(embedding.size(), 0.0f);
        grad_pos_embedding.resize(pos_embedding.size(), 0.0f);
    }
};

static void forward_impl(Model* m, const int* tokens, int n_tokens, float* out_logits) {
    const auto& cfg = m->config;
    int d = cfg.d_model, seq = n_tokens;
    std::vector<float> x(seq * d);
    for (int t = 0; t < seq; ++t)
        for (int j = 0; j < d; ++j)
            x[t*d+j] = m->embedding[tokens[t]*d+j] + m->pos_embedding[t*d+j];

    for (auto& blk : m->blocks) {
        blk.attn_out.resize(seq*d); blk.ffn_out.resize(seq*d);
        blk.residual1.resize(seq*d); blk.residual2.resize(seq*d);
        blk.ffn.hidden.resize(seq*cfg.d_ff);

        std::vector<float> q(seq*d), k_(seq*d), v_(seq*d);
        matmul(x.data(), blk.attn.Wq.weight.data(), q.data(), seq, d, d);
        add_bias(q.data(), blk.attn.Wq.bias.data(), seq, d);
        matmul(x.data(), blk.attn.Wk.weight.data(), k_.data(), seq, d, d);
        add_bias(k_.data(), blk.attn.Wk.bias.data(), seq, d);
        matmul(x.data(), blk.attn.Wv.weight.data(), v_.data(), seq, d, d);
        add_bias(v_.data(), blk.attn.Wv.bias.data(), seq, d);

        std::vector<float> attn_out(seq*d, 0.0f);
        int dh = blk.attn.d_head, nh = blk.attn.n_heads;
        float scale = 1.0f / std::sqrt((float)dh);
        for (int h = 0; h < nh; ++h) {
            for (int i = 0; i < seq; ++i) {
                std::vector<float> scores(seq, 0.0f);
                for (int j = 0; j <= i; ++j) {
                    float dot = 0.0f;
                    for (int k = 0; k < dh; ++k) {
                        dot += q[i*d + h*dh + k] * k_[j*d + h*dh + k];
                    }
                    scores[j] = dot * scale;
                }
                float maxs = scores[0];
                for (int j = 1; j <= i; ++j) if (scores[j] > maxs) maxs = scores[j];
                float sum_exp = 0.0f;
                for (int j = 0; j <= i; ++j) { scores[j] = std::exp(scores[j]-maxs); sum_exp += scores[j]; }
                for (int j = 0; j <= i; ++j) scores[j] /= sum_exp;
                for (int j = i+1; j < seq; ++j) scores[j] = 0.0f;
                for (int k = 0; k < dh; ++k) {
                    float val = 0.0f;
                    for (int j = 0; j < seq; ++j) val += scores[j] * v_[j*d + h*dh + k];
                    attn_out[i*d + h*dh + k] = val;
                }
            }
        }
        matmul(attn_out.data(), blk.attn.Wo.weight.data(), blk.attn_out.data(), seq, d, d);
        add_bias(blk.attn_out.data(), blk.attn.Wo.bias.data(), seq, d);
        for (int i = 0; i < seq*d; ++i) blk.residual1[i] = x[i];
        add(x.data(), blk.attn_out.data(), x.data(), seq*d);
        layer_norm(x.data(), x.data(), blk.ln1_gamma.data(), blk.ln1_beta.data(), seq, d, 1e-5f);

        matmul(x.data(), blk.ffn.W1.weight.data(), blk.ffn.hidden.data(), seq, cfg.d_ff, d);
        add_bias(blk.ffn.hidden.data(), blk.ffn.W1.bias.data(), seq, cfg.d_ff);
        gelu(blk.ffn.hidden.data(), blk.ffn.hidden.data(), seq*cfg.d_ff);
        matmul(blk.ffn.hidden.data(), blk.ffn.W2.weight.data(), blk.ffn_out.data(), seq, d, cfg.d_ff);
        add_bias(blk.ffn_out.data(), blk.ffn.W2.bias.data(), seq, d);
        for (int i = 0; i < seq*d; ++i) blk.residual2[i] = x[i];
        add(x.data(), blk.ffn_out.data(), x.data(), seq*d);
        layer_norm(x.data(), x.data(), blk.ln2_gamma.data(), blk.ln2_beta.data(), seq, d, 1e-5f);
    }
    layer_norm(x.data(), x.data(), m->ln_final_gamma.data(), m->ln_final_beta.data(), seq, d, 1e-5f);
    matmul(x.data() + (seq-1)*d, m->output_proj.weight.data(), out_logits, 1, cfg.vocab_size, d);
    add_bias(out_logits, m->output_proj.bias.data(), 1, cfg.vocab_size);
}

} // namespace overllm

using namespace overllm;

extern "C" {

OverLLMConfig overllm_default_config(void) {
    OverLLMConfig cfg = {32000, 256, 4, 4, 512, 512, 0.8f};
    return cfg;
}

OverLLMModel* overllm_load_model(const char* weights_path, const OverLLMConfig* config) {
    Model* m = new Model(*config);
    if (weights_path && std::strlen(weights_path) > 0) {
        std::ifstream f(weights_path, std::ios::binary);
        if (f.is_open()) {
            auto readf = [&](std::vector<float>& v) { f.read((char*)v.data(), v.size()*sizeof(float)); };
            readf(m->embedding); readf(m->pos_embedding);
            for (auto& blk : m->blocks) {
                readf(blk.attn.Wq.weight); readf(blk.attn.Wq.bias);
                readf(blk.attn.Wk.weight); readf(blk.attn.Wk.bias);
                readf(blk.attn.Wv.weight); readf(blk.attn.Wv.bias);
                readf(blk.attn.Wo.weight); readf(blk.attn.Wo.bias);
                readf(blk.ffn.W1.weight); readf(blk.ffn.W1.bias);
                readf(blk.ffn.W2.weight); readf(blk.ffn.W2.bias);
                readf(blk.ln1_gamma); readf(blk.ln1_beta);
                readf(blk.ln2_gamma); readf(blk.ln2_beta);
            }
            readf(m->ln_final_gamma); readf(m->ln_final_beta);
            readf(m->output_proj.weight); readf(m->output_proj.bias);
            f.close();
        }
    }
    return (OverLLMModel*)m;
}

void overllm_free_model(OverLLMModel* model) { delete (Model*)model; }

int overllm_forward(OverLLMModel* model, const int* tokens, int n_tokens, float* logits) {
    Model* m = (Model*)model;
    if (n_tokens > m->config.max_seq_len) n_tokens = m->config.max_seq_len;
    forward_impl(m, tokens, n_tokens, logits);
    return 0;
}

int overllm_sample_argmax(const float* logits, int vocab_size) { return argmax(logits, vocab_size); }
int overllm_sample_temperature(const float* logits, int vocab_size, float temp) {
    return sample_temperature(logits, vocab_size, temp, (unsigned)std::rand());
}

float overllm_dpo_step(OverLLMModel* model,
                       const int* chosen_tokens, int chosen_len,
                       const int* rejected_tokens, int rejected_len,
                       float beta) {
    Model* m = (Model*)model;
    int vs = m->config.vocab_size;
    std::vector<float> chosen_logits(vs), rejected_logits(vs);
    overllm_forward(model, chosen_tokens, chosen_len, chosen_logits.data());
    overllm_forward(model, rejected_tokens, rejected_len, rejected_logits.data());

    float c_max = chosen_logits[0], r_max = rejected_logits[0];
    for (int i = 1; i < vs; ++i) {
        if (chosen_logits[i] > c_max) c_max = chosen_logits[i];
        if (rejected_logits[i] > r_max) r_max = rejected_logits[i];
    }
    float c_sum = 0.0f, r_sum = 0.0f;
    for (int i = 0; i < vs; ++i) {
        c_sum += std::exp(chosen_logits[i] - c_max);
        r_sum += std::exp(rejected_logits[i] - r_max);
    }
    float c_lse = c_max + std::log(c_sum);
    float r_lse = r_max + std::log(r_sum);
    int c_target = chosen_tokens[chosen_len - 1];
    int r_target = rejected_tokens[rejected_len - 1];
    float logpi_chosen = chosen_logits[c_target] - c_lse;
    float logpi_rejected = rejected_logits[r_target] - r_lse;
    float margin = beta * (logpi_chosen - logpi_rejected);
    float sigmoid = 1.0f / (1.0f + std::exp(-margin));
    float loss = -std::log(sigmoid + 1e-10f);
    float dloss = -beta * (1.0f - sigmoid);
    std::vector<float> dlogits_c(vs, 0.0f), dlogits_r(vs, 0.0f);
    for (int i = 0; i < vs; ++i) {
        dlogits_c[i] = dloss * std::exp(chosen_logits[i] - c_lse);
        dlogits_r[i] = -dloss * std::exp(rejected_logits[i] - r_lse);
    }
    dlogits_c[c_target] -= dloss;
    dlogits_r[r_target] += dloss;
    for (int i = 0; i < vs; ++i) m->output_proj.bias[i] += 0.001f * (dlogits_c[i] + dlogits_r[i]);
    return loss;
}

void overllm_adamw_step(OverLLMModel* model, float lr, float beta1, float beta2, float eps, float weight_decay) {
    (void)model; (void)lr; (void)beta1; (void)beta2; (void)eps; (void)weight_decay;
}
void overllm_zero_grad(OverLLMModel* model) {
    Model* m = (Model*)model;
    std::fill(m->grad_embedding.begin(), m->grad_embedding.end(), 0.0f);
    std::fill(m->grad_pos_embedding.begin(), m->grad_pos_embedding.end(), 0.0f);
}
int overllm_save_weights(OverLLMModel* model, const char* path) {
    Model* m = (Model*)model;
    std::ofstream f(path, std::ios::binary);
    if (!f.is_open()) return -1;
    auto writef = [&](std::vector<float>& v) { f.write((char*)v.data(), v.size()*sizeof(float)); };
    writef(m->embedding); writef(m->pos_embedding);
    for (auto& blk : m->blocks) {
        writef(blk.attn.Wq.weight); writef(blk.attn.Wq.bias);
        writef(blk.attn.Wk.weight); writef(blk.attn.Wk.bias);
        writef(blk.attn.Wv.weight); writef(blk.attn.Wv.bias);
        writef(blk.attn.Wo.weight); writef(blk.attn.Wo.bias);
        writef(blk.ffn.W1.weight); writef(blk.ffn.W1.bias);
        writef(blk.ffn.W2.weight); writef(blk.ffn.W2.bias);
        writef(blk.ln1_gamma); writef(blk.ln1_beta);
        writef(blk.ln2_gamma); writef(blk.ln2_beta);
    }
    writef(m->ln_final_gamma); writef(m->ln_final_beta);
    writef(m->output_proj.weight); writef(m->output_proj.bias);
    f.close();
    return 0;
}

float overllm_get_action_prob(OverLLMModel* model, const int* tokens, int n_tokens, int action) {
    Model* m = (Model*)model;
    int vs = m->config.vocab_size;
    std::vector<float> logits(vs);
    overllm_forward(model, tokens, n_tokens, logits.data());
    
    float max_logit = logits[0];
    for (int i = 1; i < vs; ++i) if (logits[i] > max_logit) max_logit = logits[i];
    float sum_exp = 0.0f;
    for (int i = 0; i < vs; ++i) sum_exp += std::exp(logits[i] - max_logit);
    float prob = std::exp(logits[action] - max_logit) / sum_exp;
    return prob;
}

void overllm_set_epsilon(OverLLMModel* model, float epsilon) {
    (void)model; (void)epsilon;
    // Epsilon is managed in Rust/Go layer
}

float overllm_rl_step(OverLLMModel* model,
                      const int* state_tokens, int state_len,
                      int action, float reward,
                      const int* next_state_tokens, int next_state_len,
                      float gamma, float lr) {
    Model* m = (Model*)model;
    int vs = m->config.vocab_size;
    
    // Get action probability for state
    float state_prob = overllm_get_action_prob(model, state_tokens, state_len, action);
    
    // Get max Q-value for next state (simplified - use argmax)
    std::vector<float> next_logits(vs);
    overllm_forward(model, next_state_tokens, next_state_len, next_logits.data());
    int next_action = argmax(next_logits.data(), vs);
    float next_prob = overllm_get_action_prob(model, next_state_tokens, next_state_len, next_action);
    
    // TD error: reward + gamma * next_value - current_value
    float td_error = reward + gamma * next_prob - state_prob;
    
    // Update output layer bias (simplified policy gradient)
    std::vector<float> state_logits(vs);
    overllm_forward(model, state_tokens, state_len, state_logits.data());
    for (int i = 0; i < vs; ++i) {
        float grad = (i == action ? 1.0f : 0.0f) - std::exp(state_logits[i]);
        m->output_proj.bias[i] += lr * td_error * grad * 0.01f;
    }
    
    return td_error;
}

int overllm_load_vector_index(OverLLMModel* model, const char* path) {
    (void)model; (void)path;
    // Vector index is managed in Rust layer
    return 0;
}

} // extern "C"
