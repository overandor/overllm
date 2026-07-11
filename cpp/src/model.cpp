#include "model_internal.h"
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

Linear::Linear(int in_f, int out_f) : in_features(in_f), out_features(out_f) {
    weight.resize(in_f * out_f);
    bias.resize(out_f);
    grad_weight.resize(in_f * out_f, 0.0f);
    grad_bias.resize(out_f, 0.0f);
    m_weight.resize(in_f * out_f, 0.0f);
    v_weight.resize(in_f * out_f, 0.0f);
    m_bias.resize(out_f, 0.0f);
    v_bias.resize(out_f, 0.0f);
    float scale = std::sqrt(2.0f / (in_f + out_f));
    std::mt19937 gen(42 + in_f * 1000 + out_f);
    std::normal_distribution<float> d(0.0f, scale);
    for (auto& w : weight) w = d(gen);
    for (auto& b : bias) b = 0.0f;
}

TransformerBlock::TransformerBlock(int d_model, int n_heads, int d_ff)
    : attn(d_model, n_heads), ffn(d_model, d_ff) {
    ln1_gamma.resize(d_model, 1.0f); ln1_beta.resize(d_model, 0.0f);
    ln2_gamma.resize(d_model, 1.0f); ln2_beta.resize(d_model, 0.0f);
    grad_ln1_gamma.resize(d_model, 0.0f); grad_ln1_beta.resize(d_model, 0.0f);
    grad_ln2_gamma.resize(d_model, 0.0f); grad_ln2_beta.resize(d_model, 0.0f);
    m_ln1_gamma.resize(d_model, 0.0f); v_ln1_gamma.resize(d_model, 0.0f);
    m_ln1_beta.resize(d_model, 0.0f); v_ln1_beta.resize(d_model, 0.0f);
    m_ln2_gamma.resize(d_model, 0.0f); v_ln2_gamma.resize(d_model, 0.0f);
    m_ln2_beta.resize(d_model, 0.0f); v_ln2_beta.resize(d_model, 0.0f);
}

Model::Model(const OverLLMConfig& cfg) : config(cfg), output_proj(cfg.d_model, cfg.vocab_size) {
    embedding.resize(cfg.vocab_size * cfg.d_model);
    pos_embedding.resize(cfg.max_seq_len * cfg.d_model);
    float emb_scale = 1.0f / std::sqrt(cfg.d_model);
    std::mt19937 gen(42);
    std::normal_distribution<float> d(0.0f, emb_scale);
    for (auto& e : embedding) e = d(gen);
    for (auto& e : pos_embedding) e = d(gen);
    for (int i = 0; i < cfg.n_layers; ++i) blocks.emplace_back(cfg.d_model, cfg.n_heads, cfg.d_ff);
    ln_final_gamma.resize(cfg.d_model, 1.0f); ln_final_beta.resize(cfg.d_model, 0.0f);
    grad_ln_final_gamma.resize(cfg.d_model, 0.0f); grad_ln_final_beta.resize(cfg.d_model, 0.0f);
    m_ln_final_gamma.resize(cfg.d_model, 0.0f); v_ln_final_gamma.resize(cfg.d_model, 0.0f);
    m_ln_final_beta.resize(cfg.d_model, 0.0f); v_ln_final_beta.resize(cfg.d_model, 0.0f);
    grad_embedding.resize(embedding.size(), 0.0f);
    grad_pos_embedding.resize(pos_embedding.size(), 0.0f);
    m_embedding.resize(embedding.size(), 0.0f);
    v_embedding.resize(embedding.size(), 0.0f);
    m_pos_embedding.resize(pos_embedding.size(), 0.0f);
    v_pos_embedding.resize(pos_embedding.size(), 0.0f);
}

