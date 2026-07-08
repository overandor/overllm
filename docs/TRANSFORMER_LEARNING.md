# Real transformer learning (not just "it runs")

> Status: a small, honest demonstration that OverLLM's C++ transformer
> (`cpp/src/model.cpp`) actually performs gradient descent on real data, and
> a real bug (NaN divergence) found and fixed while proving it.

## The gap this fills

`cpp/src/model.cpp` already contained a substantial, non-stub transformer
implementation: multi-head attention, layer norm, FFN, a full backward pass,
AdamW with momentum, DPO loss, and an RL step — 634 lines, not a placeholder.
But nothing in the repo had ever verified it actually *learns* anything:

- `cpp/test_overllm.cpp` checks that a single DPO/RL/backward/AdamW step
  "completes" and produces a plausible-looking loss value. It never checks
  loss over multiple steps.
- `cpp/train_online.cpp`'s training loop feeds **uniformly random tokens**
  as DPO chosen/rejected pairs. Chosen and rejected are both random draws
  from the same distribution, so there is no learnable signal by
  construction — it can run for any number of steps and prove nothing about
  whether gradient descent works, only that the code doesn't crash.

## What this adds

`cpp/tools/train_language_model.cpp`: a real next-token language-modeling
training loop using:

- **Real tokenized text**: sentences from `benchmark/rstf/corpus.json`,
  encoded with the real trained BPE tokenizer (`tools/bpe_tokenizer.py` /
  `cpp/src/tokenizer.cpp`).
- **Real objective**: softmax cross-entropy on the next token, computed from
  `overllm_forward`'s logits and backpropagated via `overllm_backward`'s
  public API — the same functions DPO/RL training use.
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
| First epoch loss | 7.405 (matches `ln(1500)=7.31`, the theoretical loss of guessing uniformly over the vocabulary — confirms sane initialization) |
| Last epoch loss (30 epochs) | 5.198 |
| Reduction | 29.8% |
| NaN encountered | No |

Scope honesty: this is a memorization/overfitting demonstration on a tiny,
repeated corpus with a tiny model, not a claim of general language
understanding. What it proves: the backward pass and AdamW optimizer
genuinely perform gradient descent on real data — a testable, mechanically
checked claim (`tools/transformer_learning_check.py` asserts the loss
curve decreases and never hits NaN), not an assertion to take on faith.

## A real bug found and fixed while building this

The first version of this experiment (compiled with plain `-O2`) converged
cleanly. Run through this repo's actual CMake project — which builds
everything with `-O3 -ffast-math` — training instead **diverged to NaN
around epoch 15**. Investigating rather than just using the build that
happened to work: `cpp/src/model.cpp` had no gradient clipping anywhere in
its training path (`overllm_adamw_step`, `overllm_zero_grad`) — a standard
safeguard against exploding gradients that every real transformer training
setup uses, and this implementation simply didn't have it.

Added `overllm_clip_gradients(model, max_norm)` — computes the global L2
norm across every gradient buffer and rescales if it exceeds `max_norm` —
and call it between `overllm_backward` and `overllm_adamw_step`. Re-running
the exact same experiment through the real `-O3 -ffast-math` build after
the fix: stable convergence, no NaN, 29.8% loss reduction over 30 epochs
(a smaller reduction than the unclipped `-O2` run's 62.5%, since clipping
trades convergence speed for stability at this learning rate — a real,
expected trade-off, not a regression to paper over).

## Honest limits

- Tiny corpus (82 tokens), tiny model (`d_model=64`, 2 layers, ~0.4M
  parameters) — chosen for fast CPU iteration, not representative of a
  usable language model.
- No held-out evaluation set; this measures training-set loss only, so it
  cannot distinguish genuine generalization from memorization. For a corpus
  this small and repeated across many epochs, memorization is expected and
  is not a flaw in what's being tested here (whether the optimizer works).
- `overllm_clip_gradients`'s `max_norm=1.0` was chosen empirically to fix
  the observed NaN case, not tuned against a validation curve.
- This does not touch `cpp/train_online.cpp`'s random-token DPO loop, which
  remains a stress/crash test, not a learning demonstration; a real DPO
  learning experiment would need real chosen/rejected preference pairs,
  which is future work.
