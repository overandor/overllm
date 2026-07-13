# GlyphYieldBench v0

**Research Grade:** 3/4 (Primitive + Object Model + Compiler Plan + Benchmark Target)

## Core Object Model

A glyph is a fabricated computational object:

```
G = (M, P, V, K, L)
```

Where:
- **M** = visible_mask (what humans recognize)
- **P** = hidden_payload (machine-readable substrate)
- **V** = variance_field (legal deformation space)
- **K** = knot_state (transformation history)
- **L** = ledger (provenance and receipts)

## Benchmark Definition

**GlyphYieldBench** measures whether a fabricated glyph can carry more recoverable meaning per area without destroying human readability, machine recovery, or provenance.

```
GYB = w_h * R_h + w_m * R_m + w_p * S_p + w_a * D_a
```

Where:
- **R_h** = human readability
- **R_m** = machine payload recovery
- **S_p** = provenance survival
- **D_a** = meaning density per area

**Pass Condition:**
```
PASS = [R_h > θ_h] ∧ [R_m > θ_m] ∧ [S_p > θ_p] ∧ [D_a > θ_a]
```

## Project Structure

```
glyph_yield_bench/
├── README.md
├── glyph_core.py          # Core glyph object model
├── glyph_fabricator.py    # Glyph creation/compilation
├── distortion_engine.py   # Five distortion tests
├── readers.py             # Three readers (human, machine, ledger)
├── yield_benchmark.py     # Main benchmark runner
├── receipt_system.py       # Signed receipt generation
├── tests/
│   ├── test_glyph_core.py
│   ├── test_distortion.py
│   └── test_readers.py
└── results/
    └── yield.csv
```

## Next Milestone

Build GlyphYieldBench v0:
- One macro glyph
- One payload
- Five distortions
- Three readers
- One yield CSV
- One signed receipt

This turns the concept from metaphor into experiment.