// Runs token+positional embedding through every transformer block and the
// final LayerNorm, populating every activation buffer backward_impl_seq
// needs (this is the "graph" both forward_impl and forward_impl_seq share -
// they differ only in how much of the output projection they compute).
static void run_body(Model* m, const int* tokens, int n_tokens) {
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
        blk.ffn.pre_act.resize(seq*cfg.d_ff);
        blk.q.resize(seq*d); blk.k.resize(seq*d); blk.v.resize(seq*d);
        blk.ln2_out.resize(seq*d);
        blk.attn_concat.resize(seq*d);

        int dh = blk.attn.d_head, nh = blk.attn.n_heads;
        // .assign, not .resize: stale entries from a longer previous
        // sequence must not leak through as nonzero "attention" to future
        // positions that never actually computed them this call.
        blk.attn_scores.assign((size_t)nh*seq*seq, 0.0f);

        matmul(x.data(), blk.attn.Wq.weight.data(), blk.q.data(), seq, d, d);
        add_bias(blk.q.data(), blk.attn.Wq.bias.data(), seq, d);
        matmul(x.data(), blk.attn.Wk.weight.data(), blk.k.data(), seq, d, d);
        add_bias(blk.k.data(), blk.attn.Wk.bias.data(), seq, d);
        matmul(x.data(), blk.attn.Wv.weight.data(), blk.v.data(), seq, d, d);
        add_bias(blk.v.data(), blk.attn.Wv.bias.data(), seq, d);

        std::vector<float> attn_concat_local(seq*d, 0.0f);
        float scale = 1.0f / std::sqrt((float)dh);
        for (int h = 0; h < nh; ++h) {
            for (int i = 0; i < seq; ++i) {
                std::vector<float> scores(i+1, 0.0f);
                for (int j = 0; j <= i; ++j) {
                    float dot = 0.0f;
                    for (int k = 0; k < dh; ++k) {
                        dot += blk.q[i*d + h*dh + k] * blk.k[j*d + h*dh + k];
                    }
                    scores[j] = dot * scale;
                }
                float maxs = scores[0];
                for (int j = 1; j <= i; ++j) if (scores[j] > maxs) maxs = scores[j];
                float sum_exp = 0.0f;
                for (int j = 0; j <= i; ++j) { scores[j] = std::exp(scores[j]-maxs); sum_exp += scores[j]; }
                for (int j = 0; j <= i; ++j) scores[j] /= sum_exp;
                for (int j = 0; j <= i; ++j) blk.attn_scores[(size_t)h*seq*seq + i*seq + j] = scores[j];
                for (int k = 0; k < dh; ++k) {
                    float val = 0.0f;
                    for (int j = 0; j <= i; ++j) val += scores[j] * blk.v[j*d + h*dh + k];
                    attn_concat_local[i*d + h*dh + k] = val;
                }
            }
        }
        blk.attn_concat = attn_concat_local;
        matmul(attn_concat_local.data(), blk.attn.Wo.weight.data(), blk.attn_out.data(), seq, d, d);
        add_bias(blk.attn_out.data(), blk.attn.Wo.bias.data(), seq, d);
        for (int i = 0; i < seq*d; ++i) blk.residual1[i] = x[i];
        add(x.data(), blk.attn_out.data(), x.data(), seq*d);
        layer_norm(x.data(), x.data(), blk.ln1_gamma.data(), blk.ln1_beta.data(), seq, d, 1e-5f);

        // Post-LN1 value = FFN's actual input ("y1").
        for (int i = 0; i < seq*d; ++i) blk.ln2_out[i] = x[i];

        matmul(x.data(), blk.ffn.W1.weight.data(), blk.ffn.pre_act.data(), seq, cfg.d_ff, d);
        add_bias(blk.ffn.pre_act.data(), blk.ffn.W1.bias.data(), seq, cfg.d_ff);
        gelu(blk.ffn.hidden.data(), blk.ffn.pre_act.data(), seq*cfg.d_ff);
        matmul(blk.ffn.hidden.data(), blk.ffn.W2.weight.data(), blk.ffn_out.data(), seq, d, cfg.d_ff);
        add_bias(blk.ffn_out.data(), blk.ffn.W2.bias.data(), seq, d);
        for (int i = 0; i < seq*d; ++i) blk.residual2[i] = x[i];
        add(x.data(), blk.ffn_out.data(), x.data(), seq*d);
        layer_norm(x.data(), x.data(), blk.ln2_gamma.data(), blk.ln2_beta.data(), seq, d, 1e-5f);
    }

    m->ln_final_out.resize(seq*d);
    for (int i = 0; i < seq*d; ++i) m->ln_final_out[i] = x[i];

    layer_norm(x.data(), x.data(), m->ln_final_gamma.data(), m->ln_final_beta.data(), seq, d, 1e-5f);
    m->ln_final_normalized.resize(seq*d);
    for (int i = 0; i < seq*d; ++i) m->ln_final_normalized[i] = x[i];
}

