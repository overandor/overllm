# OverLLM Deployment Threat Model

This threat model defines the assets, attack surfaces, risks, and minimum controls for production-candidate OverLLM deployments.

## Assets

| Asset | Why it matters |
|---|---|
| Prompts and generated answers | May contain private strategy, code, customer data, or regulated information. |
| Local files and file metadata | May reveal sensitive project structure or personal data. |
| Financeable evidence ledger | Used for diligence; integrity and provenance matter. |
| Revenue events | May reference invoices, contracts, grants, pilots, or customers. |
| API secrets and model credentials | Enable third-party access or billing abuse if leaked. |
| Local model runtime | Can expose host resources or private context if misconfigured. |
| Outbound automation surfaces | Can send messages, emails, or actions that create real-world consequences. |

## Trust boundaries

1. Browser/UI to OverLLM API.
2. OverLLM API to local Ollama or model provider.
3. OverLLM API to local filesystem.
4. OverLLM API to financeable ledger storage.
5. Operator/deployer to cloud environment secret store.
6. Optional automation surface to external recipients or exchanges.

## Main attack surfaces

| Surface | Risk | Required control |
|---|---|---|
| `/api/terminal` | arbitrary command execution | Disabled by default; no public shell; future runner must be no-shell allowlist only. |
| `/api/files` | path traversal / data exposure | Restrict to `OVERLLM_FILE_ROOT`; return metadata only unless separately approved. |
| CORS | browser-based abuse | Explicit allowlist; no wildcard in public deployments. |
| Finance exports | false diligence / data leakage | Signed records; truth labels; no guaranteed valuation language. |
| iMessage/email automation | unwanted outbound messages | Human approval gate by default. |
| Trading/payment integrations | financial loss / unauthorized action | Paper mode by default; separate production review before live action. |
| Logs | accidental secret retention | Redact secrets; avoid raw cookies/tokens/payment data. |

## Threat scenarios

### T1: Public command execution

An attacker calls a terminal endpoint to run shell commands.

Controls:

- keep `OVERLLM_ENABLE_TERMINAL=0`;
- do not deploy shell execution publicly;
- if a runner is added, implement a typed allowlist with no shell interpolation.

### T2: File disclosure through path traversal

An attacker requests `../../` paths or absolute paths to read host files.

Controls:

- resolve and validate all file paths against `OVERLLM_FILE_ROOT`;
- do not expose file contents in public demos;
- keep demo roots separate from home directories, SSH keys, credentials, or customer files.

### T3: False finance/collateral claim

A user or fork presents receipts as guaranteed valuation, loan collateral, or investment merit.

Controls:

- separate evidence from valuation;
- require signed receipts and real revenue references;
- require reports to include limitation language;
- reject claims not tied to external invoices, contracts, grants, or payments.

### T4: Secret leakage

A `.env`, token, cookie, or API key is committed or logged.

Controls:

- keep `.env.example` documentation-only;
- use secret stores;
- rotate exposed secrets immediately;
- add secret scanning before production.

### T5: Autonomous outbound action causes harm

An automation sends messages, trades, or financial actions without approval.

Controls:

- approval gate required by default;
- all outbound actions logged with actor, target, payload hash, and timestamp;
- live financial integrations require separate review and manual enablement.

## Production-control baseline

Before production:

- P0 gates in `PRODUCTION_READY.md` pass;
- `SECURITY.md` is followed;
- `docs/OPERATIONS_RUNBOOK.md` is executable by an operator other than the author;
- incident owner is named;
- backup/restore is tested;
- public claims match runtime truth labels.

## Residual risk

Even with these controls, OverLLM remains a high-sensitivity system when connected to private prompts, local files, or financial/revenue evidence. Treat production deployments as evidence systems first and model/chat systems second: integrity, provenance, and safe action boundaries are the product.
