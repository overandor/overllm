# RSTF byte-cost report (rstf-token-cost-v0.1)

Fingerprint version: `RSTF-1`

**Metric: `utf8_byte_length`.** UTF-8 byte length, not a real tokenizer count. It is a provable upper bound on token count for byte-level BPE tokenizers (a token is >=1 raw byte), computed offline because this environment's egress policy blocks the hosts tiktoken/Hugging Face tokenizers need (403 on openaipublic.blob.core.windows.net and huggingface.co).

## Overall

| Metric | Value |
|---|---|
| Examples | 160 |
| Raw UTF-8 bytes (total) | 9361 |
| Canonical UTF-8 bytes (total) | 6908 |
| Byte savings ratio | 26.2% |

## Per-transform

| Transform | Count | Raw bytes | Canonical bytes | Byte savings ratio |
|---|---|---|---|---|
| `bidi_override` | 40 | 1967 | 1727 | 12.2% |
| `homoglyph` | 40 | 2840 | 1727 | 39.2% |
| `reversed` | 40 | 1727 | 1727 | 0.0% |
| `upside_down` | 40 | 2827 | 1727 | 38.9% |

Note: `reversed` is expected to show ~0% byte savings — reordering bytes doesn't change how many there are. The savings come entirely from `upside_down` (multi-byte rotation glyphs), `homoglyph` (multi-byte Cyrillic/Greek confusables), and `bidi_override` (stripped 3-byte bidi control characters) collapsing to single-byte ASCII.

