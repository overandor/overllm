# RSTF Real Corpus Cost Scan

Generated: `2026-07-08T19:08:18.846181+00:00`
Metric: `utf8_byte_length`
Truth label: `non_synthetic_real_input_rtf_scan_not_generated_attack_corpus`

## Overall

| Metric | Value |
|---|---:|
| Records scanned | 2391 |
| Records with transform detected | 5 |
| Transform prevalence | 0.21% |
| Raw units | 108463 |
| Canonical units | 108452 |
| Units saved | 11 |
| Overall savings ratio | 0.01% |

## RAM compression A/B

Compressor: `zlib_level_6`

| Metric | Value |
|---|---:|
| Raw UTF-8 bytes | 108463 |
| Canonical UTF-8 bytes | 108452 |
| UTF-8 bytes saved | 11 |
| UTF-8 savings ratio | 0.01% |
| Receipt JSON bytes | 870320 |
| Compressed raw bytes | 114750 |
| Compressed canonical bytes | 114733 |
| Compressed canonical+receipt bytes | 599292 |
| Hot-path compressed bytes saved | 17 |
| Hot-path compressed savings ratio | 0.01% |
| Audit-path compressed delta bytes | -484542 |
| Audit-path compressed delta ratio | -422.26% |

## Transformed records only

| Metric | Value |
|---|---:|
| Records | 5 |
| Units saved | 11 |
| Savings ratio | 4.62% |

## Per transform

| Transform | Count | Raw units | Canonical units | Units saved | Savings ratio |
|---|---:|---:|---:|---:|---:|
| `homoglyph` | 1 | 71 | 69 | 2 | 2.82% |
| `reversed` | 1 | 70 | 70 | 0 | 0.00% |
| `upside_down` | 3 | 97 | 88 | 9 | 9.28% |

## Scope

This scan uses real input records as-is. It does not generate attack examples. Low or zero savings on clean corpora is expected and should be interpreted as low observed prevalence, not detector failure. RAM compression metrics are an A/B probe using the selected lossless compressor, not an exact model of any OS memory compressor.
