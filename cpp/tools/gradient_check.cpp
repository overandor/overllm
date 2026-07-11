// Numerical gradient check for cpp/src/model.cpp's backward pass.
//
// This is the actual proof the backward-pass fix is correct - not just
// "compiles and loss goes down," which the pre-fix code also satisfied
// while its attention gradients were wrong (see docs/TRANSFORMER_LEARNING.md
// for the bugs this verifies are fixed). For a set of probed parameters,
// compares the analytical gradient from backward_impl_seq against a
// central-difference finite-difference estimate, and fails loudly (nonzero
// exit code) if they disagree beyond tolerance.
//
// Probes a non-last query/target position deliberately: the pre-fix
// attention backward stub happened to be closer to "not obviously wrong"
// for the very last position in a sequence; the causal accumulation bug
// (a key/value at position j must receive gradient from every query i>=j,
// not just i==j) only shows up when checking an earlier position.

#include "model_internal.h"
#include "tensor_ops.h"
#include <algorithm>
#include <cstdio>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>

using namespace overllm;

namespace {

struct Probe {
    std::string name;
    std::vector<float>* param;
    std::vector<float>* grad;
    int index;
};

float compute_probe_loss(Model* m, const int* tokens, int seq, int probe_pos, int target_token) {
    int vocab = m->config.vocab_size;
    std::vector<float> logits((size_t)seq * vocab);
    forward_impl_seq(m, tokens, seq, logits.data());
    std::vector<float> scratch(vocab);
    return cross_entropy_loss(logits.data() + (size_t)probe_pos * vocab, vocab, target_token, scratch.data());
}

bool run_probe(Model* m, const int* tokens, int seq, int probe_pos, int target_token,
               const Probe& p, float eps, float rtol, float atol, int& failures) {
    float w0 = (*p.param)[p.index];

    (*p.param)[p.index] = w0 + eps;
    float loss_plus = compute_probe_loss(m, tokens, seq, probe_pos, target_token);

    (*p.param)[p.index] = w0 - eps;
    float loss_minus = compute_probe_loss(m, tokens, seq, probe_pos, target_token);

    (*p.param)[p.index] = w0;  // restore

    float grad_fd = (loss_plus - loss_minus) / (2.0f * eps);
    float grad_analytical = (*p.grad)[p.index];
    float abs_err = std::fabs(grad_fd - grad_analytical);
    // Combined absolute+relative bound (same shape as numpy.allclose /
    // torch.autograd.gradcheck), not pure relative error: for a
    // near-zero true gradient, float32 finite-difference noise (~1e-4 to
    // 1e-3 in absolute terms, inherent to eps~1e-3 at float32 precision,
    // not fixable by retuning eps) dominates the relative-error ratio
    // without indicating an actual bug. Pure relative error was rejecting
    // several genuinely-correct small gradients before this was added.
    float rel_err = abs_err / std::max({std::fabs(grad_fd), std::fabs(grad_analytical), 1e-6f});
    bool pass = abs_err <= atol + rtol * std::fabs(grad_analytical);

    if (!pass) ++failures;
    std::printf("%-28s idx=%-5d  fd=% .6f  analytical=% .6f  abs_err=%.6f  rel_err=%.5f  %s\n",
                p.name.c_str(), p.index, grad_fd, grad_analytical, abs_err, rel_err, pass ? "PASS" : "FAIL");
    return pass;
}

} // namespace

int main() {
    OverLLMConfig cfg{};
    cfg.vocab_size = 50;
    cfg.d_model = 16;
    cfg.n_heads = 2;
    cfg.n_layers = 2;
    cfg.d_ff = 32;
    cfg.max_seq_len = 8;
    cfg.temperature = 0.8f;

    Model model(cfg);

    const int tokens[] = {3, 7, 1, 9, 2, 5};
    const int seq = 6;
    const int probe_positions[] = {1, 3};  // two non-last positions
    const int target_token = 11;

    const float eps = 1e-3f;
    const float rtol = 1e-2f;
    const float atol = 1e-3f;
    int failures = 0;

    for (int probe_pos : probe_positions) {
        std::printf("\n=== probe position %d (seq=%d, last=%d) ===\n", probe_pos, seq, seq-1);

        int vocab = cfg.vocab_size;
        std::vector<float> logits((size_t)seq * vocab);
        forward_impl_seq(&model, tokens, seq, logits.data());

        std::vector<float> dlogits((size_t)seq * vocab, 0.0f);
        std::vector<float> scratch(vocab);
        cross_entropy_loss(logits.data() + (size_t)probe_pos * vocab, vocab, target_token,
                            dlogits.data() + (size_t)probe_pos * vocab);

        overllm_zero_grad((OverLLMModel*)&model);
        backward_impl_seq(&model, tokens, seq, dlogits.data());

        auto& blk = model.blocks[0];
        std::vector<Probe> probes = {
            {"blocks[0].attn.Wq.weight", &blk.attn.Wq.weight, &blk.attn.Wq.grad_weight, 5},
            {"blocks[0].attn.Wk.weight", &blk.attn.Wk.weight, &blk.attn.Wk.grad_weight, 5},
            {"blocks[0].attn.Wv.weight", &blk.attn.Wv.weight, &blk.attn.Wv.grad_weight, 5},
            {"blocks[0].attn.Wq.bias",   &blk.attn.Wq.bias,   &blk.attn.Wq.grad_bias,   2},
            {"output_proj.weight (non-last pos)", &model.output_proj.weight, &model.output_proj.grad_weight, 20},
            // extended coverage
            {"blocks[0].attn.Wo.weight", &blk.attn.Wo.weight, &blk.attn.Wo.grad_weight, 3},
            {"blocks[0].ffn.W1.weight",  &blk.ffn.W1.weight,  &blk.ffn.W1.grad_weight,  7},
            {"blocks[0].ffn.W2.weight",  &blk.ffn.W2.weight,  &blk.ffn.W2.grad_weight,  4},
            {"blocks[0].ffn.W1.bias",    &blk.ffn.W1.bias,    &blk.ffn.W1.grad_bias,    1},
            {"blocks[0].ffn.W2.bias",    &blk.ffn.W2.bias,    &blk.ffn.W2.grad_bias,    1},
            {"blocks[0].ln1_gamma",      &blk.ln1_gamma,      &blk.grad_ln1_gamma,      0},
            {"blocks[0].ln2_gamma",      &blk.ln2_gamma,      &blk.grad_ln2_gamma,      0},
            {"ln_final_gamma",           &model.ln_final_gamma, &model.grad_ln_final_gamma, 0},
            {"embedding",                &model.embedding,    &model.grad_embedding,    tokens[probe_pos]*cfg.d_model + 2},
            {"pos_embedding",            &model.pos_embedding, &model.grad_pos_embedding, probe_pos*cfg.d_model + 2},
        };

        for (const auto& p : probes) {
            run_probe(&model, tokens, seq, probe_pos, target_token, p, eps, rtol, atol, failures);
        }
    }

    std::printf("\n%d probe(s) failed.\n", failures);
    return failures == 0 ? 0 : 1;
}
