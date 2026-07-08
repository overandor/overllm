# OverLLM Production Readiness Contract

OverLLM is not automatically production-ready because it has a public repository, a demo API, or a financeable-evidence ledger. This document defines what must be true before anyone may claim a deployment is production-ready.

## Current status

**Repository posture:** pilot-ready after local reproduction.

**Production posture:** gated. A deployment is production-ready only when the required gates below pass for the exact commit, environment, secrets, data boundary, and use case being deployed.

Do not claim production readiness for:

- autonomous iMessage sending without a human approval gate;
- live trading or live financial execution;
- public shell execution;
- public deployment with wildcard CORS;
- unsigned financeable ledgers used for diligence;
- valuation, loan, collateral, or investment claims not tied to real contracts or invoices.

## Allowed deployment classes

| Class | Allowed claim | Allowed users | Required controls |
|---|---|---|---|
| Local demo | Experimental local runtime | Owner / developer | No public access, local secrets only |
| Controlled pilot | Supervised pilot | Named pilot users | Auth, logs, backups, signed ledger, incident owner |
| Public demo | Demo API/UI | Public visitors | No secrets exposed, no terminal, no live funds, rate limits |
| Production | Production service | Paying users / enterprise users | All P0 gates pass, release tag, monitoring, rollback, support process |

## P0 gates before production

Every production deployment must pass all of these gates.

1. **Reproducible build**
   - Clean clone from the production commit.
   - Commit SHA recorded in the deployment packet.
   - CI passes for every language surface that is deployed.
   - A release tag exists for the deployed commit.

2. **Security boundary**
   - `OVERLLM_ENABLE_TERMINAL=0` in public environments.
   - `OVERLLM_CORS_ORIGINS` is an explicit allowlist, never `*`.
   - `OVERLLM_LEDGER_SECRET` is set outside git for any diligence or customer evidence use.
   - `OVERLLM_FILE_ROOT` is restricted to an intended non-sensitive directory.
   - No API keys, tokens, cookies, passwords, or customer data are committed.

3. **Human approval boundary**
   - Any outbound message, email, iMessage, trading action, or financial action requires approval by default.
   - Fully autonomous outbound actions must be separately threat-modeled and explicitly enabled by the deployer.

4. **Data integrity**
   - Receipts are hash-linked or independently exportable.
   - Revenue events point to real invoices, contracts, grants, pilots, or payment references.
   - Reports label evidence separately from valuation.

5. **Operational readiness**
   - Health check endpoint monitored.
   - Logs retained for incident review.
   - Backup and restore path tested for ledger data.
   - Rollback plan documented.
   - Incident contact and response process documented.

6. **Truthful claims**
   - Public copy says “demo,” “pilot,” or “production” according to the actual gate status.
   - C++ inference, local model execution, trading, finance, and evidence claims match runtime truth labels.
   - No guaranteed profit, valuation, loan approval, securities, or collateral language.

## Production readiness scorecard

Use this scorecard in every buyer, funder, or operator review.

| Area | Pass condition | Status |
|---|---|---|
| Build reproducibility | Clean clone + CI + recorded SHA | Pending per deployment |
| API safety | Terminal disabled, CORS allowlisted, file root scoped | Pending per deployment |
| Secrets | No secrets in git, ledger secret configured | Pending per deployment |
| Financeable evidence | Signed receipts + real revenue references | Pending per deployment |
| Autonomous actions | Human approval gate enforced | Pending per deployment |
| Observability | Health, logs, alerts, owner | Pending per deployment |
| Backups | Ledger backup + restore test | Pending per deployment |
| Release | Semver tag + changelog + rollback | Pending per deployment |

## Decision rule

A deployment may be called **production-ready** only when every P0 gate is marked pass for that deployment.

Until then, use this language:

> OverLLM is a local-first AI-agent provenance runtime with a financeable-evidence layer. This deployment is approved for controlled pilot/demo use only until the production readiness gates pass for the deployed commit and environment.
