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

## Test

```bash
python -m pytest tests/test_rstf_cost_pipeline.py -v
```
