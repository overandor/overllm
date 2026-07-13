#pragma once
// Internal transformer struct/function declarations, shared between
// model.cpp (implementation) and tools that need direct struct access for
// verification (cpp/tools/gradient_check.cpp). Not part of the public C ABI
// in include/overllm.h - callers outside this build should use that instead.
#include "overllm.h"
#include <vector>

namespace overllm {

struct Linear {
    std::vector<float> weight;
    std::vector<float> bias;
    std::vector<float> grad_weight;
    std::vector<float> grad_bias;
    std::vector<float> m_weight;  // Adam momentum
    std::vector<float> v_weight;  // Adam velocity
    std::vector<float> m_bias;
    std::vector<float> v_bias;
    int in_features, out_features;
    Linear(int in_f, int out_f);
};

struct Attention {
    int n_heads, d_model, d_head;
    Linear Wq, Wk, Wv, Wo;
    Attention(int dm, int nh) : n_heads(nh), d_model(dm), d_head(dm/nh),
        Wq(dm,dm), Wk(dm,dm), Wv(dm,dm), Wo(dm,dm) {}
};

struct FFN {
    Linear W1, W2;
    std::vector<float> hidden;   // post-GELU activation (W2's input)
    std::vector<float> pre_act;  // pre-GELU activation (W1 output + bias); gelu_backward's src
    FFN(int d_model, int d_ff) : W1(d_model, d_ff), W2(d_ff, d_model) {}
};

struct TransformerBlock {
    Attention attn;
    FFN ffn;
    std::vector<float> ln1_gamma, ln1_beta, ln2_gamma, ln2_beta;
    std::vector<float> grad_ln1_gamma, grad_ln1_beta, grad_ln2_gamma, grad_ln2_beta;
    std::vector<float> m_ln1_gamma, v_ln1_gamma, m_ln1_beta, v_ln1_beta;
    std::vector<float> m_ln2_gamma, v_ln2_gamma, m_ln2_beta, v_ln2_beta;
    std::vector<float> attn_out, ffn_out, residual1, residual2;

    // Activation storage for backward pass
    std::vector<float> q, k, v, ln2_out;
    // Causal softmax attention weights, layout attn_scores[h*seq*seq + i*seq + j]
    // for j <= i; entries with j > i stay 0 (re-assigned to seq*seq*n_heads
    // zeros at the top of every forward call, since seq varies call to call).
    std::vector<float> attn_scores;
    // Concatenated multi-head attention output BEFORE the Wo projection -
    // the actual matmul input Wo's weight gradient needs (attn_out is
    // POST-Wo and must not be used as that gradient's activand).
    std::vector<float> attn_concat;

    TransformerBlock(int d_model, int n_heads, int d_ff);
};

struct Model {
    OverLLMConfig config;
    std::vector<float> embedding, pos_embedding;
    std::vector<TransformerBlock> blocks;
    Linear output_proj;
    std::vector<float> ln_final_gamma, ln_final_beta;
    std::vector<float> grad_ln_final_gamma, grad_ln_final_beta;
    std::vector<float> m_ln_final_gamma, v_ln_final_gamma, m_ln_final_beta, v_ln_final_beta;
    std::vector<float> grad_embedding, grad_pos_embedding;
    std::vector<float> m_embedding, v_embedding, m_pos_embedding, v_pos_embedding;
    int t_step = 0;

    // Activation storage for backward pass
    std::vector<float> ln_final_out;         // input to the final LayerNorm
    std::vector<float> ln_final_normalized;  // output of the final LayerNorm

    Model(const OverLLMConfig& cfg);
};

// tokens/n_tokens in, logits out. forward_impl writes vocab_size logits for
// the LAST position only (matches the existing public overllm_forward
// contract every current caller allocates for); forward_impl_seq writes
// n_tokens*vocab_size logits, one per position - callers must size their
// buffer accordingly. Both must be called before the matching backward_*
// function on the same tokens/n_tokens, since backward reads activations
// forward saved on the block/model structs above.
void forward_impl(Model* m, const int* tokens, int n_tokens, float* out_logits);
void forward_impl_seq(Model* m, const int* tokens, int n_tokens, float* out_logits);

// dlogits/backward_impl: vocab_size floats, gradient w.r.t. the last
// position's logits only (existing contract). backward_impl_seq:
// n_tokens*vocab_size floats, one slice per position - positions with no
// loss contribution should be zero-filled by the caller.
void backward_impl(Model* m, const int* tokens, int n_tokens, const float* dlogits);
void backward_impl_seq(Model* m, const int* tokens, int n_tokens, const float* dlogits);

} // namespace overllm
