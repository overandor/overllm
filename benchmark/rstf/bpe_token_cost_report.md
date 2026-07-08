# RSTF real-BPE token-cost report (rstf-bpe-token-cost-v0.1)

Fingerprint version: `RSTF-1` | Tokenizer vocab size: `1500` | Merges: `1244`

**Metric: `overllm_bpe_token_count`.** Real token counts from OverLLM's own trained BPE tokenizer (tools/bpe_tokenizer.py, C++ mirror in cpp/src/tokenizer.cpp, parity-verified by tools/bpe_parity_check.py). This is OverLLM's own tokenizer trained on this repo's own docs (a few tens of KB), not GPT-4/Claude/Llama's production tokenizer - absolute counts do not represent production API billing, but the measurement method (a real, working byte-level BPE tokenizer) is genuine, not a byte-length proxy.

## Overall

| Metric | Value |
|---|---|
| Examples | 160 |
| Raw tokens (total) | 7245 |
| Canonical tokens (total) | 2436 |
| Token savings ratio | 66.4% |

## Per-transform

| Transform | Count | Raw tokens | Canonical tokens | Token savings ratio |
|---|---|---|---|---|
| `bidi_override` | 40 | 1026 | 585 | 43.0% |
| `homoglyph` | 40 | 2764 | 585 | 78.8% |
| `reversed` | 40 | 1117 | 681 | 39.0% |
| `upside_down` | 40 | 2338 | 585 | 75.0% |

