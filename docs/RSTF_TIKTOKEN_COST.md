# RSTF tiktoken token-cost benchmark

`tools/rstf_tiktoken_cost.py` adds a third RSTF cost view:

1. `tools/rstf_token_cost.py` — offline UTF-8 byte upper-bound proxy when external tokenizers are unavailable.
2. `tools/rstf_bpe_token_cost.py` — real token counts under OverLLM's small repo-trained BPE tokenizer.
3. `tools/rstf_tiktoken_cost.py` — real tiktoken counts for a selected OpenAI model or encoding when `tiktoken` is installed.

## Install

```bash
pip install tiktoken
```

## Run

```bash
python tools/rstf_tiktoken_cost.py --summary-only
python tools/rstf_tiktoken_cost.py --model gpt-4o-mini --summary-only
python tools/rstf_tiktoken_cost.py --encoding cl100k_base --out-md benchmark/rstf/tiktoken_cost_report.md
```

## Pricing

The tool does not hard-code provider pricing. Pass current model-specific input pricing manually when you want a cost estimate:

```bash
python tools/rstf_tiktoken_cost.py --input-price-per-1m 0.15 --summary-only
```

The cost estimate truth label is:

```text
user_supplied_price_not_live_provider_pricing
```

## Truth boundary

The benchmark reports real tiktoken counts for the selected model or encoding. It does not claim universal provider billing. Actual API cost depends on the current provider pricing table, selected model, cached input treatment, output tokens, service mode, batching, tool use, and deployment details.

Primary truth label:

```text
real_tiktoken_count_for_selected_model_or_encoding_not_provider_bill
```
