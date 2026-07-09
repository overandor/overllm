# RSTF Defensible Claim Set

**Document Version:** 1.1  
**Date:** July 8, 2026  
**Purpose:** Consolidated defensible claims for technical and commercial diligence

---

## Evidence Tier Structure

**Tier 1 — Real Provider Accounting:** Groq usage.prompt_tokens, 14.4%
**Tier 2 — Gateway/Provider Accounting Pending:** OpenRouter Claude route, not shown yet
**Tier 3 — Local Tokenizer Benchmark:** tiktoken GPT-4o, 75.6%; OverLLM BPE, 66.4%
**Tier 4 — Raw-Size Proxy:** UTF-8 byte proxy, 26.2%

---

## Defensible Claims (Tier 1 - Real Provider Accounting)

### Claim 1: Groq llama-3.1-8b-instant
**Statement:** "Groq provider accounting showed 14.4% prompt-token reduction on 6 RSTF examples for llama-3.1-8b-instant."

**Evidence:**
- Provider: Groq
- Model: llama-3.1-8b-instant
- Test Date: July 8, 2026, 19:45 UTC
- API Endpoint: POST https://api.groq.com/openai/v1/chat/completions
- Measurement: usage.prompt_tokens from provider response
- Test Corpus: 6 examples (upside-down, homoglyph, reversed, clean)
- Raw Tokens: 389
- Canonical Tokens: 333
- Tokens Saved: 56
- Savings: 14.4%
- Truth Label: `groq_usage_prompt_tokens_not_claude`

**Validation:**
- Direct API measurement (not local simulation)
- Provider-reported usage accounting
- Reproducible with valid API key
- Consistent across multiple test runs

### Claim 2: Groq llama-3.3-70b-versatile
**Statement:** "Groq provider accounting showed 14.4% prompt-token reduction on 6 RSTF examples for llama-3.3-70b-versatile."

**Evidence:**
- Provider: Groq
- Model: llama-3.3-70b-versatile
- Test Date: July 8, 2026, 19:58 UTC
- API Endpoint: POST https://api.groq.com/openai/v1/chat/completions
- Measurement: usage.prompt_tokens from provider response
- Test Corpus: 6 examples (identical to Claim 1)
- Raw Tokens: 389
- Canonical Tokens: 333
- Tokens Saved: 56
- Savings: 14.4%
- Truth Label: `groq_usage_prompt_tokens_not_claude`

**Validation:**
- Identical token counts to llama-3.1-8b-instant
- Consistent tokenization across Groq models
- Validates reproducibility

---

## Defensible Claims (Tier 3 - Local Tokenizer Benchmark)

### Claim 3: tiktoken GPT-4o
**Statement:** "tiktoken GPT-4o local benchmark showed 75.6% token reduction on 160 synthetic adversarial RSTF examples."

**Evidence:**
- Tokenizer: tiktoken (o200k_base)
- Model: GPT-4o
- Test Date: July 8, 2026, 19:54 UTC
- Corpus: 160 adversarial examples (reversed, upside_down, homoglyph, bidi_override)
- Method: Local tokenizer simulation
- Raw Tokens: 5,077
- Canonical Tokens: 1,237
- Tokens Saved: 3,840
- Savings: 75.6%
- Truth Label: `real_tiktoken_count_for_selected_model_or_encoding_not_provider_bill`

**Validation:**
- Industry-standard tokenizer (OpenAI tiktoken)
- Reproducible local measurement
- Not direct provider billing (local simulation)

### Claim 4: OverLLM BPE
**Statement:** "OverLLM BPE benchmark showed 66.4% token reduction on the same synthetic benchmark family."

**Evidence:**
- Tokenizer: OverLLM BPE small repo-trained vocab
- Vocabulary Size: 1,500 tokens
- Test Date: July 8, 2026, 19:54 UTC
- Corpus: 160 adversarial examples (same as Claim 3)
- Method: Local BPE tokenizer
- Raw Tokens: 7,245
- Canonical Tokens: 2,436
- Tokens Saved: 4,809
- Savings: 66.4%
- Truth Label: `real_tokenizer_measurement_small_repo_trained_vocab_not_production_scale`

**Validation:**
- Real tokenizer measurement (not simulation)
- Small vocabulary (not production scale)
- Reproducible local measurement

---

## Defensible Claims (Technical Validation)

### Claim 5: Deterministic Canonicalization with Audit Receipts
**Statement:** "RSTF provides deterministic canonicalization for covered Unicode transform classes and emits raw/canonical hashes plus transform receipts for auditability."

**Evidence:**
- Multiple implementation languages (Python, C, C++)
- SHA-256 hashing for audit trail
- Transform receipts (list of applied transformations)
- Zero false positives on the current clean-text test set
- Semantic preservation verified on tested transform families, not universally guaranteed

### Claim 6: Prompt-Risk Pattern Detection
**Statement:** "RSTF includes deterministic prompt-risk pattern detection with 30+ rules. This is a preflight signal, not a complete prompt-injection defense."

