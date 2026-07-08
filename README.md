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

## Reversible semantic transform fingerprint (RSTF)

OverLLM includes a text-identity module under `api/semantic_fingerprint.py` and `tools/semantic_fingerprint.py`.

A cryptographic hash answers "same exact bytes?". RSTF answers a narrower, related question: is a byte-different string the same recoverable message under a known, reversible presentation transform? It detects and recovers four specific transforms — plain reversal, upside-down "flip text" glyphs, Unicode bidi-override spoofing (the mechanism behind Trojan Source-style attacks), and Cyrillic/Greek homoglyph substitution — and emits a receipt with `raw_hash`, `canonical_hash`, `canonical_text`, the detected `transform_receipt`, and a `lossless` flag.

```bash
python tools/semantic_fingerprint.py compute --text "ʇsǝʇ"
python tools/semantic_fingerprint.py compare --text-a "test" --text-b "ʇsǝʇ"
```

A 160-example synthetic benchmark (`tools/rstf_benchmark.py`) measures detection/recovery accuracy (95.6% overall, 0% false positives on unmodified text) — but that benchmark is circular by construction (it's generated by the same tables the detector uses). Two independent checks exist for that: `tools/rstf_adversarial_eval.py` runs hand-authored/independently-recalled examples (91.7% detection, 0% false positives on legitimate non-English text), and `tools/rstf_dogfood_scan.py` scans this repo's own real `.md`/`.py` files (not a customer pilot — no external party supplied the data) for false positives. Both evals found and fixed real bugs: the homoglyph detector previously flagged all monolingual Cyrillic/Greek text as an attack (100% false positive), and the reversed-text detector flagged ordinary code like `import os` (19 unrelated hits in this repo alone) — see `docs/SEMANTIC_TRANSFORM_FINGERPRINT.md` for what changed and the residual limitations of each fix.

`tools/rstf_token_cost.py` measures whether canonicalization actually reduces UTF-8 byte length — a provable upper bound on token count for byte-level BPE tokenizers — before it reaches a model (26.2% overall byte savings; 0% for plain reversal, as expected, since reordering bytes can't change how many there are).

Beyond the byte proxy, `tools/bpe_tokenizer.py` trains a real byte-level BPE tokenizer (the same algorithm GPT-2/3.5/4, Claude, and Llama use) on this repo's own docs, with a C++ mirror in `cpp/src/tokenizer.cpp` (replacing an earlier single-character-lookup stub) parity-verified against the Python reference by `tools/bpe_parity_check.py`. `tools/rstf_bpe_token_cost.py` measures real token counts with it: 66.4% overall token savings, and — the finding the byte proxy structurally cannot produce — **39.0% savings on plain reversed text**, because BPE merges are learned from forward-reading corpus text and reversing a string breaks them, unlike byte count, which cannot change under reordering. This is OverLLM's own tokenizer trained on a few tens of KB of this repo's own text, not GPT-4/Claude/Llama's production tokenizer — absolute counts aren't production billing, but the algorithm and measurement are genuine, not a proxy.

Read the full guide: [`docs/SEMANTIC_TRANSFORM_FINGERPRINT.md`](docs/SEMANTIC_TRANSFORM_FINGERPRINT.md).

Important truth label: the glyph and homoglyph tables are curated subsets, not exhaustive Unicode confusables data, and the bidi recovery is a simplified reconstruction, not a full UAX#9 implementation. The byte-cost benchmark reports UTF-8 byte length, not real tokenizer token counts, because this environment's egress policy blocks the hosts tiktoken/Hugging Face tokenizers need — the real-BPE benchmark closes that gap with OverLLM's own tokenizer, not a production one. Neither the adversarial eval nor the dogfood scan is a substitute for a real external pilot — no party outside this repo has tested RSTF on their own data yet.

---

## Real transformer learning

`cpp/src/model.cpp` has a real (non-stub) transformer implementation — attention, layer norm, FFN, a full backward pass, AdamW — but nothing previously verified it actually learns: the existing test suite only checks a single training step "completes," and `cpp/train_online.cpp`'s DPO loop trains on uniformly random token pairs, which have no learnable signal by construction. `cpp/tools/train_language_model.cpp` (run via `python tools/transformer_learning_check.py`) trains it as a real next-token language model on real BPE-tokenized text and mechanically checks the loss decreases: 7.41 → 5.20 over 30 epochs (29.8% reduction), no NaN.

Building this found a real bug: run through this repo's actual `-O3 -ffast-math` CMake build (not a looser standalone compile), training diverged to NaN around epoch 15, because `model.cpp` had no gradient clipping anywhere in its training path — a standard safeguard every real transformer training setup uses. Added `overllm_clip_gradients()` to fix it. Full writeup, including the honest limits (tiny corpus, no held-out eval, memorization not generalization): [`docs/TRANSFORMER_LEARNING.md`](docs/TRANSFORMER_LEARNING.md).

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
