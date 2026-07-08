# RSTF comparative cost pipeline

`tools/rstf_cost_pipeline.py` runs the full RSTF cost-observability stack and emits one comparative report.

It combines:

1. `tools/rstf_token_cost.py` — UTF-8 byte upper-bound proxy.
2. `tools/rstf_bpe_token_cost.py` — real OverLLM repo-trained BPE token counts.
3. `tools/rstf_tiktoken_cost.py` — real tiktoken counts for selected OpenAI model/encoding.

## Run

```bash
python tools/rstf_cost_pipeline.py
```

Default outputs:

```text
benchmark/rstf/comparative_cost_report.json
benchmark/rstf/comparative_cost_report.md
```

## Select tiktoken models

```bash
python tools/rstf_cost_pipeline.py \
  --tiktoken-model gpt-4o \
  --tiktoken-model gpt-4o-mini
```

## Add caller-supplied pricing

Pricing is never fetched live or hard-coded. Pass input pricing per 1M tokens manually:

```bash
python tools/rstf_cost_pipeline.py \
  --tiktoken-model gpt-4o \
  --tiktoken-model gpt-4o-mini \
  --price gpt-4o=2.50 \
  --price gpt-4o-mini=0.15
```

Cost estimates are truth-labeled:

```text
user_supplied_price_not_live_provider_pricing
```

## Truth label

The full comparative report truth label is:

```text
synthetic_rstf_corpus_multi_tokenizer_cost_observability_not_production_traffic_guarantee
```

## Buyer-safe claim

Use this:

```text
On the synthetic 160-example RSTF corpus, the pipeline compares UTF-8 byte reduction, OverLLM local BPE token reduction, and tiktoken model/encoding-specific token reduction. The results demonstrate tokenizer-aware cost observability for transformed/adversarial text, not guaranteed savings on arbitrary production traffic.
```

Do not use this:

```text
RSTF cuts every LLM bill by 78%.
```

## Cost reduction numbers

These results come from a 160-example synthetic RSTF benchmark covering four reversible/adversarial transform classes: reversed, upside_down, homoglyph, and bidi_override.

### OpenAI Models / Encodings via tiktoken

- **GPT-4o**: 75.6% input-token reduction
  - 5,077 raw tokens → 1,237 canonical tokens; 3,840 tokens saved.
  - Estimated input cost saved: $0.0096 at user-supplied pricing of $2.50 per 1M input tokens.
- **GPT-4o-mini**: 75.6% input-token reduction
  - 5,077 raw tokens → 1,237 canonical tokens; 3,840 tokens saved.
  - Estimated input cost saved: $0.000576 at user-supplied pricing of $0.15 per 1M input tokens.
- **GPT-4 / GPT-3.5-turbo**: 78.0% input-token reduction
  - 5,662 raw tokens → 1,245 canonical tokens; 4,417 tokens saved.

### Offline Byte Proxy

- **UTF-8 byte-length proxy**: 26.2% byte reduction
  - 9,361 raw bytes → 6,908 canonical bytes; 2,453 bytes saved.
  - This is an offline byte-length proxy, not a model-specific tokenizer count and not proof of Llama, Mistral, or other local-model billing savings.

### Reference Implementation

- **OverLLM BPE**: 66.4% token reduction
  - 7,245 raw tokens → 2,436 canonical tokens; 4,809 tokens saved.
  - This is a real BPE measurement using OverLLM's small repo-trained vocabulary of 1,500 tokens, not production-provider billing.

### Transform Breakdown

- **upside_down**: 88.1% tiktoken reduction; 38.9% byte reduction; 75.0% OverLLM BPE reduction.
- **homoglyph**: 79.2% tiktoken reduction; 39.2% byte reduction; 78.8% OverLLM BPE reduction.
- **bidi_override**: 46.6% tiktoken reduction; 12.2% byte reduction; 43.0% OverLLM BPE reduction.
- **reversed**: 44.8% tiktoken reduction; 0.0% byte reduction; 39.0% OverLLM BPE reduction.

### Scope

On this synthetic reversible-transform corpus, RSTF canonicalization reduced measured input tokens by 75.6–78.0% under selected tiktoken encodings and 66.4% under OverLLM's repo-trained BPE tokenizer. The offline UTF-8 proxy showed 26.2% byte reduction. These results demonstrate tokenizer-aware cost observability for transformed or adversarial Unicode text, not guaranteed savings on arbitrary production traffic or final provider invoices.

Production savings depend on the prevalence of transformed inputs, the selected tokenizer/model, cached-input behavior, output tokens, tool usage, batching/service mode, and current provider pricing.

## Test

```bash
python -m pytest tests/test_rstf_cost_pipeline.py -v
```
