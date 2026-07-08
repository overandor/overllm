# OverLLM RSTF C++ Package

This package turns the RSTF canonicalization benchmark into an embeddable C++17 module for model runners, gateways, and cost-control filters.

RSTF means **Reversible Semantic Transform Fingerprint**. The package canonicalizes text that has been transformed through reversible or visually confusing Unicode surfaces before it reaches expensive downstream inference.

## Why this exists

The merged Python benchmark in this repository showed that canonicalization reduced UTF-8 byte length on a 160-example synthetic corpus by 26.2% overall, with the strongest reductions on homoglyph and upside-down text. That result is a byte-cost proxy, not a real tokenizer-price claim.

The C++ package exists for the next step: move canonicalization into the low-latency path where model runners, SDKs, local agents, gateways, and edge services can normalize hostile or expensive text before it is sent to a tokenizer or model.

## Scope

Implemented deterministic surfaces:

- Bidi control stripping: removes U+202A..U+202E and U+2066..U+2069 control characters.
- Curated homoglyph collapse: maps common Cyrillic/Greek confusables back to ASCII.
- Curated upside-down recovery: maps upside-down glyphs back to ASCII and reverses the recovered sequence.
- Explicit reversal policy: plain reversal is not automatically inferred because `tset` could be either intentional text or reversed `test`. Use `--reverse` or `Options{.force_reverse = true}` only when an upstream transform receipt or caller policy says reversal is expected.

This is not a full Unicode security implementation. It is a packaged, testable, finance-ready baseline.

## Build

```bash
cd cpp/rstf
cmake -S . -B build
cmake --build build
ctest --test-dir build --output-on-failure
```

## CLI

```bash
./build/overllm-rstf "ʇsǝʇ"
./build/overllm-rstf --json "ʇsǝʇ"
./build/overllm-rstf --reverse "tset"
```

## API

```cpp
#include "overllm/rstf.hpp"

const auto fp = overllm::rstf::compute_fingerprint("ʇsǝʇ");
// fp.canonical_text == "test"
// fp.raw_utf8_bytes > fp.canonical_utf8_bytes
```

## Financing use

This package converts the research artifact into underwritable software inventory:

1. A buildable C++ library.
2. A command-line demonstrator.
3. Deterministic tests.
4. Byte-cost measurement fields.
5. A clean boundary between proven canonicalization and future real-tokenizer benchmarks.

The financing claim should be framed as: **OverLLM owns a reproducible canonicalization layer that can be benchmarked against model-runner cost, robustness, abuse filtering, and tokenizer pressure.** It should not be framed as guaranteed API savings until real tokenizer runs are added.
