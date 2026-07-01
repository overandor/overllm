# OverGPT

OverGPT is the product layer on top of OverLLM.

OverLLM is the substrate: local agents, memory, proof receipts, VentureChain, and claim-verification primitives.

OverGPT is the user-facing economic interface: it turns a raw idea, claim, repo, prototype, or research note into a financeable value packet with evidence, provenance, settlement terms, and claim-control.

## Core thesis

A raw answer is difficult to sell because disclosure transfers the answer before payment.

OverGPT does not sell raw answers.

It manufactures underwritable knowledge artifacts.

The primitive is:

- claim
- evidence
- provenance
- bond field
- resolution rule
- HotTensor underwriting score
- hash-chained receipt
- allowed public wording
- blocked overclaim wording

## Honest evidence posture

OverGPT must not label generated output as a breakthrough by default.

The correct default status is:

Tier 3 candidate: stable internal proof.

A stronger label requires stronger evidence:

- baseline comparison
- ablation
- repeated runs
- real-world task performance
- external reproduction

## Product promise

OverGPT converts ambiguous cognition into standardized, receipt-backed, underwritable claims.

It helps answer:

- What exactly is being claimed?
- What evidence supports it?
- What is the settlement rule?
- What wording is allowed at this evidence tier?
- What wording is blocked as overclaiming?
- What stake would make the claim economically accountable?
- What HotTensor score describes underwrite readiness?

## Relationship to VentureChain

VentureChain tracks deal-state progress.

OverGPT packages that progress into market-facing value packets.

The pipeline is:

raw idea
→ structured claim
→ evidence packet
→ reproducible artifact
→ HotTensor underwriting
→ claim firewall
→ receipt
→ optional bond
→ receipted exchange

## Current implementation

The first OverGPT artifact is:

`tools/value_packet_demo.py`

It is a self-contained, dependency-free demo that emits a JSON value packet and receipt.

Current status:

Tier 3 candidate: stable internal proof.

Not claimed:

- scientific breakthrough
- externally verified result
- baseline-beating result
- validated commercial result

## Commercial interpretation

OverGPT is not merely a chatbot.

It is a claim-underwriting interface for AI-generated work.

Its commercial object is not an answer.

Its commercial object is a receipted value packet.
