# Real transformer learning (not just "it runs")

> Status: a small, honest demonstration that OverLLM's C++ transformer
> (`cpp/src/model.cpp`) actually performs gradient descent on real data,
> numerically verified against finite-difference gradients — and a real,
> multi-part backward-pass correctness bug found and fixed while proving it.

## The gap this fills

`cpp/src/model.cpp` already contained a substantial, non-stub transformer
implementation: multi-head attention, layer norm, FFN, a full backward pass,
AdamW with momentum, DPO loss, and an RL step. But nothing in the repo had
ever verified it actually *learns* anything, and — as this pass found — the
backward pass had never been checked for mathematical correctness either:

- `cpp/test_overllm.cpp` checks that a single DPO/RL/backward/AdamW step
  "completes" and produces a plausible-looking loss value. It never checks
  loss over multiple steps.
- `cpp/train_online.cpp`'s training loop feeds **uniformly random tokens**
  as DPO chosen/rejected pairs. Chosen and rejected are both random draws
  from the same distribution, so there is no learnable signal by
  construction — it can run for any number of steps and prove nothing about
  whether gradient descent works, only that the code doesn't crash.
- The original transformer-learning demo (documented below, in the section
  on the bugs this replaces) *did* show loss decreasing with no NaN — but
  that turned out to be true for the wrong reason. Loss decreasing is
  necessary but not sufficient evidence that a backward pass is correct.

## What proves correctness here: a numerical gradient check

`cpp/tools/gradient_check.cpp` compares `backward_impl_seq`'s analytical
gradients against finite-difference estimates
(`(loss(w+eps) - loss(w-eps)) / 2eps`) for a probed set of parameters —
attention `Wq`/`Wk`/`Wv`/`Wo` weights and biases, FFN `W1`/`W2` weights and
biases, both per-block LayerNorms, the final LayerNorm, token/positional
embeddings, and the output projection at a **non-last** sequence position —
at two different non-last query positions in a 6-token sequence.

```bash
cmake -B cpp/build -S cpp && cmake --build cpp/build --target gradient_check
./cpp/build/gradient_check
```

All 30 probes pass (combined absolute/relative tolerance, matching
`torch.autograd.gradcheck`'s approach: pure relative error rejects
genuinely-correct near-zero gradients, since float32 finite-difference noise
at that scale dominates the ratio without indicating a bug). This is the
actual proof the fix below is correct — not the loss curve, which the
pre-fix code also produced successfully while several of its gradients were
wrong.

## Real bugs found and fixed

Reading `backward_impl` in full while scoping how to scale this experiment
into a genuine, trained-from-scratch decoder-only transformer found seven
distinct, compounding gradient-correctness bugs, not just the attention
stub that prompted the closer look:

1. **Attention Q/K/V backward was a stub.** It wrote one identical, wrong
   `d×d` matrix into `Wq/Wk/Wv.grad_weight` instead of real
   causal-softmax backprop, and never updated the gradient flowing to the
   block's input — so gradient into the embedding table skipped attention
   entirely, mathematically equivalent to `x` flowing straight through `Wo`.
2. **Both `layer_norm_backward` calls used the wrong `src`** (pre-residual
   values instead of the actual post-residual pre-LayerNorm input forward
   computed), independent of the attention bug.
3. **The residual-branch gradient was double-counted, then discarded** — 
   added once correctly via `layer_norm_backward`'s `ddst` argument, added a
   second time, then overwritten instead of merged.
4. **`gelu_backward` was given the post-activation buffer as if it were the
   pre-activation buffer** (forward applied GELU in place, destroying the
   value backward needed) — computed `GELU'(GELU(z))` instead of `GELU'(z)`.
5. **`Wo`'s weight gradient used the wrong activation** (the post-`Wo`
   value, instead of the actual pre-`Wo` concatenated attention output,
   which forward never saved anywhere).
6. **`output_proj`'s weight gradient used the raw token embedding** of the
   last token, not the actual post-final-LayerNorm activation that really
   fed the output projection.
7. **No bias gradient was ever accumulated** for `Wq/Wk/Wv/Wo/W1/W2` in any
   block — those biases stayed frozen at zero-init for the entire training
   run, in every prior training experiment in this repo.

None of this means the original 7.405→5.198 loss curve was fabricated —
gradient descent genuinely ran and genuinely reduced loss, propelled by
whatever *did* work (the FFN path, once corrected here; the final LayerNorm;
embeddings via the `Wo`-backward chain). It means "loss decreases, no NaN"
was necessary but not sufficient evidence the transformer was learning via
its attention mechanism specifically, which is the whole point of the
architecture.

### The fix

`cpp/src/model.cpp` now implements real causal multi-head attention
backprop: per head, per query position (outer loop, matching forward's own
loop structure), per key/value position `j <= i` (inner loop), it
accumulates `dV`/`dP` from the saved softmax weights, backprops through the
softmax via `softmax_backward` restricted to the causal-valid slice, then
propagates through the `Q·K` dot product into `dQ`/`dK`. The critical
correctness point: a key/value at position `j` must receive a gradient
contribution from **every** query `i >= j`, not just `i == j` — this only
shows up as a bug for non-last query positions, which is exactly why
`gradient_check.cpp` deliberately probes position 1 and 3 of a 6-token
sequence, not just the last one.

