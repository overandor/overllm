# RSTF dogfood scan (rstf-dogfood-scan-v0.1)

Fingerprint version: `RSTF-1`

Scanned this repository's own `.md` and `.py` files line-by-line - real text, not synthetic benchmark fixtures. This is not a customer pilot: nobody outside this repo supplied the input.

| Metric | Value |
|---|---|
| Files scanned | 66 |
| Non-blank lines scanned | 9042 |
| Total hits | 29 |
| Expected hits (within RSTF's own module/docs/benchmark/test files) | 28 |
| **Unexpected hits (elsewhere in the repo)** | **1** |

## Unexpected hits — needs review

| file | line | text | transform_receipt |
|---|---|---|---|
| lang/overml/docs/DESIGN.md | 160 | 'arithmetic, no OS randomness, no per-platform float rounding differences.' | `{'bidi_override': False, 'upside_down': False, 'reversed': True, 'homoglyph_substitution': False}` |