void forward_impl(Model* m, const int* tokens, int n_tokens, float* out_logits) {
    run_body(m, tokens, n_tokens);
    const auto& cfg = m->config;
    int d = cfg.d_model, seq = n_tokens;
    matmul(m->ln_final_normalized.data() + (size_t)(seq-1)*d, m->output_proj.weight.data(), out_logits, 1, cfg.vocab_size, d);
    add_bias(out_logits, m->output_proj.bias.data(), 1, cfg.vocab_size);
}

void forward_impl_seq(Model* m, const int* tokens, int n_tokens, float* out_logits) {
    run_body(m, tokens, n_tokens);
    const auto& cfg = m->config;
    int d = cfg.d_model, seq = n_tokens;
    matmul(m->ln_final_normalized.data(), m->output_proj.weight.data(), out_logits, seq, cfg.vocab_size, d);
    add_bias(out_logits, m->output_proj.bias.data(), seq, cfg.vocab_size);
}

// Full, correct backward pass: real causal multi-head attention backprop
// (softmax-with-causal-mask backward + per-head dQ/dK/dV, accumulated over
// every query position that attended to a given key/value), correctly
// reconstructed LayerNorm inputs, correct GELU/Wo/output-projection
// activands, and bias-gradient accumulation for every sublayer. See
// docs/TRANSFORMER_LEARNING.md for the bugs this replaces.
void backward_impl_seq(Model* m, const int* tokens, int n_tokens, const float* dlogits) {
    if (!m || !tokens || !dlogits || n_tokens <= 0) return;

    const auto& cfg = m->config;
    int d = cfg.d_model, seq = n_tokens;
    int vocab = cfg.vocab_size;

    if (seq > cfg.max_seq_len) seq = cfg.max_seq_len;
    for (int i = 0; i < seq; ++i) {
        if (tokens[i] < 0 || tokens[i] >= vocab) return;
    }
    if (m->ln_final_normalized.size() < (size_t)seq*d) return;  // forward wasn't run on a matching sequence

    // ---- Output projection backward, every position ----
    std::vector<float> dx((size_t)seq*d, 0.0f);
    for (int t = 0; t < seq; ++t) {
        const float* x_final_t = m->ln_final_normalized.data() + (size_t)t*d;
        const float* dlogits_t = dlogits + (size_t)t*vocab;
        for (int i = 0; i < d; ++i) {
            float sum = 0.0f;
            for (int j = 0; j < vocab; ++j)
                sum += dlogits_t[j] * m->output_proj.weight[(size_t)i*vocab + j];
            dx[(size_t)t*d + i] = sum;
        }
        for (int i = 0; i < d; ++i)
            for (int j = 0; j < vocab; ++j)
                m->output_proj.grad_weight[(size_t)i*vocab + j] += x_final_t[i] * dlogits_t[j];
        for (int j = 0; j < vocab; ++j)
            m->output_proj.grad_bias[j] += dlogits_t[j];
    }

    // ---- Final LayerNorm backward ----
    {
        std::vector<float> dln_final_out((size_t)seq*d);
        layer_norm_backward(m->ln_final_out.data(), m->ln_final_gamma.data(), m->ln_final_beta.data(),
                             dx.data(), dln_final_out.data(), m->grad_ln_final_gamma.data(),
                             m->grad_ln_final_beta.data(), seq, d, 1e-5f);
        dx.swap(dln_final_out);
    }

    // ---- Transformer blocks, reverse order ----
    for (int blk_idx = cfg.n_layers - 1; blk_idx >= 0; --blk_idx) {
        auto& blk = m->blocks[blk_idx];
        int dh = blk.attn.d_head, nh = blk.attn.n_heads;

        // --- FFN / LN2 branch ---
        // Reconstruct the actual pre-LN2 input (forward applied LN2
        // in-place after this add; nothing saves it directly).
        std::vector<float> s2((size_t)seq*d);
        for (int i = 0; i < seq*d; ++i) s2[i] = blk.residual2[i] + blk.ffn_out[i];

        std::vector<float> dln2_out((size_t)seq*d);
        layer_norm_backward(s2.data(), blk.ln2_gamma.data(), blk.ln2_beta.data(),
                             dx.data(), dln2_out.data(), blk.grad_ln2_gamma.data(),
                             blk.grad_ln2_beta.data(), seq, d, 1e-5f);

        std::vector<float> dffn_hidden((size_t)seq*cfg.d_ff);
        matmul_backward(blk.ffn.hidden.data(), blk.ffn.W2.weight.data(), dln2_out.data(),
                         dffn_hidden.data(), blk.ffn.W2.grad_weight.data(), seq, d, cfg.d_ff);
        for (int t = 0; t < seq; ++t)
            for (int j = 0; j < d; ++j)
                blk.ffn.W2.grad_bias[j] += dln2_out[(size_t)t*d + j];

        std::vector<float> dgelu_out((size_t)seq*cfg.d_ff);
        gelu_backward(blk.ffn.hidden.data(), blk.ffn.pre_act.data(), dffn_hidden.data(), dgelu_out.data(), seq*cfg.d_ff);

        std::vector<float> dffn_in((size_t)seq*d);
        matmul_backward(blk.ln2_out.data(), blk.ffn.W1.weight.data(), dgelu_out.data(),
                         dffn_in.data(), blk.ffn.W1.grad_weight.data(), seq, cfg.d_ff, d);
        for (int t = 0; t < seq; ++t)
            for (int j = 0; j < cfg.d_ff; ++j)
                blk.ffn.W1.grad_bias[j] += dgelu_out[(size_t)t*cfg.d_ff + j];

        // Merge residual branch (dln2_out, already correct via
        // layer_norm_backward's ddst argument) with the FFN branch exactly
        // once - the pre-fix code both double-counted this and then
        // discarded it via an overwrite.
        for (int i = 0; i < seq*d; ++i) dx[i] = dln2_out[i] + dffn_in[i];

        // --- Attention / LN1 branch ---
        std::vector<float> s1((size_t)seq*d);
        for (int i = 0; i < seq*d; ++i) s1[i] = blk.residual1[i] + blk.attn_out[i];

        std::vector<float> dln1_out((size_t)seq*d);
        layer_norm_backward(s1.data(), blk.ln1_gamma.data(), blk.ln1_beta.data(),
                             dx.data(), dln1_out.data(), blk.grad_ln1_gamma.data(),
                             blk.grad_ln1_beta.data(), seq, d, 1e-5f);

        std::vector<float> dattn_concat((size_t)seq*d);
        matmul_backward(blk.attn_concat.data(), blk.attn.Wo.weight.data(), dln1_out.data(),
                         dattn_concat.data(), blk.attn.Wo.grad_weight.data(), seq, d, d);
        for (int t = 0; t < seq; ++t)
            for (int j = 0; j < d; ++j)
                blk.attn.Wo.grad_bias[j] += dln1_out[(size_t)t*d + j];

        // --- Real causal multi-head attention backward ---
        std::vector<float> dQ((size_t)seq*d, 0.0f), dK((size_t)seq*d, 0.0f), dV((size_t)seq*d, 0.0f);
        float scale = 1.0f / std::sqrt((float)dh);
        for (int h = 0; h < nh; ++h) {
            for (int i = 0; i < seq; ++i) {
                std::vector<float> dP(i+1, 0.0f);
                for (int j = 0; j <= i; ++j) {
                    float g = 0.0f;
                    for (int k = 0; k < dh; ++k)
                        g += dattn_concat[(size_t)i*d + h*dh + k] * blk.v[(size_t)j*d + h*dh + k];
                    dP[j] = g;
                    float p_ij = blk.attn_scores[(size_t)h*seq*seq + i*seq + j];
                    for (int k = 0; k < dh; ++k)
                        // dV[j] accumulates a contribution from EVERY query
                        // i >= j across this whole h/i loop, not just i==j -
                        // that's the causal-mask direction that's easy to
                        // get backwards.
                        dV[(size_t)j*d + h*dh + k] += p_ij * dattn_concat[(size_t)i*d + h*dh + k];
                }
                std::vector<float> dScoresRaw(i+1, 0.0f);
                softmax_backward(&blk.attn_scores[(size_t)h*seq*seq + (size_t)i*seq], dP.data(), dScoresRaw.data(), 1, i+1);
                for (int j = 0; j <= i; ++j) {
                    float g = dScoresRaw[j] * scale;
                    for (int k = 0; k < dh; ++k) {
                        dQ[(size_t)i*d + h*dh + k] += g * blk.k[(size_t)j*d + h*dh + k];
                        dK[(size_t)j*d + h*dh + k] += g * blk.q[(size_t)i*d + h*dh + k];
                    }
                }
            }
        }

        std::vector<float> du_q((size_t)seq*d), du_k((size_t)seq*d), du_v((size_t)seq*d);
        matmul_backward(blk.residual1.data(), blk.attn.Wq.weight.data(), dQ.data(), du_q.data(), blk.attn.Wq.grad_weight.data(), seq, d, d);
        matmul_backward(blk.residual1.data(), blk.attn.Wk.weight.data(), dK.data(), du_k.data(), blk.attn.Wk.grad_weight.data(), seq, d, d);
        matmul_backward(blk.residual1.data(), blk.attn.Wv.weight.data(), dV.data(), du_v.data(), blk.attn.Wv.grad_weight.data(), seq, d, d);
        for (int t = 0; t < seq; ++t) {
            for (int j = 0; j < d; ++j) {
                blk.attn.Wq.grad_bias[j] += dQ[(size_t)t*d + j];
                blk.attn.Wk.grad_bias[j] += dK[(size_t)t*d + j];
                blk.attn.Wv.grad_bias[j] += dV[(size_t)t*d + j];
            }
        }

        for (int i = 0; i < seq*d; ++i)
            dx[i] = dln1_out[i] + du_q[i] + du_k[i] + du_v[i];
    }

    // ---- Embeddings ----
    for (int t = 0; t < seq; ++t) {
        int token = tokens[t];
        for (int j = 0; j < d; ++j) {
            m->grad_embedding[(size_t)token*d+j] += dx[(size_t)t*d + j];
            m->grad_pos_embedding[(size_t)t*d + j] += dx[(size_t)t*d + j];
        }
    }
}

