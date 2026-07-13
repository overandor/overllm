# OverLLM Underwriting Package

Status: financing and diligence package, not a securities offering.

See also: [`docs/COMPETITIVE_LANDSCAPE_IMESSAGE_LENDING.md`](COMPETITIVE_LANDSCAPE_IMESSAGE_LENDING.md) for the competitive white-space analysis behind the iMessage-derived demand evidence wedge described in `docs/MAC_IMESSAGE_OLLAMA_MEMORY_OS.md`.

## Executive thesis

OverLLM becomes financeable when it is presented as a reproducible software asset with measurable technical evidence, not as an abstract LLM idea. The current underwritable wedge is **RSTF canonicalization**: a normalization layer that detects and recovers text transformed through upside-down glyphs, homoglyph substitution, bidi controls, and explicit transform receipts before expensive model execution.

The borrower/company story is simple:

> OverLLM reduces model-runner waste and robustness failures caused by adversarial, obfuscated, or high-entropy Unicode input by canonicalizing recoverable text before tokenization or inference.

## Underwritable asset

The asset is not the conversation history. The asset is the packaged system of evidence:

1. **Algorithmic primitive**: reversible semantic transform fingerprinting and canonical text recovery.
2. **Benchmark artifact**: synthetic corpus and byte-cost report showing canonicalization deltas.
3. **Implementation inventory**: Python reference implementation plus C++ package for embedding.
4. **Testing evidence**: deterministic regression tests for byte accounting and transform behavior.
5. **Commercial use case**: model gateway, LLM firewall, tokenizer pressure reducer, Unicode abuse filter, evaluation harness, and normalization-aware training dataset.

## Current evidence base

PR #15 converted the RSTF idea into a measurable benchmark. It added `tools/rstf_token_cost.py`, committed JSON/Markdown reports, and documented that the metric is UTF-8 byte length rather than real tokenizer count because live tokenizer vocabulary hosts were blocked in the execution environment.

Reported benchmark values:

| Transform | Byte savings ratio |
|---|---:|
| Homoglyph | 39.2% |
| Upside-down | 38.9% |
| Bidi override | 12.2% |
| Reversed | 0.0% |
| Overall | 26.2% |

The key diligence point is that `reversed` shows 0.0% byte savings. That is not a failure. It is a structural correctness control: reordering characters cannot change byte length. Nonzero savings there would indicate a benchmark bug.

## What can be financed

The financeable object is a staged commercialization package:

### Stage 1 — Diligence grant / prototype note

Use of funds:

- Port RSTF into C++ and package it as an embeddable model-runner component.
- Add CI builds on Linux/macOS.
- Add real-tokenizer benchmark adapters for tiktoken, Hugging Face tokenizers, llama.cpp tokenizers, and SentencePiece where licenses allow.
- Produce a signed benchmark packet with corpus hash, source commit, binary hash, report hash, and run metadata.

Repayment or value basis:

- Delivery of a reproducible package, not speculative revenue.
- Milestone acceptance by buyer, grant reviewer, internal R&D sponsor, or pilot customer.

### Stage 2 — Paid pilot

Use of funds:

- Integrate as an SDK or reverse proxy before LLM calls.
- Measure actual token deltas and error-rate deltas on customer traffic or approved synthetic corpora.
- Add policy logs for raw hash, canonical hash, transform receipt, and downstream token count.

Repayment or value basis:

- Pilot fee.
- Cost-savings share only after verified real-tokenizer or real-invoice data exists.

### Stage 3 — Enterprise component

Use of funds:

- Package as gateway middleware, C++ static library, Rust/Python bindings, and model-evaluation harness.
- Add enterprise reporting: normalization volume, transformed-input rate, recovered bytes/tokens, abuse classes, and model-error reduction.

Repayment or value basis:

- Annual license.
- Usage-based gateway fee.
- Security/compliance evaluation subscription.

## Underwriting checklist

A funder or buyer should be able to verify the following without trusting the founder's narrative:

- Repository URL and commit hash.
- Build commands complete successfully.
- Tests pass.
- Benchmark corpus is present.
- Benchmark report can be regenerated.
- Raw and canonical byte counts match report values.
- No dollar-cost claim is made without real tokenizer or invoice data.
- Security limits are stated clearly: curated tables, not exhaustive Unicode confusables; simplified bidi handling, not full UAX #9; synthetic examples, not production adversarial coverage.

## Collateral framing

This is not bank collateral in the traditional sense unless a lender accepts software/IP receivables. The stronger framing is **technical diligence collateral**:

- Code inventory.
- Test inventory.
- Benchmark inventory.
- Reproducibility receipts.
- Commercial pilot plan.
- Buyer-specific integration path.

A realistic lender/investor will not underwrite against the idea alone. They may underwrite against deliverables, contracts, grants, signed pilots, or receivables created from this package.

## Financing scorecard

| Category | Status | Diligence comment |
|---|---|---|
| Technical novelty | Medium-high | Unicode canonicalization exists generally; RSTF's specific transform-receipt + cost benchmark framing is differentiated. |
| Reproducibility | Medium | Python benchmark exists; C++ package and CI should raise this to high. |
| Revenue proof | Low | No customer contract or invoice yet. |
| Cost-saving proof | Medium-low | Byte proxy exists; real tokenizer benchmark still required. |
| Risk disclosure | High | Current docs correctly avoid fake token-price claims. |
| Finance readiness | Medium | Strong enough for grant/prototype/pilot financing; not yet enough for revenue-backed underwriting. |

## Required next artifacts

1. `cpp/rstf` build and tests.
2. CI workflow for the C++ package.
3. Tokenizer benchmark adapters.
4. `benchmark/rstf/tokenizer_cost_report.md` with model-specific token counts.
5. Signed receipts: corpus hash, source hash, binary hash, report hash.
6. One buyer-facing pilot page: "Install this before your LLM gateway and measure recovered tokens/errors."

## Clean claim language

Use this:

> OverLLM RSTF has demonstrated a 26.2% UTF-8 byte reduction on a 160-example synthetic transform corpus and is being packaged as a C++ model-runner normalization layer. The next milestone is real-tokenizer and real-traffic validation.

Do not use this yet:

> OverLLM reduces API bills by 26.2%.

That statement is not proven until real tokenizer counts and production traffic measurements exist.
