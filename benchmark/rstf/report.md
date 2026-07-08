# RSTF benchmark report (rstf-benchmark-v0.1)

Fingerprint version: `RSTF-1` | Corpus version: `rstf-benchmark-v0.1`

Synthetic, generated examples — not real-world traffic. See docs/SEMANTIC_TRANSFORM_FINGERPRINT.md for scope and limits.

## Overall

| Metric | Value |
|---|---|
| Examples | 160 |
| Raw hash divergence rate | 100.0% |
| Detection rate | 99.4% |
| Exact recovery rate | 99.4% |

## Per-transform

| Transform | Count | Raw hash divergence | Detection rate | Exact recovery rate |
|---|---|---|---|---|
| `bidi_override` | 40 | 100.0% | 100.0% | 100.0% |
| `homoglyph` | 40 | 100.0% | 100.0% | 100.0% |
| `reversed` | 40 | 100.0% | 97.5% | 97.5% |
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
| 8 | `reversed` | False | False |
