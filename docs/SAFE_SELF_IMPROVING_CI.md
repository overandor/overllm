# Safe Self-Improving CI Doctrine

This document defines the allowed version of a self-improving OverGPT repository loop.

It explicitly rejects malware behavior, autonomous propagation, credential harvesting, stealth, persistence outside the repository, or uncontrolled self-modification.

## Non-negotiable boundary

The repository must not become a virus.

Forbidden behavior:

- self-propagation to other repositories, accounts, machines, or networks
- credential exfiltration
- hidden persistence
- stealth execution
- unauthorized file modification
- bypassing CI or branch protection
- auto-merging without human approval
- modifying deployment settings without explicit review
- reverse-engineering external infrastructure to bypass controls
- using Vercel, GitHub Actions, or any deployment function as a propagation mechanism

## Allowed version

The safe version is a constrained self-improvement loop.

It may:

- inspect its own tests
- inspect its own CI output
- propose improvements
- generate receipt-backed patches
- open pull requests
- run tests
- produce diligence reports
- label evidence tiers
- block unsupported claims
- wait for human review before merge

It may not:

- push directly to main
- merge itself
- change secrets
- access production credentials
- create external accounts
- deploy public changes without approval
- modify other repositories
- execute arbitrary remote code

## Safe architecture

The safe loop is:

CI result
→ failure summary
→ improvement proposal
→ patch branch
→ tests
→ value packet
→ diligence report
→ pull request
→ human approval
→ merge

The unsafe loop would be:

CI result
→ autonomous mutation
→ self-deploy
→ self-propagate
→ bypass review

The unsafe loop is prohibited.

## Required controls

A safe self-improving CI system needs these controls:

1. Pull-request-only writes
2. No direct writes to main
3. No access to repository secrets during patch generation
4. No external network writes except GitHub PR creation
5. Human approval before merge
6. Artifact receipts for every generated change
7. Diligence report for every valuation or breakthrough claim
8. Claim firewall on public wording
9. Branch protection
10. Clear audit log

## Evidence tiers

A self-improvement proposal is not a breakthrough.

Default label:

Tier 3 candidate: stable internal proof.

Higher tiers require:

- Tier 4: baseline comparison
- Tier 5: ablation
- Tier 6: repeated runs
- Tier 7: real-world task performance
- Tier 8: external reproduction

## Safe OverGPT autopilot definition

OverGPT Autopilot is a bounded repository-improvement agent that reads CI outputs, generates improvement proposals, attaches receipts, and opens pull requests for human review.

It is not autonomous malware.

It does not self-propagate.

It does not bypass approval.

It does not claim breakthrough status.

## Minimum viable safe implementation

The first safe implementation should do only this:

1. Run the existing quality gate.
2. If tests fail, summarize the failing test names.
3. Create a local improvement proposal document.
4. Generate a value packet for the proposal.
5. Generate a diligence report.
6. Open a pull request for review.

No automatic merge.

No external deployment mutation.

No secret access.

## Commercial framing

The safe product is not a virus.

The product is a controlled CI improvement assistant for receipt-backed software assets.

Its value is in:

- faster review
- clearer proof
- fewer unsupported claims
- better artifact traceability
- stronger diligence evidence
- lower buyer/reviewer uncertainty

## Claim firewall

Allowed wording:

- safe self-improving CI assistant
- PR-only improvement loop
- receipt-backed repository improvement workflow
- bounded OverGPT autopilot
- human-approved CI repair loop

Blocked wording:

- virus
- worm
- autonomous propagation
- stealth self-modifier
- credential harvester
- self-deploying malware
- breakthrough without external validation

## Bottom line

The correct direction is not a self-modifying virus.

The correct direction is a self-auditing, PR-only improvement loop with receipts, tests, CI, diligence reports, and human approval.
