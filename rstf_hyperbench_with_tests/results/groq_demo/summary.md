# RSTF HyperBench Summary

Truth label: `benchmark_summary_see_row_truth_labels`

## Overall

| Metric | Value |
|---|---:|
| Measurements | 60 |
| Raw prompt tokens | 8017 |
| Canonical prompt tokens | 4220 |
| Tokens saved | 3797 |
| Savings ratio | 47.36% |

## By model and transform

| Model / transform | Count | Raw | Canonical | Saved | Savings | With savings | Unchanged/worse |
|---|---:|---:|---:|---:|---:|---:|---:|
| `llama-3.1-8b-instant::bidi_override` | 10 | 729 | 699 | 30 | 4.12% | 10 | 0 |
| `llama-3.1-8b-instant::clean` | 10 | 721 | 721 | 0 | 0.00% | 0 | 10 |
| `llama-3.1-8b-instant::homoglyph` | 10 | 1437 | 696 | 741 | 51.57% | 10 | 0 |
| `llama-3.1-8b-instant::reversed_forced` | 10 | 936 | 676 | 260 | 27.78% | 10 | 0 |
| `llama-3.1-8b-instant::stacked_upside_homoglyph` | 10 | 1967 | 719 | 1248 | 63.45% | 10 | 0 |
| `llama-3.1-8b-instant::upside_down` | 10 | 2227 | 709 | 1518 | 68.16% | 10 | 0 |