Two new public functions, `overllm_forward_seq`/`overllm_backward_seq`,
compute logits and gradients for every position in a sequence (existing
`overllm_forward`/`overllm_backward` keep their original last-position-only
contract unchanged, so no existing caller's buffer sizes or behavior
change — see `cpp/include/overllm.h`). `overllm_backward` now internally
routes through the corrected `backward_impl_seq` with a zero-padded
`dlogits` buffer, so DPO/RL and every other existing caller gets the fixed
gradient computation for free with no signature or behavior-contract change.

## What this adds

`cpp/tools/train_language_model.cpp`: a real next-token language-modeling
training loop using:

- **Real tokenized text**: sentences from `benchmark/rstf/corpus.json`,
  encoded with the real trained BPE tokenizer (`tools/bpe_tokenizer.py` /
  `cpp/src/tokenizer.cpp`).
- **Real objective**: softmax cross-entropy at *every* position in each
  training window (not just the window's last token), computed from
  `overllm_forward_seq`'s logits and backpropagated via
  `overllm_backward_seq` — the multi-position functions above, chunking the
  corpus into non-overlapping windows the way real GPT pretraining batches
  contiguous context, not a workaround for a forward pass that used to only
  compute one token's logits at a time.
- **A small model** (`d_model=64`, 2 layers) so a full run trains in seconds
  on CPU.

```bash
python tools/transformer_learning_check.py
python tools/transformer_learning_check.py --epochs 30 --out benchmark/transformer_learning/report.json
```

Committed run: `benchmark/transformer_learning/report.json`,
`benchmark/transformer_learning/run_log.txt`.

## Result

| Metric | Value |
|---|---|
| Corpus | 6 sentences, 82 tokens |
| First epoch loss | 7.434 |
| Last epoch loss (30 epochs) | 4.703 |
| Reduction | 36.7% |
| NaN encountered | No |
| Loss curve shape | Monotonically decreasing every epoch (checked to 60 epochs: 7.434 → 1.895, 74.5% reduction, still stable, no divergence) |

This reduction is larger than the pre-fix run's 29.8%, and now comes with
the gradient-check evidence above that it's driven by a mathematically
correct backward pass through the actual attention mechanism, not
incidentally by the paths that happened to be correct before.

Scope honesty: this is a memorization/overfitting demonstration on a tiny,
repeated corpus with a tiny model, not a claim of general language
understanding. What it proves: the backward pass and AdamW optimizer
genuinely perform correct gradient descent on real data through every
sublayer, including attention — a testable, mechanically checked claim
(`gradient_check` asserts analytical gradients match finite-difference
estimates; `tools/transformer_learning_check.py` asserts the loss curve
decreases and never hits NaN), not an assertion to take on faith.

## Honest limits

- Tiny corpus (82 tokens), tiny model (`d_model=64`, 2 layers, ~0.4M
  parameters) — chosen for fast CPU iteration, not representative of a
  usable language model.
- No held-out evaluation set; this measures training-set loss only, so it
  cannot distinguish genuine generalization from memorization. For a corpus
  this small and repeated across many epochs, memorization is expected and
  is not a flaw in what's being tested here (whether the optimizer works).
- `overllm_clip_gradients`'s `max_norm=1.0` was chosen empirically to fix an
  earlier NaN-divergence case (see below), not tuned against a validation
  curve.
- `gradient_check.cpp` probes a representative subset of parameters (one
  entry per weight/bias matrix per probed position), not every parameter —
  a full check of every element would be prohibitively slow, and this
  subset already exercises every distinct code path (all four attention
  matrices, both FFN matrices, both block LayerNorms, the final LayerNorm,
  embeddings, and a non-last output-projection position).
- This does not touch `cpp/train_online.cpp`'s random-token DPO loop, which
  remains a stress/crash test, not a learning demonstration; a real DPO
  learning experiment would need real chosen/rejected preference pairs,
  which is future work.
- Corpus scale-up (beyond 82 tokens), a train/val split with held-out
  perplexity, retraining the BPE tokenizer to match this repo's growth, and
  fixing `cpp/src/inference_main.cpp`'s tokenizer mismatch (it uses a
  hand-rolled whitespace tokenizer, not the real BPE one training uses) are
  explicitly out of scope for this pass — a distinct, larger follow-up.

## Previously: the NaN-divergence bug (still relevant, unchanged by this fix)

The first version of this experiment (compiled with plain `-O2`) converged
cleanly. Run through this repo's actual CMake project — which builds
everything with `-O3 -ffast-math` — training instead **diverged to NaN
around epoch 15**. Investigating rather than just using the build that
happened to work: `cpp/src/model.cpp` had no gradient clipping anywhere in
its training path — a standard safeguard against exploding gradients that
every real transformer training setup uses, and this implementation simply
didn't have it.

Added `overllm_clip_gradients(model, max_norm)` — computes the global L2
norm across every gradient buffer and rescales if it exceeds `max_norm` —
and call it between backward and the AdamW step. This remains necessary and
unchanged by the attention-backward fix above (it operates on whatever
gradients exist, correct or not, and gradients are still just as capable of
exploding now that more of them are real signal rather than a stub).
