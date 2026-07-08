# OverLLM

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/overandor/overllm)
![README views](https://komarev.com/ghpvc/?username=overandor-overllm&label=README%20views&style=flat)

**OverLLM** is a local-first AI agent runtime for reproducible coding work: system telemetry, prompts, commands, file changes, generated answers, tests, and receipts are treated as one protocolized evidence chain.

Search anchor: **local AI coding agent**, **reproducible LLM runtime**, **proof-of-inference receipts**, **coding-agent provenance**, **C++ transformer engine**, **Go agent orchestration**, **Rust telemetry daemon**, **deterministic ML language**, **OverML**, **local-first developer AI**, **forkable AI agent protocol**.

> Status: experimental research software. This repository contains real components, partial components, and clearly labeled placeholders. Do not market a fork as production-ready unless it passes the reproducibility checks below.

---

## What this repo is

OverLLM is a protocolized workspace for teams and users who want an AI coding agent that can be reproduced, forked, audited, and measured.

The core thesis is simple:

```text
prompt + context + command + diff + test + receipt = reproducible agent work
```

A normal coding assistant gives an answer. OverLLM is designed to preserve the surrounding evidence: what context was available, what command ran, what files changed, what test result was produced, and what proof/receipt was attached.

---

## Two modes: local agent vs. cloud demo

This repo ships two related but separate deployment targets. Do not confuse them.

| Mode | Path | Runs where | Network | Data boundary | Truth label |
|---|---|---|---|---|---|
| Local agent | `cpp/`, `go/`, `rust/`, `training/` | macOS ARM64 workstation | Offline-first, uses local Ollama when configured | `~/.overllm/data/` | Experimental local runtime |
| Cloud demo | `ui/`, `api/` | Vercel, Render, Hugging Face, Docker | Server-side model/API calls when configured | Your deployed backend + configured model provider | Demo / API surface |
| OverML package | `lang/overml/` | Rust toolchain / C ABI host | None required for local examples | Local source + provenance output | Experimental language package |

If you are evaluating whether OverLLM can run fully offline, the answer is: **the local agent path is designed for offline/local operation; the cloud demo is not an offline product.**

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
  "mode": "local-agent | cloud-demo | overml | mixed",
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

### Phase 2 — Build each subsystem separately

Run the subsystems independently before claiming a full system.

```bash
# Native local stack
./build.sh

# Python cloud/API stack, when used
python -m pip install -r requirements.txt
python api/main.py

# UI demo, when used
cd ui
npm install
npm run build

# OverML package
cd ../lang/overml
cargo test
```

If any command fails, label the fork as `partial`, not `ready`.

### Phase 3 — Run the local loop

The intended local loop is:

```bash
# Terminal 1
ollama serve

# Terminal 2
./overllm-agent

# Terminal 3
./overllm-telemetry

# Terminal 4
python training/generate.py --count 20
python training/dpo_trainer.py --epochs 10 --export models/overllm.bin
./overllm_inference vocab.txt models/overllm.bin "What should I do next?"
```

Telemetry must be opt-in, visible, and documented. Do not collect user/application/file telemetry silently.

### Phase 4 — Produce a receipt

A valid receipt must include, at minimum:

```json
{
  "prompt_hash": "sha256(prompt)",
  "output_hash": "sha256(output)",
  "model_or_runtime": "runtime label",
  "commands_run": [],
  "files_touched": [],
  "test_result_hash": "sha256(test output)",
  "created_at": "ISO-8601 timestamp",
  "truth_label": "real | partial | mock | not_configured"
}
```

A receipt is not proof by itself. It becomes stronger when it is reproducible, signed, stored, and linked to tests.

### Phase 5 — Publish claim labels

Use these labels in README files, demos, dashboards, and pitch material.

| Label | Meaning |
|---|---|
| `real` | Implemented and reproduced from a clean checkout. |
| `experimental` | Implemented but not production-hardened. |
| `partial` | Interface exists, but the full path is not wired. |
| `mock` | Placeholder or simulated output. |
| `not_configured` | Real path exists but requires external setup. |
| `disabled_for_security` | Intentionally blocked until a safe runner exists. |

A fork that keeps these labels earns more trust than a fork that overclaims.

---

## Team adoption playbook

For teams, OverLLM should be adopted as a protocol before it is adopted as a product.

1. Assign an owner for local data, telemetry, and proof policy.
2. Reproduce the build on a clean machine.
3. Record commit SHA, OS version, toolchain versions, model/runtime configuration, and test logs.
4. Run one end-to-end task with a receipt.
5. Publish an adoption manifest.
6. Only then extend the agent, UI, proof layer, or OverML language package.

A team fork should add this table to its README:

| Adoption item | Status | Evidence |
|---|---|---|
| Clean clone recorded | `pending` | Commit SHA |
| Native build passes | `pending` | Build log |
| UI build passes | `pending` | `npm run build` log |
| OverML tests pass | `pending` | `cargo test` log |
| Receipt generated | `pending` | Receipt JSON |
| Telemetry policy published | `pending` | Privacy note |
| Analytics policy published | `pending` | Aggregate-only badge or GitHub traffic |

---

## Fork adoption protocol

Forks should keep the upstream anchor visible while adding their own fork identity.

```markdown
This fork adopts URAP-1 from `overandor/overllm`.
Origin: https://github.com/overandor/overllm
Fork owner: YOUR_GITHUB_USER_OR_ORG
Fork mode: local-agent | cloud-demo | overml | mixed
Truth-label policy: real / experimental / partial / mock / not_configured
```

Forks should replace the README view badge with their own aggregate counter label:

```markdown
![README views](https://komarev.com/ghpvc/?username=YOUR_OWNER-overllm&label=README%20views&style=flat)
```

This badge counts aggregate image loads. It does **not** identify individual visitors, and GitHub image caching/proxying can make the count approximate. For official repository owner analytics, use GitHub’s built-in traffic page instead.

---

## Privacy-safe analytics policy

This README includes an aggregate README view badge for lightweight adoption measurement.

Rules for OverLLM analytics:

- Aggregate counters are acceptable.
- GitHub stars, forks, watchers, clones, and traffic totals are acceptable.
- Do not claim to know exactly who visited a GitHub README from a pixel.
- Do not collect private visitor identity without clear consent.
- Do not use analytics to fingerprint users.
- Forks must disclose any external counter or badge they add.

Recommended public adoption KPIs:

| KPI | Source | Privacy level |
|---|---|---|
| Stars | GitHub repo metadata | Public aggregate |
| Forks | GitHub repo metadata | Public aggregate |
| README view badge | External badge/counter | Approximate aggregate |
| Clones/views | GitHub Traffic | Owner-only aggregate |
| Reproducible builds | CI logs | Public or private evidence |
| Valid receipts | Receipt files / dashboard | Depends on contents |

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│                         Local Mac / Workstation                       │
│                                                                      │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐ │
│  │ Rust telemetry   │────▶│ Go agent server   │────▶│ C++ runtime   │ │
│  │ system context   │     │ context + API     │     │ inference     │ │
│  └──────────────────┘     └────────┬─────────┘     └──────────────┘ │
│                                     │                                │
│                                     ▼                                │
│                            ~/.overllm/data/                          │
│                      preferences, logs, receipts                     │
│                                     │                                │
│                                     ▼                                │
│                         Python training bridge                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                             Cloud demo                               │
│                                                                      │
│      React/Vite UI ─────▶ FastAPI backend ─────▶ configured model/API │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Components

### C++ — inference engine (`cpp/`)

- Tensor operations: matmul, softmax, GELU, layer norm.
- Transformer-style decoder stack.
- C ABI for host-language integration.
- Binary weight save/load format.
- Experimental DPO/RL interfaces.

### Go — local agent server (`go/`)

- Telemetry ingestion endpoint.
- Context window builder.
- Status and generation APIs.
- Receipt/proof handler boundary.
- OverAgent experimental endpoints.

### Rust — telemetry daemon (`rust/`)

- Active app detection through macOS automation.
- CPU/RAM/process/file/network telemetry.
- Vector, DAG, article, blockchain, and RL experimental modules.
- Async publisher to local Go agent.

### Python — API and training bridge (`api/`, `training/`)

- Cloud/API demo with truth-labeled runtime states.
- Ollama-backed generation when available.
- Disabled public shell execution by default.
- Local training/export scripts.

### OverML — deterministic ML package (`lang/overml/`)

- Shape/dtype-checked tensor language.
- Deterministic-by-default execution model.
- Fixed-capacity `KvCache` for bounded attention-cache memory.
- C ABI shared library for host-language import.

---

## Current truth table

| Claim | Current label | Notes |
|---|---|---|
| Local-first agent architecture | `experimental` | Multi-language implementation exists. |
| Fully production-ready LLM | `partial` | Native inference/training need stronger wiring and benchmarks. |
| Cloud demo API | `experimental` | FastAPI surface exists with truth labels. |
| Public terminal execution | `disabled_for_security` | Should remain disabled until a safe allowlist runner exists. |
| Proof receipts | `partial` | Receipt interfaces exist; external proof daemon/anchoring must be configured. |
| Solana/IPFS anchoring | `not_configured` by default | Do not claim live anchoring without signatures/CIDs. |
| OverML language package | `experimental` | Strong standalone package direction. |
| README visitor analytics | `aggregate_only` | Approximate badge + GitHub traffic, not individual identity. |

---

## Reproducibility checklist

Before publishing a demo, release, fork, or investor packet, capture this:

```text
[ ] repo URL
[ ] commit SHA
[ ] branch name
[ ] OS + architecture
[ ] CMake version
[ ] clang++ / Xcode version
[ ] Go version
[ ] Rust version
[ ] Python version
[ ] Node version
[ ] local model/runtime used
[ ] exact build commands
[ ] exact test commands
[ ] generated receipt path
[ ] known failures
[ ] truth labels updated
```

Suggested machine-readable run record:

```json
{
  "protocol": "URAP-1",
  "repo": "overandor/overllm",
  "commit": "COMMIT_SHA",
  "machine": "macOS ARM64",
  "commands": [
    "./build.sh",
    "cargo test --manifest-path lang/overml/Cargo.toml",
    "npm --prefix ui run build"
  ],
  "results": {
    "native_build": "pass | fail | partial",
    "overml_tests": "pass | fail | partial",
    "ui_build": "pass | fail | partial",
    "receipt_generated": true
  },
  "truth_label": "experimental"
}
```

---

## Build

```bash
./build.sh
```

Requires:

- macOS ARM64 for the local desktop path.
- Xcode command line tools / `clang++`.
- CMake.
- Go version compatible with `go/go.mod`.
- Rust toolchain.
- Python 3.
- Ollama running locally when using local model generation.

---

## Quick start

```bash
# Terminal 1: local model server, when used
ollama serve

# Terminal 2: local agent
./overllm-agent

# Terminal 3: telemetry daemon
./overllm-telemetry

# Terminal 4: training and inference path
python training/generate.py --count 20
python training/dpo_trainer.py --epochs 10 --export models/overllm.bin
./overllm_inference vocab.txt models/overllm.bin "What should I do next?"
```

---

## HTTP API

| Endpoint | Method | Description | Truth label |
|---|---:|---|---|
| `/telemetry` | POST | Ingest local telemetry event | Experimental |
| `/api/status` | GET | Agent/runtime status | Real if server is running |
| `/api/context` | GET | Current context window | Experimental |
| `/api/generate` | POST | Generate through configured runtime | Environment-dependent |
| `/api/preference_queue` | GET | DPO batch queue status | Experimental |
| `/api/proof/receipt` | POST | Receipt generation boundary | External proof daemon required |
| `/api/overagent/*` | Mixed | Experimental autonomous-agent endpoints | Prototype |

---

## Cloud deployment

The cloud demo is not the offline local agent. It is a separate web/API deployment target.

```bash
cd ui
cp .env.example .env.local
npm install
npm run build
```

Backend/API:

```bash
python -m pip install -r requirements.txt
python api/main.py
```

One-click Render deployment remains available for demo workflows:

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/overandor/overllm)

---

## SEO adoption anchors for forks

Forks should retain these phrases when accurate:

```text
OverLLM fork
local-first AI coding agent
reproducible LLM runtime
proof-of-inference receipt
agent work provenance
C++ transformer runtime
Go orchestration server
Rust telemetry daemon
OverML deterministic ML language
URAP-1 adoption protocol
```

Do not copy claims that your fork has not reproduced.

---

## Roadmap

- [ ] Add CI for native build, UI build, Python import checks, and OverML tests.
- [ ] Fix telemetry schema compatibility across Rust and Go.
- [ ] Replace mock proof endpoints with `not_configured` or real proof generation.
- [ ] Publish a signed sample receipt.
- [ ] Add one clean end-to-end demo: prompt → context → generation → receipt → dashboard.
- [ ] Add fork adoption manifest template.
- [ ] Add benchmark fixtures for deterministic regression testing.
- [ ] Add a safe, explicit telemetry-consent flow.
- [ ] Add quantization and Metal backend experiments.
- [ ] Add BPE or equivalent tokenizer path.

---

## License

MIT / OverLLM Project
