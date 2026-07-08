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

### OpenAI tiktoken measurements

- **GPT-4o**: 75.6% input-token reduction, 5077 → 1237 tokens, 3840 saved.
- **GPT-4o-mini**: 75.6% input-token reduction, 5077 → 1237 tokens, 3840 saved.
- **GPT-4 / GPT-3.5-turbo**: 78.0% input-token reduction, 5662 → 1245 tokens, 4417 saved.

### Offline byte proxy

- **UTF-8 byte proxy**: 26.2% byte reduction, 9361 → 6908 bytes, 2453 saved.
- This is an upper-bound proxy only, not model-specific token savings.

### Reference implementation

- **OverLLM BPE**: 66.4% token reduction, 7245 → 2436 tokens, 4809 saved.
- Real BPE measurement using a small repo-trained vocabulary.

### Transform breakdown

- **upside_down**: 88.1% tiktoken, 38.9% bytes, 75.0% BPE.
- **homoglyph**: 79.2% tiktoken, 39.2% bytes, 78.8% BPE.
- **bidi_override**: 46.6% tiktoken, 12.2% bytes, 43.0% BPE.
- **reversed**: 44.8% tiktoken, 0.0% bytes, 39.0% BPE.

### Scope

These are benchmark results on a synthetic reversible-transform corpus, not guaranteed production traffic savings. Production savings depend on the prevalence of transformed inputs, selected tokenizer/model, current provider pricing, cached input behavior, tools, batching, output tokens, and service mode.

### Buyer-safe claim

**Use this:**

```text
RSTF demonstrated 75.6–78.0% measured input-token reduction under selected tiktoken encodings on a 160-example synthetic adversarial corpus.
```

**Do not say:**

```text
RSTF reduces OpenAI bills by 78%.
```

**Say:**

```text
RSTF exposes and reduces token waste in transformed/adversarial Unicode inputs; production savings depend on the input distribution and provider billing rules.
```

## Test

```bash
python -m pytest tests/test_rstf_cost_pipeline.py -v
```
