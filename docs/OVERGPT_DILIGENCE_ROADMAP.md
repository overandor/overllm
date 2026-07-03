# OverGPT Diligence Roadmap

This roadmap defines the path from the current OverGPT demo artifact to a higher-confidence commercial asset.

It does not assert a market valuation. It defines what evidence would be needed to support stronger valuation discussions.

## Current state

Current evidence label:

Tier 3 candidate: stable internal proof.

Current artifact set:

- value packet demo
- HotTensor underwriting score
- hash-chained receipt
- claim firewall
- enterprise diligence gate
- Python test suite
- GitHub Actions quality gate

## Why this matters

The project now has two important proof surfaces:

1. The value packet generator shows that a claim can be packaged into a structured, receipted, underwritable object.
2. The diligence gate shows what is missing before a stronger valuation claim becomes defensible.

This is valuable because it prevents unsupported valuation inflation while still making the asset easier to inspect, review, and improve.

## Evidence ladder

### Tier 3: stable internal proof

Requirement:

- runnable artifact
- internal smoke output
- deterministic receipt
- tests
- CI quality gate

Current status:

Mostly satisfied for the OverGPT single-file demo.

### Tier 4: baseline comparison

Requirement:

- define a baseline method
- compare against the baseline
- measure result differences
- produce a baseline receipt

Next artifact:

`tools/overgpt_baseline_compare.py`

Suggested baseline:

A plain JSON claim without evidence, bond, resolution rule, receipt chain, or underwriting score.

Metric:

Reviewability score, verification completeness, settlement readiness, and underwrite readiness.

### Tier 5: ablation support

Requirement:

- remove one feature at a time
- measure loss of reviewability or settlement readiness
- show which components matter

Ablations:

- no bond
- no resolution rule
- no claim firewall
- no HotTensor score
- no receipt chain
- no evidence entropy

### Tier 6: repeated runs

Requirement:

- run multiple generated packets
- verify stable schema
- verify bounded scores
- verify receipt hash recomputation

Metrics:

- success rate
- schema failure rate
- hash verification failure rate
- score bound violation rate

### Tier 7: real-world task performance

Requirement:

- use the artifact on actual project claims
- produce real venture packets
- have a human reviewer score usefulness

Examples:

- repo appraisal packet
- prototype claim packet
- prior-art claim packet
- deployment-readiness packet

### Tier 8: external reproduction

Requirement:

- another person runs the artifact
- another person verifies the receipt
- another person reproduces the diligence score

Evidence:

- external run log
- independent packet hash
- reviewer note
- dated reproduction receipt

## Commercial evidence needed

To support a much stronger valuation conversation, OverGPT needs evidence beyond code:

- live deployment
- working demo URL
- onboarding page
- sample outputs
- user interviews
- signed counterparty or pilot
- usage logs
- revenue or paid test
- legal transfer documentation
- license clarity
- security review

## Definition of done for next milestone

The next milestone is not a bigger claim.

The next milestone is:

- merge PR #5
- run the GitHub Actions quality gate
- archive the generated value packet artifact
- create one baseline comparison artifact
- add one real project claim packet
- produce a diligence report for that real packet

## Claim discipline

Allowed current wording:

- runnable OverGPT value-packet demo
- Tier 3 candidate
- stable internal proof
- deterministic receipt-backed claim package
- enterprise diligence gate for valuation-readiness

Not supported yet:

- market-proven product
- enterprise-ready product
- externally verified system
- revenue-backed valuation
- scientific contribution

## Target state

The target state is not just more code.

The target state is a repeatable proof chain:

claim
→ evidence
→ receipt
→ baseline comparison
→ ablation
→ repeated runs
→ real project packet
→ external review
→ priced transaction

That is the path from artifact to asset.