// Existing single-last-position contract, now internally correct: routes
// through backward_impl_seq with a dlogits buffer that's zero everywhere
// except the last position's slice, so DPO/RL/every existing caller gets
// the fixed gradient computation for free with no signature change.
void backward_impl(Model* m, const int* tokens, int n_tokens, const float* dlogits) {
    if (!m || !tokens || !dlogits || n_tokens <= 0) return;
    const auto& cfg = m->config;
    int seq = n_tokens;
    if (seq > cfg.max_seq_len) seq = cfg.max_seq_len;
    int vocab = cfg.vocab_size;
    std::vector<float> full_dlogits((size_t)seq*vocab, 0.0f);
    for (int j = 0; j < vocab; ++j) full_dlogits[(size_t)(seq-1)*vocab + j] = dlogits[j];
    backward_impl_seq(m, tokens, seq, full_dlogits.data());
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

int overllm_backward(OverLLMModel* model, const int* tokens, int n_tokens, const float* dlogits) {
    Model* m = (Model*)model;
    if (n_tokens > m->config.max_seq_len) n_tokens = m->config.max_seq_len;
    backward_impl(m, tokens, n_tokens, dlogits);
    return 0;
}

int overllm_forward_seq(OverLLMModel* model, const int* tokens, int n_tokens, float* logits) {
    Model* m = (Model*)model;
    if (n_tokens > m->config.max_seq_len) n_tokens = m->config.max_seq_len;
    forward_impl_seq(m, tokens, n_tokens, logits);
    return 0;
}

int overllm_backward_seq(OverLLMModel* model, const int* tokens, int n_tokens, const float* dlogits) {
    Model* m = (Model*)model;
    if (n_tokens > m->config.max_seq_len) n_tokens = m->config.max_seq_len;
    backward_impl_seq(m, tokens, n_tokens, dlogits);
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

    // Use full backward pass
    overllm_zero_grad(model);
    std::vector<float> combined_dlogits(vs);
    for (int i = 0; i < vs; ++i) combined_dlogits[i] = dlogits_c[i] + dlogits_r[i];
    overllm_backward(model, chosen_tokens, chosen_len, combined_dlogits.data());

    return loss;
}

void overllm_adamw_step(OverLLMModel* model, float lr, float beta1, float beta2, float eps, float weight_decay) {
    Model* m = (Model*)model;
    m->t_step++;
    float lr_t = lr * std::sqrt(1.0f - std::pow(beta2, m->t_step)) / (1.0f - std::pow(beta1, m->t_step));

    // Helper to update a parameter with AdamW
    auto update_param = [&](std::vector<float>& param, std::vector<float>& grad, std::vector<float>& m_param, std::vector<float>& v_param) {
        for (size_t i = 0; i < param.size(); ++i) {
            m_param[i] = beta1 * m_param[i] + (1.0f - beta1) * grad[i];
            v_param[i] = beta2 * v_param[i] + (1.0f - beta2) * grad[i] * grad[i];
            float m_hat = m_param[i] / (1.0f - std::pow(beta1, m->t_step));
            float v_hat = v_param[i] / (1.0f - std::pow(beta2, m->t_step));
            param[i] -= lr_t * (m_hat / (std::sqrt(v_hat) + eps) + weight_decay * param[i]);
        }
    };

    // Update embeddings
    update_param(m->embedding, m->grad_embedding, m->m_embedding, m->v_embedding);
    update_param(m->pos_embedding, m->grad_pos_embedding, m->m_pos_embedding, m->v_pos_embedding);

    // Update blocks
    for (auto& blk : m->blocks) {
        update_param(blk.attn.Wq.weight, blk.attn.Wq.grad_weight, blk.attn.Wq.m_weight, blk.attn.Wq.v_weight);
        update_param(blk.attn.Wq.bias, blk.attn.Wq.grad_bias, blk.attn.Wq.m_bias, blk.attn.Wq.v_bias);
        update_param(blk.attn.Wk.weight, blk.attn.Wk.grad_weight, blk.attn.Wk.m_weight, blk.attn.Wk.v_weight);
        update_param(blk.attn.Wk.bias, blk.attn.Wk.grad_bias, blk.attn.Wk.m_bias, blk.attn.Wk.v_bias);
        update_param(blk.attn.Wv.weight, blk.attn.Wv.grad_weight, blk.attn.Wv.m_weight, blk.attn.Wv.v_weight);
        update_param(blk.attn.Wv.bias, blk.attn.Wv.grad_bias, blk.attn.Wv.m_bias, blk.attn.Wv.v_bias);
        update_param(blk.attn.Wo.weight, blk.attn.Wo.grad_weight, blk.attn.Wo.m_weight, blk.attn.Wo.v_weight);
        update_param(blk.attn.Wo.bias, blk.attn.Wo.grad_bias, blk.attn.Wo.m_bias, blk.attn.Wo.v_bias);
        update_param(blk.ffn.W1.weight, blk.ffn.W1.grad_weight, blk.ffn.W1.m_weight, blk.ffn.W1.v_weight);
        update_param(blk.ffn.W1.bias, blk.ffn.W1.grad_bias, blk.ffn.W1.m_bias, blk.ffn.W1.v_bias);
        update_param(blk.ffn.W2.weight, blk.ffn.W2.grad_weight, blk.ffn.W2.m_weight, blk.ffn.W2.v_weight);
        update_param(blk.ffn.W2.bias, blk.ffn.W2.grad_bias, blk.ffn.W2.m_bias, blk.ffn.W2.v_bias);
        update_param(blk.ln1_gamma, blk.grad_ln1_gamma, blk.m_ln1_gamma, blk.v_ln1_gamma);
        update_param(blk.ln1_beta, blk.grad_ln1_beta, blk.m_ln1_beta, blk.v_ln1_beta);
        update_param(blk.ln2_gamma, blk.grad_ln2_gamma, blk.m_ln2_gamma, blk.v_ln2_gamma);
        update_param(blk.ln2_beta, blk.grad_ln2_beta, blk.m_ln2_beta, blk.v_ln2_beta);
    }

    // Update final layer norm
    update_param(m->ln_final_gamma, m->grad_ln_final_gamma, m->m_ln_final_gamma, m->v_ln_final_gamma);
    update_param(m->ln_final_beta, m->grad_ln_final_beta, m->m_ln_final_beta, m->v_ln_final_beta);

    // Update output projection
    update_param(m->output_proj.weight, m->output_proj.grad_weight, m->output_proj.m_weight, m->output_proj.v_weight);
    update_param(m->output_proj.bias, m->output_proj.grad_bias, m->output_proj.m_bias, m->output_proj.v_bias);
}

int overllm_ga_optimize(OverLLMModel* model, int population_size, float mutation_rate, float crossover_rate) {
    (void)model; (void)population_size; (void)mutation_rate; (void)crossover_rate;
    // Simplified stub - in production this would use the GeneticAlgorithm class
    // For now, just return success to indicate the interface exists
    return 0;
}
float overllm_clip_gradients(OverLLMModel* model, float max_norm) {
    Model* m = (Model*)model;

    // Same gradient set overllm_zero_grad touches, gathered as references so
    // both the norm computation and the rescale pass iterate identically.
    std::vector<std::vector<float>*> grads = {
        &m->grad_embedding, &m->grad_pos_embedding,
        &m->grad_ln_final_gamma, &m->grad_ln_final_beta,
        &m->output_proj.grad_weight, &m->output_proj.grad_bias,
    };
    for (auto& blk : m->blocks) {
        grads.push_back(&blk.attn.Wq.grad_weight); grads.push_back(&blk.attn.Wq.grad_bias);
        grads.push_back(&blk.attn.Wk.grad_weight); grads.push_back(&blk.attn.Wk.grad_bias);
        grads.push_back(&blk.attn.Wv.grad_weight); grads.push_back(&blk.attn.Wv.grad_bias);
        grads.push_back(&blk.attn.Wo.grad_weight); grads.push_back(&blk.attn.Wo.grad_bias);
        grads.push_back(&blk.ffn.W1.grad_weight); grads.push_back(&blk.ffn.W1.grad_bias);
        grads.push_back(&blk.ffn.W2.grad_weight); grads.push_back(&blk.ffn.W2.grad_bias);
        grads.push_back(&blk.grad_ln1_gamma); grads.push_back(&blk.grad_ln1_beta);
        grads.push_back(&blk.grad_ln2_gamma); grads.push_back(&blk.grad_ln2_beta);
    }

    double sum_sq = 0.0;
    for (auto* g : grads) {
        for (float v : *g) sum_sq += static_cast<double>(v) * v;
    }
    float total_norm = static_cast<float>(std::sqrt(sum_sq));

    if (total_norm > max_norm && total_norm > 0.0f) {
        float scale = max_norm / total_norm;
        for (auto* g : grads) {
            for (float& v : *g) v *= scale;
        }
    }
    return total_norm;
}

void overllm_zero_grad(OverLLMModel* model) {
    Model* m = (Model*)model;
    std::fill(m->grad_embedding.begin(), m->grad_embedding.end(), 0.0f);
    std::fill(m->grad_pos_embedding.begin(), m->grad_pos_embedding.end(), 0.0f);
    std::fill(m->grad_ln_final_gamma.begin(), m->grad_ln_final_gamma.end(), 0.0f);
    std::fill(m->grad_ln_final_beta.begin(), m->grad_ln_final_beta.end(), 0.0f);
    std::fill(m->output_proj.grad_weight.begin(), m->output_proj.grad_weight.end(), 0.0f);
    std::fill(m->output_proj.grad_bias.begin(), m->output_proj.grad_bias.end(), 0.0f);

    for (auto& blk : m->blocks) {
        std::fill(blk.attn.Wq.grad_weight.begin(), blk.attn.Wq.grad_weight.end(), 0.0f);
        std::fill(blk.attn.Wq.grad_bias.begin(), blk.attn.Wq.grad_bias.end(), 0.0f);
        std::fill(blk.attn.Wk.grad_weight.begin(), blk.attn.Wk.grad_weight.end(), 0.0f);
        std::fill(blk.attn.Wk.grad_bias.begin(), blk.attn.Wk.grad_bias.end(), 0.0f);
        std::fill(blk.attn.Wv.grad_weight.begin(), blk.attn.Wv.grad_weight.end(), 0.0f);
        std::fill(blk.attn.Wv.grad_bias.begin(), blk.attn.Wv.grad_bias.end(), 0.0f);
        std::fill(blk.attn.Wo.grad_weight.begin(), blk.attn.Wo.grad_weight.end(), 0.0f);
        std::fill(blk.attn.Wo.grad_bias.begin(), blk.attn.Wo.grad_bias.end(), 0.0f);
        std::fill(blk.ffn.W1.grad_weight.begin(), blk.ffn.W1.grad_weight.end(), 0.0f);
        std::fill(blk.ffn.W1.grad_bias.begin(), blk.ffn.W1.grad_bias.end(), 0.0f);
        std::fill(blk.ffn.W2.grad_weight.begin(), blk.ffn.W2.grad_weight.end(), 0.0f);
        std::fill(blk.ffn.W2.grad_bias.begin(), blk.ffn.W2.grad_bias.end(), 0.0f);
        std::fill(blk.grad_ln1_gamma.begin(), blk.grad_ln1_gamma.end(), 0.0f);
        std::fill(blk.grad_ln1_beta.begin(), blk.grad_ln1_beta.end(), 0.0f);
        std::fill(blk.grad_ln2_gamma.begin(), blk.grad_ln2_gamma.end(), 0.0f);
        std::fill(blk.grad_ln2_beta.begin(), blk.grad_ln2_beta.end(), 0.0f);
    }
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

    // Use full backward pass with policy gradient
    overllm_zero_grad(model);
    std::vector<float> state_logits(vs);
    overllm_forward(model, state_tokens, state_len, state_logits.data());

    // Compute policy gradient
    std::vector<float> dlogits(vs);
    for (int i = 0; i < vs; ++i) {
        float prob = std::exp(state_logits[i]);
        dlogits[i] = (i == action ? 1.0f : 0.0f) - prob;
        dlogits[i] *= td_error * lr;
    }

    overllm_backward(model, state_tokens, state_len, dlogits.data());

    return td_error;
}

int overllm_load_vector_index(OverLLMModel* model, const char* path) {
    (void)model; (void)path;
    // Vector index is managed in Rust layer
    return 0;
}

} // extern "C"
