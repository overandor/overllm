# RSTF Cost Reduction Comparison

**Generated:** 2026-07-08T14:15:00Z  
**Test Corpus:** 160 RSTF adversarial examples (reversed, upside_down, homoglyph, bidi_override)  
**Truth Label:** `synthetic_rstf_corpus_multi_tokenizer_cost_observability_not_production_traffic_guarantee`

## Headline Finding

On a 160-example synthetic reversible-transform corpus, RSTF canonicalization reduced measured input tokens by 75.6-78.0% under selected tiktoken encodings, 66.4% under OverLLM's repo-trained BPE tokenizer, and 26.2% under an offline UTF-8 byte upper-bound proxy. These results demonstrate tokenizer-aware cost observability for transformed/adversarial text, not guaranteed savings on arbitrary production traffic.

## Buyer-Facing Summary

RSTF provides tokenizer-aware cost observability for transformed or adversarial Unicode text. In the repo's 160-example synthetic benchmark, canonicalization reduced measured tiktoken input counts by 75.6-78.0% and OverLLM BPE counts by 66.4%, while the offline UTF-8 proxy showed 26.2% byte reduction. Production savings depend on the prevalence of these transformed inputs, the selected tokenizer/model, and current provider pricing. The byte proxy does not mean "local models show 26.2% token savings." It means the canonicalized strings are 26.2% shorter in UTF-8 bytes. Exact token savings still require the target tokenizer.

## Model Results

### GPT-4 (tiktoken cl100k_base)

| Metric | Value |
|---|---|
| Raw tokens | 5662 |
| Canonical tokens | 1245 |
| Tokens saved | 4417 |
| Savings ratio | 78.0% |
| Estimated cost saved | N/A (pricing required) |
| Pricing source | user_supplied_required |

### GPT-3.5-turbo (tiktoken cl100k_base)

| Metric | Value |
|---|---|
| Raw tokens | 5662 |
| Canonical tokens | 1245 |
| Tokens saved | 4417 |
| Savings ratio | 78.0% |
| Estimated cost saved | N/A (pricing required) |
| Pricing source | user_supplied_required |

### GPT-4o (tiktoken o200k_base)

| Metric | Value |
|---|---|
| Raw tokens | 5077 |
| Canonical tokens | 1237 |
| Tokens saved | 3840 |
| Savings ratio | 75.6% |
| Estimated cost saved | $0.0096 |
| Pricing per 1M tokens | $2.50 |
| Pricing source | user_supplied_not_live_provider_pricing |

### GPT-4o-mini (tiktoken o200k_base)

| Metric | Value |
|---|---|
| Raw tokens | 5077 |
| Canonical tokens | 1237 |
| Tokens saved | 3840 |
| Savings ratio | 75.6% |
| Estimated cost saved | $0.000576 |
| Pricing per 1M tokens | $0.15 |
| Pricing source | user_supplied_not_live_provider_pricing |

### UTF-8 Byte Proxy (offline upper-bound)

| Metric | Value |
|---|---|
| Raw bytes | 9361 |
| Canonical bytes | 6908 |
| Bytes saved | 2453 |
| Savings ratio | 26.2% |
| Note | This is not a tokenizer-specific count and does not prove Llama/Mistral billing savings. The canonicalized strings are 26.2% shorter in UTF-8 bytes. |
| Truth label | `synthetic_examples_utf8_byte_upper_bound_proxy_not_real_tokenizer_counts` |

### OverLLM BPE (reference implementation)

| Metric | Value |
|---|---|
| Raw tokens | 7245 |
| Canonical tokens | 2436 |
| Tokens saved | 4809 |
| Savings ratio | 66.4% |
| Vocab size | 1500 |
| Merge count | 1244 |
| Note | Real BPE tokenizer, not production scale |
| Truth label | `real_tokenizer_measurement_small_repo_trained_vocab_not_production_scale` |

## Key Findings

- On the repo's 160 synthetic RSTF adversarial examples, selected OpenAI tiktoken encodings showed 75-78% input-token reduction after canonicalization
- GPT-4o uses o200k_base encoding (more efficient than cl100k_base), still achieves 75.6% savings on the benchmark corpus
- The offline UTF-8 byte proxy shows 26.2% byte-length reduction; this is not a tokenizer-specific count and does not prove Llama/Mistral billing savings
- OverLLM BPE reference shows 66.4% token savings on the benchmark corpus (real BPE measurement, not production-scale)
- Highest savings come from upside_down (88-89%) and homoglyph (79-83%) transforms
- Reversed transform shows lower but still significant savings (45-49%) for real tokenizers
- Cost savings scale with model pricing: GPT-4o saves $0.0096 vs GPT-4o-mini saves $0.000576 for same corpus (user-supplied pricing, not live provider pricing)

## Transform Breakdown

### upside_down
- **Description:** Multi-byte rotation glyphs collapsed to ASCII
- **tiktoken savings:** 88-89%
- **byte proxy savings:** 38.9%
- **BPE savings:** 75.0%

### homoglyph
- **Description:** Cyrillic/Greek confusables normalized to ASCII
- **tiktoken savings:** 79-83%
- **byte proxy savings:** 39.2%
- **BPE savings:** 78.8%

### bidi_override
- **Description:** Bidi control characters (3 bytes) stripped
- **tiktoken savings:** 47-54%
- **byte proxy savings:** 12.2%
- **BPE savings:** 43.0%

### reversed
- **Description:** Text reordering (bytes unchanged, tokens change)
- **tiktoken savings:** 45-49%
- **byte proxy savings:** 0.0%
- **BPE savings:** 39.0%

## Truth Labels

- **tiktoken:** `real_tiktoken_count_for_selected_model_or_encoding_not_provider_bill`
- **byte_proxy:** `synthetic_examples_utf8_byte_upper_bound_proxy_not_real_tokenizer_counts`
- **bpe:** `real_tokenizer_measurement_small_repo_trained_vocab_not_production_scale`

## Pricing Disclaimer

Cost estimates use user-supplied pricing, not live provider pricing. Actual bills depend on cached input, tools usage, batching mode, priority mode, and current provider pricing tables.

## Tiktoken Billing Note

This uses OpenAI's tiktoken encoding for the selected model/encoding. It measures input tokens, but final billing still depends on the provider's current pricing, cached input behavior, tools, batching, output tokens, and service mode.
