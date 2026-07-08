# OverLLM Operations Runbook

This runbook is for controlled pilots and production-candidate deployments. It converts OverLLM from a research workspace into an operated service with clear boundaries, checks, and rollback steps.

## 1. Deployment classes

Use the deployment class that matches reality.

| Class | Purpose | Public users? | Production claim? |
|---|---|---:|---:|
| `local-demo` | Developer/local demo | No | No |
| `controlled-pilot` | Named users, supervised | Limited | No |
| `public-demo` | Public UI/API demo | Yes | No |
| `production` | Paying/customer service | Yes | Yes, only after gates pass |

Set `OVERLLM_DEPLOYMENT_CLASS` to one of these values.

## 2. Pre-deploy checklist

Before deploying any public or pilot environment:

- Record the commit SHA in `OVERLLM_RELEASE_SHA`.
- Confirm CI passes for the language surfaces deployed.
- Confirm `OVERLLM_ENABLE_TERMINAL=0`.
- Confirm `OVERLLM_CORS_ORIGINS` is an explicit comma-separated allowlist.
- Confirm `OVERLLM_FILE_ROOT` points to a safe non-sensitive directory.
- Confirm `OVERLLM_LEDGER_SECRET` is set for any evidence used outside local demos.
- Confirm live trading, payments, or outbound messages are disabled unless a human approval gate is deployed.
- Confirm logs and ledger data have a backup path.

## 3. Required environment variables

| Variable | Required for | Safe default | Notes |
|---|---|---|---|
| `OLLAMA_BASE_URL` | local generation | `http://localhost:11434` | Do not expose Ollama directly to the public internet. |
| `OLLAMA_MODEL` | local generation | `llama3.2` | Model must exist on the host. |
| `OVERLLM_ENABLE_TERMINAL` | API safety | `0` | Public deployments must keep this disabled. |
| `OVERLLM_CORS_ORIGINS` | browser API access | localhost only | Use explicit origins. |
| `OVERLLM_FILE_ROOT` | file metadata endpoint | `.` | Scope tightly in public demos. |
| `OVERLLM_LEDGER_SECRET` | signed receipts | empty for local demo only | Required for diligence/customer evidence. |
| `OVERLLM_FINANCE_ROOT` | evidence storage | `.overllm/finance` | Back this up in pilot/production. |

## 4. Health checks

Primary checks:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/api/status
```

Expected response posture:

- service returns HTTP 200;
- `truth_labels.live_trading` remains disabled;
- terminal execution remains disabled by default;
- finance summary returns without corrupting ledger state;
- unavailable C++/Ollama components are truth-labeled instead of faked.

## 5. Backup and restore

The evidence ledger is operationally important. Back up:

- `.overllm/finance/receipts.jsonl`
- `.overllm/finance/revenue_events.jsonl`
- `.overllm/finance/collateral_reports.jsonl`
- any exported diligence CSV or report artifacts

Restore test:

1. Stop the API.
2. Copy the ledger directory to a new environment.
3. Start the API with `OVERLLM_FINANCE_ROOT` pointing to the restored directory.
4. Call `/api/finance/summary`.
5. Compare receipt count, revenue count, and report count to the source environment.

## 6. Incident response

Severity levels:

| Severity | Example | Required response |
|---|---|---|
| SEV-1 | secret leak, arbitrary command execution, customer data exposure | Disable public access, rotate secrets, preserve logs, publish incident notes to affected parties |
| SEV-2 | corrupted ledger, false production claim, broken auth boundary | Freeze exports, restore from backup, correct claims, open remediation issue |
| SEV-3 | degraded generation, unavailable local model, failed demo endpoint | Truth-label degradation, restart service, record operator note |

Minimum incident record:

- time detected;
- affected commit and deployment class;
- impact;
- mitigation;
- follow-up control added.

## 7. Rollback

Rollback must be possible before production claim.

1. Identify the last passing release tag or commit SHA.
2. Redeploy that ref.
3. Keep the ledger directory intact unless corruption is confirmed.
4. If ledger corruption is confirmed, restore from the latest known-good backup and preserve the corrupted copy for analysis.
5. Record rollback in the incident log.

## 8. Release process

A production release should include:

- semantic version tag;
- changelog entry;
- passing CI;
- production readiness scorecard filled out;
- known limitations;
- migration notes;
- rollback target.

## 9. Claims guardrail

Do not use production language unless the deployed commit and environment pass `PRODUCTION_READY.md` gates. Acceptable language before that point:

> controlled pilot

> public demo

> production candidate

> financeable evidence prototype

Do not use:

> guaranteed collateral

> guaranteed loan approval

> guaranteed profit

> autonomous production messaging

> live trading engine
