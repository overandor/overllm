# RSTF Training Bootcamp

Purpose: convert the RSTF trajectory from a single benchmark into a training and evaluation curriculum for normalization-aware model runners.

This is not a claim that fine-tuning alone reduces API cost. API cost falls only when expensive transformed input is canonicalized before tokenization, or when a gateway/model policy learns to request/perform canonicalization before forwarding text into a costly model. Fine-tuning can improve recognition, routing, repair decisions, and refusal/abuse handling, but the cost-saving mechanism must live upstream of the billed tokenizer/model path.

## Core hypothesis

A model or gateway trained on dense transformed text can learn a new skill:

> Detect when surface complexity is reversible, recover canonical meaning, preserve a transform receipt, and avoid spending expensive reasoning tokens on preventable Unicode entropy.

## Dataset tracks

### Track A — Simple reversible transforms

- Plain reversal with explicit receipt.
- Upside-down glyph substitutions.
- Left-right mirrored ordering.
- Bidi control insertion.
- Fullwidth and compatibility forms.

### Track B — Homoglyph pressure

- Cyrillic confusables.
- Greek confusables.
- Mixed-script words.
- Domain and brand impersonation examples.
- High-density confusable paragraphs.

### Track C — Stacked transforms

- Upside-down plus reverse.
- Homoglyph plus bidi.
- Mirror plus homoglyph.
- Zero-width controls plus visible transform.
- Mixed normal and transformed spans.

### Track D — Recovery receipts

Each example should include:

```json
{
  "raw_text": "transformed input",
  "canonical_text": "recovered input",
  "transform_stack": ["homoglyph", "upside_down"],
  "raw_utf8_bytes": 0,
  "canonical_utf8_bytes": 0,
  "raw_token_count_by_model": {},
  "canonical_token_count_by_model": {},
  "semantic_equivalence": true,
  "risk_label": "benign|abuse|ambiguous|unknown",
  "difficulty": "low|medium|high|extreme"
}
```

The receipt is as important as the normalized text. It proves what changed and prevents silent mutation.

## Model-runner curriculum

The bootcamp should train and evaluate four behaviors:

1. **Recognize**: identify likely transform class.
2. **Recover**: produce canonical text or request a deterministic canonicalizer.
3. **Receipt**: preserve raw hash, transform path, and canonical hash.
4. **Route**: send canonical text to downstream inference only when safe and semantically equivalent.

## Evaluation metrics

- Canonical recovery accuracy.
- False-positive normalization rate on clean text.
- False-negative rate on transformed text.
- Semantic equivalence after recovery.
- Raw bytes versus canonical bytes.
- Raw tokens versus canonical tokens by tokenizer.
- Downstream task accuracy before/after canonicalization.
- Model latency before/after canonicalization.
- Abuse-detection accuracy before/after canonicalization.

## Cost-saving mechanism

The defensible sequence is:

1. User submits complex Unicode/transformed text.
2. Lightweight deterministic canonicalizer runs before expensive model call.
3. Gateway emits transform receipt.
4. Tokenizer sees canonical text instead of raw high-entropy surface.
5. Model reasons over recovered meaning instead of spending context on surface noise.
6. Cost and robustness are measured with real tokenizers and real model outcomes.

Fine-tuning can improve steps 1, 3, 4, and 5. It does not replace step 2 unless the fine-tuned model is itself running locally or cheaply enough to be part of the preprocessor.

## Bootcamp deliverables

- `benchmark/rstf/corpus_large.jsonl`: large synthetic corpus.
- `benchmark/rstf/tokenizer_cost_report.md`: real tokenizer report.
- `benchmark/rstf/semantic_recovery_report.md`: recovery accuracy report.
- `benchmark/rstf/router_policy_report.md`: decision quality report.
- `cpp/rstf`: embeddable C++ canonicalizer.
- `tools/rstf_dataset_generator.py`: reproducible data generator.
- `tools/rstf_tokenizer_benchmark.py`: model-specific tokenizer counter.

## Underwriting relevance

This bootcamp makes OverLLM financeable because it turns the idea into repeated evidence:

- More examples.
- More transforms.
- More tokenizers.
- More receipts.
- More measurable deltas.
- Clear separation between proven software behavior and future commercial savings.

The strongest financing milestone is not a pitch deck. It is a regenerable benchmark packet with real tokenizer counts and a buyer's model-gateway integration path.
