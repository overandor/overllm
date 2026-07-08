# RSTF benchmark report (rstf-benchmark-v0.1)

Fingerprint version: `RSTF-1` | Corpus version: `rstf-benchmark-v0.1`

Synthetic, generated examples — not real-world traffic. See docs/SEMANTIC_TRANSFORM_FINGERPRINT.md for scope and limits.

## Overall

| Metric | Value |
|---|---|
| Examples | 160 |
| Raw hash divergence rate | 100.0% |
| Detection rate | 95.6% |
| Exact recovery rate | 95.6% |

## Per-transform

| Transform | Count | Raw hash divergence | Detection rate | Exact recovery rate |
|---|---|---|---|---|
| `bidi_override` | 40 | 100.0% | 100.0% | 100.0% |
| `homoglyph` | 40 | 100.0% | 100.0% | 100.0% |
| `reversed` | 40 | 100.0% | 82.5% | 82.5% |
| `upside_down` | 40 | 100.0% | 100.0% | 100.0% |

## Control group (unmodified text)

Measures the false-positive ("false merge") rate: how often the detector flags a transform on text nobody transformed.

| Metric | Value |
|---|---|
| Examples | 40 |
| False positive rate | 0.0% |

## Failed examples


### Missed detections / imperfect recovery

| source_id | transform | detected | recovered_exact |
|---|---|---|---|
| 1 | `reversed` | False | False |
| 8 | `reversed` | False | False |
| 10 | `reversed` | False | False |
| 22 | `reversed` | False | False |
| 33 | `reversed` | False | False |
| 34 | `reversed` | False | False |
| 38 | `reversed` | False | False |
