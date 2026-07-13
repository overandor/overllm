# RSTF Enterprise Positioning

**Document Version:** 1.0  
**Date:** July 8, 2026  
**Positioning:** Security-first, audit-second, cost-third

---

## Executive Summary

RSTF is a deterministic LLM input-integrity layer that canonicalizes visually deceptive Unicode, flags prompt-injection patterns, and emits audit receipts before text reaches expensive or privileged AI systems.

**Serious One-Line Pitch:**
"RSTF is a deterministic LLM input-control layer that detects transformed Unicode, canonicalizes recoverable text, and emits evidence receipts for prompt-risk and token-cost analysis."

---

## What It Is

**RSTF is a Unicode normalization and prompt-risk preprocessor for LLM gateways.**

It does three boring useful things:

1. **Detects weird Unicode before the model sees it**
   - Homoglyphs (Аpple → Apple)
   - Upside-down text (ʇsǝʇ → test)
   - Bidirectional controls
   - Zero-width characters
   - Encoding obfuscation

2. **Canonicalizes recoverable transformed text**
   - Reversible transformations
   - Semantic preservation
   - Hash-based audit trail
   - Transform receipts

3. **Records token/cost/security deltas for audit**
   - Provider-measured token deltas
   - Prompt-injection pattern detection
   - Severity classification
   - CSV evidence ledger

---

## What It Is Not

**RSTF is NOT:**
- A universal cost saver
- A Claude billing claim
- A replacement for LLM security
- A magic shield against all attacks
- A guaranteed savings product

**RSTF does NOT:**
- Promise specific dollar savings
- Replace model-level guardrails
- Solve all prompt injection
- Guarantee zero false positives
- Replace human review

---

## Where It Sits

**Deployment Positions:**
- Before model gateway
- RAG ingestion pipeline
- Support-chat intake
- Agent tool-use boundary
- CI/CD code review
- Document processing

**Integration Points:**
- LLM gateway middleware
- API proxy layer
- Webhook preprocessor
- Serverless function
- C/C++ library
- CLI tool

---

## Why Now

**Market Drivers:**

1. **LLM Input Costs Rising**
   - Enterprises incurring large LLM usage costs
   - Research on token-reduction heuristics active
   - Cost optimization recognized enterprise problem

2. **Prompt Injection Risk**
   - OWASP/NCSC recognize as major LLM application security issue
   - Innocuous-looking inputs cause unintended model behavior
   - Mitigations include input/output filtering, least privilege, isolation

3. **Unicode Security Concerns**
   - Trojan Source showed bidi characters can hide malicious intent
   - Unicode confusables make text look familiar while changing codepoints
   - Research shows non-standard Unicode reduces guardrail efficacy across GPT-4, Gemini, Llama, Claude

---

## Evidence Stack

**Tier 1 — Security Value:**
- Detects and normalizes Unicode obfuscation before LLM processing
- 30+ prompt-injection detection patterns
- Severity classification (none, low, medium, high)
- Reversible transformations with audit trail

**Tier 2 — Audit Value:**
- Produces raw/canonical hashes
- Transform receipts
- Evidence CSV ledger
- Chain of custody documentation

**Tier 3 — Cost Value:**
- Provider-measured token delta on Groq (14.4% on 6 examples)
- Local tokenizer reductions on adversarial corpora (tiktoken 75.6%, BPE 66.4%)
- UTF-8 byte proxy (26.2%)
- **Note:** Actual savings depend on traffic mix and model tokenizer

**Tier 4 — Deployment Value:**
- Gateway middleware
- CLI tool
- C/C++ library
- Netlify/Vercel endpoint
- CI scanner

---

## Missing Proof

**Not Yet Validated:**
- Customer traffic on production systems
- Claude direct count_tokens validation
- Production false-positive rates
- Enterprise false-negative rates
- Real-world attack detection rate

**Required for Production:**
- Live gateway integration
- Customer traffic analysis
- Anthropic count_tokens validation
- Security audit (SOC 2, penetration testing)
- Customer case studies

---

## Honest Maturity Label

**Current Status:**
- Prototype with verified benchmarks
- Pilot-ready after live gateway integration
- Not yet production-validated on customer traffic

**Maturity Level:**
- Technical: Prototype
- Security: Verified patterns, not production-tested
- Commercial: Pilot-ready
- Evidence: Strong technical proof, medium commercial proof

---

## Commercial Wedge

**Paid Pilot: $1,500 LLM Input Risk Assessment**

**Deliverable:**
A private report on up to 10,000 prompts/documents with:
- Raw vs canonical hashes
- Unicode obfuscation findings
- Prompt-injection pattern findings
- Severity breakdown
- Provider token deltas
- Recommended gateway policy
- CSV evidence bundle
- Executive summary

**Duration:** 2 weeks
**Includes:** Gateway integration support, policy configuration, team training

---

## Target Customers

**Primary:**
- AI security teams
- LLM gateway vendors
- Agent platforms
- SOC teams experimenting with AI
- Compliance teams reviewing AI inputs
- Companies using AI coding agents

**Secondary:**
- SaaS platforms with user-generated content
- Content moderation teams
- Enterprise AI platforms
- AI chatbot providers

---

## Credible Positioning

**Not:**
"We save 75% of your LLM bill."

**Instead:**
"We add a preflight Unicode and token-risk control before LLM calls. On adversarial transformed text, this can reduce prompt-token waste and improve auditability. Actual savings depend on traffic mix and model tokenizer."

---

## Product Naming

**Public Toy (Lead Magnet):**
- LLM Token Leak Test

**Paid Product:**
- RSTF Input Integrity Assessment

**Enterprise Product:**
- RSTF Gateway Policy Engine

**Technical Name:**
- RSTF Unicode Risk Gateway

**Alternative:**
- Prompt Firewall: Unicode & Obfuscation Layer
- LLM Input Integrity Scanner

---

## Pitch Deck Title

**RSTF: Deterministic Unicode Preflight for LLM Gateways**

**Subtitle:**
"Reduce prompt-risk, normalize adversarial text, and measure token waste before expensive model calls."

---

## Language to Drop

**Scam-sounding phrases:**
- "Investment readiness high"
- "Bank-safe"
- "Money directly"
- "Token savings guaranteed"
- "Claude cost reduced"
- "Revenue collateral"
- "Viral leaderboard"
- "Make it money directly"

**Serious replacements:**
- "Security control"
- "Input integrity layer"
- "Audit receipt"
- "Unicode obfuscation detection"
- "LLM gateway middleware"
- "Provider-measured token delta"
- "Not a billing guarantee"

---

## Next Steps

**Technical:**
- Complete test suite (unit tests, mock provider tests, summary math tests)
- Implement CI workflow with proper testing
- Add live Groq smoke test (gated behind GROQ_API_KEY)
- Security audit (SOC 2 preparation, penetration testing)

**Commercial:**
- Secure 3-5 pilot customers
- Deploy live gateway integration
- Generate customer case studies
- Validate on production traffic

**Evidence:**
- Anthropic count_tokens validation
- Customer traffic analysis
- Production false-positive/negative rates
- Real-world attack detection rate

---

## Conclusion

RSTF belongs as one small deterministic filter in the LLM security stack, not as a magic shield. The serious positioning is security-first, audit-second, cost-third.

**Bankable Language:**
"RSTF is a deterministic LLM input-control layer that detects transformed Unicode, canonicalizes recoverable text, and emits evidence receipts for prompt-risk and token-cost analysis."

**Not Bankable Language:**
"We save 75% of your LLM bill."

The move is to make it less viral, more boring. Boring sells to companies.