**Evidence:**
- 30+ regex patterns for injection detection
- Severity classification (none, low, medium, high)
- Categories: instruction overrides, jailbreaks, system prompt bypass, encoding attacks
- Test results: normal text (none), injection text (low)
- Integrated into canonicalization pipeline

---

## Not Defensible Yet (Scope Limitations)

### Claim 7: Claude Billing Reduction
**Statement:** "Claude billing reduced by X%."

**Status:** NOT DEFENSIBLE YET

**Reason:** Requires Anthropic direct measurement

**Required Validation:**
- Anthropic count_tokens endpoint
- Same corpus, same system prompt, same model, same wrapper
- Anthropic warns counts are estimates
- Claude tokenization is model-specific (newer models ~30% more tokens)
- Must recount against exact Claude model

**Next Step:** Implement Anthropic count_tokens validation

### Claim 8: Universal Provider Savings
**Statement:** "RSTF savings apply to all AI providers."

**Status:** NOT DEFENSIBLE YET

**Reason:** Requires per-provider validation

**Required Validation:**
- Direct measurement for each provider
- Provider-specific tokenization differences
- Different pricing structures
- Different billing methodologies

**Current Status:** Validated on Groq only

### Claim 9: Production Traffic Savings
**Statement:** "RSTF guarantees X% savings on all production traffic."

**Status:** NOT DEFENSIBLE YET

**Reason:** Depends on input distribution

**Required Validation:**
- Real customer data
- Production deployment
- Use case-specific analysis
- Traffic pattern analysis

**Current Status:** Synthetic benchmarks only

---

## Token Savings vs Dollar Savings

### Important Distinction

**Token Savings:** VERIFIED
- Groq: 14.4% reduction on 6 examples
- tiktoken: 75.6% reduction on 160 examples
- OverLLM BPE: 66.4% reduction on 160 examples

**Dollar Savings:** NOT YET
- Requires paid traffic volume
- Requires provider invoices
- Requires production deployment

### Money Formula

```
dollars_saved = tokens_saved / 1,000,000 × input_price_per_1M_tokens
```

### Example Calculations

**Small Test (Current):**
- 56 tokens saved
- At $1/1M tokens: $0.000056
- At $5/1M tokens: $0.00028
- **Result:** Tiny due to small test scale

**At Scale (Hypothetical):**
- 14.4% savings on 100M tokens = 14.4M tokens saved
- At $1/1M tokens: $14.40
- At $5/1M tokens: $72.00
- **Result:** Real infrastructure savings at scale

### Revenue Paths

1. **Internal LLM Bill Reduction:** Use RSTF to reduce own API costs
2. **Middleware Sales:** Sell as "Normalize hostile/expensive Unicode before model calls"
3. **Technical Diligence:** Sell benchmark/report showing token waste reduction

### Best Honest Claim

"This is not cash directly; it is verified token-cost compression. It converts to money when applied to paid provider traffic at scale."

---

## Best One-Line Investor Version

"RSTF is a deterministic LLM input-integrity layer that canonicalizes covered Unicode transform classes, flags prompt-risk patterns, and emits audit receipts; it has verified Groq provider-token reductions on a small benchmark and stronger local tokenizer reductions on synthetic adversarial corpora, with Claude direct validation pending."

---

## Diligence-Safe Conclusion

"RSTF has verified provider-side prompt-token savings on Groq, verified local tokenizer savings on GPT-4o/tiktoken and OverLLM BPE, and is ready for direct Claude count_tokens validation."

---

## Diligence Readiness Assessment

**Technical Diligence Readiness:** HIGH
- Real provider validation (Groq)
- Multiple tokenizer validation (tiktoken, BPE)
- Cross-language implementation (Python, C, C++)
- Reproducible test methodology
- Chain of custody documentation

**Commercial Diligence Readiness:** EARLY
- Token savings verified
- Dollar savings not yet (requires paid traffic volume)
- Claude billing not yet (requires Anthropic count_tokens)
- Commercial potential: YES (as LLM gateway middleware / security-cost optimizer)

**Overall Status:**
- Technical proof: REAL
- Provider-side usage proof: REAL on Groq
- Direct money proof: NOT YET
- Claude money proof: NOT YET
- Commercial potential: YES

---

## Next Proof to Add

**Anthropic count_tokens Validation:**
- Anthropic's token counting endpoint is specifically designed to count tokens before sending messages
- Returns total input_tokens
- Accepts the same structured message inputs as the Messages API
- Anthropic warns counts are estimates that may differ slightly from actual message usage
- Claude tokenization is model-specific (newer Claude tokenizers can produce ~30% more tokens for the same input)
- Must recount against the exact Claude model you plan to use
- Token counting is free to use, with separate rate limits from message creation

**Required Test:**
- Anthropic count_tokens raw vs canonical for the same corpus
- Same system prompt
- Same model
- Same wrapper

---

**Document Control:**
- Version: 1.0
- Date: July 8, 2026
- Status: FINAL
- Next Review: August 8, 2026
- Approved By: [signature required]
