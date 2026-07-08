# Security Policy

OverLLM is a local-first AI-agent runtime with optional cloud demo surfaces. Treat every deployment as security-sensitive because prompts, local files, receipts, telemetry, and revenue evidence can contain private or commercial information.

## Supported versions

Only tagged releases should be used for production deployments. Until the first production release tag exists, deployments must be treated as demo or controlled-pilot deployments.

| Version / ref | Support status |
|---|---|
| `main` | Development branch, not a production support target |
| Release tags | Supported according to the release notes for that tag |
| Forks | Supported by the fork owner, not automatically by the upstream project |

## Reporting a vulnerability

Do not publish exploit details in a public issue if the bug could expose secrets, customer data, private files, prompt history, ledger records, revenue evidence, or credentials.

Report privately to the repository owner or through GitHub private vulnerability reporting when enabled. Include:

- affected commit or release tag;
- deployment class: local demo, controlled pilot, public demo, or production;
- reproduction steps;
- expected vs. actual behavior;
- impact on confidentiality, integrity, availability, or evidence correctness;
- whether secrets, tokens, customer files, or ledger records were exposed.

## Required security defaults

Production and public demo deployments must use these defaults unless a documented exception exists:

- `OVERLLM_ENABLE_TERMINAL=0`
- explicit `OVERLLM_CORS_ORIGINS`, never wildcard CORS;
- scoped `OVERLLM_FILE_ROOT` pointing only at intended non-sensitive files;
- `OVERLLM_LEDGER_SECRET` provided through the deployment secret store, never committed;
- no live trading or financial movement enabled;
- no autonomous outbound messages without a human approval gate;
- logs must not store raw secrets, cookies, API keys, private keys, seed phrases, or payment credentials.

## Secret handling

Never commit:

- API keys;
- OAuth tokens;
- session cookies;
- private keys or seed phrases;
- exchange credentials;
- bank, payment, or broker credentials;
- customer files or private prompt exports;
- production `.overllm` ledger directories.

Use `.env.example` as documentation only. Real `.env` files must stay local or in a secret manager.

## High-risk surfaces

The following surfaces require extra review before public deployment:

- `/api/terminal` or any command execution path;
- file browsing or file export endpoints;
- financeable evidence exports;
- iMessage or email automation;
- trading, brokerage, crypto, bank, or payment integrations;
- endpoints that ingest private prompts, files, or customer data.

## Evidence integrity

The financeable-evidence layer records evidence. It does not create guaranteed valuation, loan approval, collateral value, securities compliance, or investment merit. Any report used with buyers, lenders, investors, grant reviewers, or customers must keep evidence, revenue, valuation, and risk as separate claims.
