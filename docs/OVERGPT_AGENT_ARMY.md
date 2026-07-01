# OverGPT Agent Army

OverGPT Agent Army is a permissioned swarm of repo-improvement agents.

It is not malware, not self-propagating code, and not unauthorized automation.

The purpose is to create more useful repositories by coordinating safe specialist agents that produce reviewable branches, tests, documentation, demos, receipts, and pull requests.

## Prime rule

Agents may prepare work autonomously.

Agents may not publish, merge, deploy, message humans, spend money, create accounts, or modify external systems without explicit approval.

## Why an army

A single agent can generate a file.

An army can create a proof chain.

The useful unit is not raw code volume. The useful unit is verified repo improvement:

- an issue that defines a problem
- a branch that isolates a change
- a commit that adds functionality
- tests that verify behavior
- CI that repeats the proof
- docs that explain usage
- receipts that prove output
- a PR that makes review possible

## Agent roles

### 1. Scout Agent

Finds repo gaps.

Outputs:

- missing tests
- broken workflows
- unclear docs
- weak demos
- valuation blockers
- security concerns

Allowed actions:

- read files
- create reports
- open issues with approval

Blocked actions:

- external scraping without permission
- credential access
- destructive edits

### 2. Spec Agent

Turns an idea into a buildable specification.

Outputs:

- feature brief
- acceptance criteria
- test plan
- risk list
- evidence tier target

### 3. Builder Agent

Implements narrow functionality.

Outputs:

- branch
- small commits
- runnable files
- minimal dependencies

Rule:

No large change without a spec.

### 4. Test Agent

Adds proof.

Outputs:

- unit tests
- smoke tests
- hash verification tests
- failure-mode tests
- CI checks

Rule:

No quality claim without executable tests.

### 5. Receipt Agent

Generates reproducibility artifacts.

Outputs:

- run manifest
- value packet
- diligence report
- output hashes
- CI artifact links

### 6. Claim Firewall Agent

Blocks overclaiming.

Outputs:

- allowed wording
- blocked wording
- evidence-tier explanation
- missing evidence list

Rule:

No breakthrough, validated, proven, or enterprise-ready wording unless the evidence tier supports it.

### 7. Diligence Agent

Scores commercial readiness.

Outputs:

- valuation-readiness report
- missing commercial evidence
- legal transferability checklist
- deployment checklist
- target gap report

### 8. Merge Captain

Summarizes PRs and decides whether they are ready for human review.

Outputs:

- PR summary
- risk summary
- test summary
- merge recommendation

Blocked actions:

- auto-merge without approval
- bypassing failed CI
- force-pushing without approval

## Safe operating loop

1. Create issue
2. Create branch
3. Add spec
4. Add code
5. Add tests
6. Run quality gate
7. Generate receipts
8. Open PR
9. Wait for human approval
10. Merge only after approval

## Viral repo quality, not virus behavior

The goal is to create repositories that spread because they are useful, clear, runnable, and trustworthy.

Allowed viral mechanics:

- excellent README
- one-command demo
- clear screenshots
- reproducible outputs
- useful templates
- strong examples
- easy installation
- public benchmarks when honest
- contributor-friendly issues

Blocked viral mechanics:

- self-propagation
- unauthorized repo modification
- credential harvesting
- spam
- hidden persistence
- covert execution
- worm behavior
- deceptive stars or engagement
- automated messaging without consent

## Army scoring function

An agent action is good when it increases proof density.

Score =

- runnable artifact progress
- test coverage increase
- CI reliability increase
- documentation clarity increase
- receipt completeness increase
- claim discipline increase
- commercial diligence increase
- reviewer burden reduction

Minus:

- unsupported claims
- broken builds
- hidden side effects
- external actions without approval
- inflated line count
- unclear ownership
- security risk

## Repo Army maturity levels

### Level 0: Manual repo

Human writes everything.

### Level 1: Assistant-generated changes

Agent proposes files and commits, human reviews.

### Level 2: Specialist agents

Separate agents handle specs, tests, docs, receipts, and diligence.

### Level 3: CI-governed army

Every agent output must pass quality gates.

### Level 4: Receipt-backed army

Every meaningful repo improvement emits a receipt, value packet, or diligence report.

### Level 5: Market-facing army

The repo army produces artifacts that can be shown to buyers, collaborators, users, or reviewers.

## Current OverGPT target

OverGPT should reach Level 3 first:

- one-command proof chain
- test suite
- CI gate
- receipt artifact
- diligence report
- claim firewall

Then Level 4:

- baseline comparison receipts
- ablation receipts
- repeated-run receipts
- real project claim packets

## Safety invariant

The army must never become a virus.

It must remain a permissioned, reviewable, human-approved repo-improvement system.

The strongest version of OverGPT is not autonomous spread.

The strongest version is autonomous preparation with human-approved publication.
