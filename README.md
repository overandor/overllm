# OverLLM

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/overandor/overllm)
![README views](https://komarev.com/ghpvc/?username=overandor-overllm&label=README%20views&style=flat)

**OverLLM** is a local-first AI agent runtime for reproducible coding work: system telemetry, prompts, commands, file changes, generated answers, tests, receipts, and financeable evidence are treated as one protocolized diligence chain.

Search anchor: **local AI coding agent**, **reproducible LLM runtime**, **proof-of-inference receipts**, **coding-agent provenance**, **financeable AI evidence ledger**, **tamper-evident work receipts**, **AI revenue evidence export**, **C++ transformer engine**, **Go agent orchestration**, **Rust telemetry daemon**, **deterministic ML language**, **OverML**, **local-first developer AI**, **forkable AI agent protocol**.

> Status: experimental research software. This repository contains real components, partial components, and clearly labeled placeholders. Do not market a fork as production-ready or collateral-ready unless it passes the reproducibility and financeable-evidence checks below.

---

## What this repo is

OverLLM is a protocolized workspace for teams and users who want an AI coding agent that can be reproduced, forked, audited, measured, and packaged into diligence evidence.

The core thesis is simple:

```text
prompt + context + command + diff + test + receipt + revenue event = financeable evidence
```

A normal coding assistant gives an answer. OverLLM is designed to preserve the surrounding evidence: what context was available, what command ran, what files changed, what test result was produced, what receipt was attached, and whether the work is linked to a real payment, pilot, invoice, license, grant, or contract reference.

---

## Financeable evidence layer

OverLLM now includes a financeable evidence layer under `api/financeable.py` and `tools/finance_packet.py`.

This is the part that makes the repo look less like a toy and more like something a buyer, funder, bank, grant reviewer, or enterprise pilot can diligence.

It provides:

| Feature | Endpoint / command | Why it matters |
|---|---|---|
| Work receipts | `POST /api/finance/receipts` | Hashes prompt/task + output/diff/report into a tamper-evident record. |
| Revenue events | `POST /api/finance/revenue-events` | Links invoices, pilots, subscriptions, licenses, usage, grants, or consulting to evidence. |
| Finance summary | `GET /api/finance/summary` | Produces evidence, monetization, and reproducibility KPIs. |
| Collateral report | `POST /api/finance/collateral-report` | Creates a diligence packet from the local ledger. |
| CSV export | `GET /api/finance/export.csv` | Exports spreadsheet-ready records for underwriting/review. |
| CLI packet builder | `python tools/finance_packet.py ...` | Generates receipts/revenue/report artifacts without using Swagger. |

Set `OVERLLM_LEDGER_SECRET` to create HMAC-SHA256 signed records:

```bash
export OVERLLM_LEDGER_SECRET="replace-with-private-diligence-secret"
```

Create a receipt from a real output file:

```bash
python tools/finance_packet.py receipt \
  --source local.agent \
  --work-unit signed-ledger-api \
  --prompt-text "Add a financeable evidence layer" \
  --output-file api/financeable.py \
  --amount-usd 500 \
  --tag financeable \
  --tag diligence
```

Create a revenue event:

```bash
python tools/finance_packet.py revenue \
  --event-type pilot \
  --amount-usd 500 \
  --memo "Paid pilot for financeable evidence ledger"
```

Generate a diligence report:

```bash
python tools/finance_packet.py report \
  --title "OverLLM Financeable Evidence Packet" \
  --scope pilot \
  --narrative "Local-first AI agent with signed work receipts and revenue-linked diligence exports."
```

Read the full guide: [`docs/FINANCEABLE_FEATURES.md`](docs/FINANCEABLE_FEATURES.md).

Important truth label: this layer records evidence. It does **not** create a guaranteed valuation, loan approval, securities offering, or bank collateral by itself.

---

## Two modes: local agent vs. cloud demo

This repo ships two related but separate deployment targets. Do not confuse them.

| Mode | Path | Runs where | Network | Data boundary | Truth label |
|---|---|---|---|---|---|
| Local agent | `cpp/`, `go/`, `rust/`, `training/` | macOS ARM64 workstation | Offline-first, uses local Ollama when configured | `~/.overllm/data/` | Experimental local runtime |
| Cloud demo | `ui/`, `api/` | Vercel, Render, Hugging Face, Docker | Server-side model/API calls when configured | Your deployed backend + configured model provider | Demo / API surface |
| OverML package | `lang/overml/` | Rust toolchain / C ABI host | None required for local examples | Local source + provenance output | Experimental language package |
| Financeable evidence | `api/financeable.py`, `tools/finance_packet.py` | Local or deployed API | Local file ledger unless deployed | `.overllm/finance` or `OVERLLM_FINANCE_ROOT` | Evidence ledger, not valuation |
| iMessage auto-reply | `macos/imessage-agent/` | macOS 13+ workstation, requires Full Disk Access + Messages.app Automation permission | Local Ollama only | `~/Library/Messages/chat.db` (read-only) + `~/.overllm/data/imessage_state.json` | Untested prototype — sends autonomously, no approval step, see its README |

If you are evaluating whether OverLLM can run fully offline, the answer is: **the local agent, financeable ledger, and iMessage auto-reply paths are designed for local operation; the cloud demo is not an offline product.**

---

## Universal Reproducible Adoption Protocol — URAP-1

URAP-1 is the adoption contract for users, teams, forks, demos, and investor/audit reviews. A fork is considered a serious OverLLM adoption only when it publishes its state against these phases.

### Phase 0 — Identify the fork

Every fork should define its identity before changing claims.

```json
{
  "protocol": "URAP-1",
  "project": "overllm",
  "fork_owner": "YOUR_GITHUB_USER_OR_ORG",
  "repo": "overllm",
  "origin": "overandor/overllm",
  "mode": "local-agent | cloud-demo | overml | financeable-evidence | mixed",
  "claim_policy": "truth-labeled",
  "analytics_policy": "aggregate-only"
}
```

Recommended file path for forks:

```text
.overllm/adoption.json
```

### Phase 1 — Reproduce the repository

A clean adoption must begin from a clean clone.

```bash
git clone https://github.com/overandor/overllm.git
cd overllm
git rev-parse HEAD
```

Record the commit SHA in your adoption notes. A team report without a commit SHA is not reproducible.
