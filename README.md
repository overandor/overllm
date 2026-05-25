# OverLLM

A personal-contextual LLM built from scratch in **C++**, **Go**, and **Rust**.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR MAC (macOS ARM64)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Rust Daemon │  │  Go Agent    │  │  C++ Engine  │       │
│  │  telemetry   │──│  orchestrator│──│  inference   │       │
│  │  collector   │  │  + DPO loop  │  │  + training  │       │
│  └──────────────┘  └──────┬───────┘  └──────────────┘       │
│                             │                                  │
│                        ┌────┴────┐                             │
│                        │  Ollama │  (teacher / data source)    │
│                        └─────────┘                             │
└─────────────────────────────────────────────────────────────┘
```

## Core Concept: Punishment-as-Reward

OverLLM learns to out-perform its Ollama teacher through **Direct Preference Optimization (DPO)**:

- **Punished** (`rejected`): Ollama generates a response **without** system context → generic, impersonal
- **Rewarded** (`chosen`): Ollama generates a response **with** full telemetry context → personalized, actionable
- OverLLM is trained to **maximize the margin** between chosen and rejected, learning to exploit system metadata

The Rust daemon continuously harvests:
- Active application / window
- File system access patterns
- Process resource consumption
- Network connections
- CPU / RAM telemetry
- Context switches (proxy for clicks/interactions)

This telemetry is injected into every prompt, making OverLLM hyper-aware of your current state.

## Components

### C++ — Inference Engine (`cpp/`)
- Custom tensor ops (matmul, softmax, GELU, layer norm)
- Multi-head causal self-attention
- Transformer decoder stack
- C API for cgo interop
- Binary weight save/load format

### Go — Agent (`go/`)
- HTTP telemetry ingestion endpoint (`:7749/telemetry`)
- Ollama API client with punished/rewarded modes
- Automatic preference pair generation every 30s
- DPO batch queue management
- Status REST API (`/api/status`, `/api/context`, `/api/generate`)

### Rust — Telemetry Daemon (`rust/`)
- Active app detection (AppleScript)
- System stats (CPU, RAM via `ps`)
- Top process monitoring
- Recent file access (`lsof`)
- Network summary (`netstat`)
- Async HTTP publisher to Go agent

### Python — Training Bridge (`training/`)
- `generate.py`: Manual Ollama data generation
- `dpo_trainer.py`: NumPy-based DPO trainer that exports to C++ weight format

## Build

```bash
./build.sh
```

Requires:
- macOS with Xcode / `clang++`
- CMake (`brew install cmake`)
- Go 1.26+ (`brew install go`)
- Rust (`rustup`)
- Ollama running locally

## Quick Start

```bash
# Terminal 1: Ollama (if not already running)
ollama serve

# Terminal 2: Agent
./overllm-agent

# Terminal 3: Telemetry
./overllm-telemetry

# Terminal 4: Generate training data
python training/generate.py --count 20

# Terminal 4: Train OverLLM
python training/dpo_trainer.py --epochs 10 --export models/overllm.bin

# Terminal 4: Run inference
./overllm_inference vocab.txt models/overllm.bin "What should I do next?"
```

## HTTP API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telemetry` | POST | Ingest event from Rust daemon |
| `/api/status` | GET | Agent status, queue size |
| `/api/context` | GET | Current telemetry context window |
| `/api/generate` | POST | Generate with full context via Ollama |
| `/api/preference_queue` | GET | DPO batch queue status |

## Data Flow

1. Rust daemon polls macOS every 5s → sends events to Go agent
2. Go agent accumulates a rolling 100-event context window
3. Every 30s, Go queries Ollama twice:
   - Without context → `rejected` (punished)
   - With context → `chosen` (rewarded)
4. Preference pair persisted to `~/.overllm/data/preferences.jsonl`
5. Python DPO trainer loads pairs, trains model, exports `.bin` weights
6. C++ engine loads `.bin` and runs fast local inference

## Why Custom Code?

Unlike frameworks that hide internals, OverLLM exposes every layer:
- **C++ tensors**: No PyTorch, no CUDA dependencies, pure CPU
- **Go orchestration**: Native concurrency, tiny binary, no Python runtime
- **Rust telemetry**: Zero-cost abstractions, safe system access

This stack compiles to ~50MB total and runs entirely offline on your Mac.

## Roadmap

- [x] DMG packaging for one-click install
- [ ] Full backpropagation in C++ for end-to-end DPO training
- [ ] Byte-pair encoding tokenizer
- [ ] Quantization (Q4/Q8) for faster inference
- [ ] Metal GPU backend for C++ engine
- [ ] Click-level accessibility tracking (requires permission)
- [ ] Automatic weight reloading without restart
- [ ] Web deployment (Vercel + Hugging Face)

## Deployment

### Web Version

#### Frontend (Vercel)
```bash
cd ui
cp .env.example .env.local
# Set VITE_API_URL to your deployed backend URL
vercel deploy
```

#### Backend (Hugging Face Spaces)
1. Go to https://huggingface.co/spaces
2. Create a new Space with Docker runtime
3. Clone the Space locally
4. Copy the Dockerfile from this repository
5. Push to the Space
6. The Space will automatically build and deploy the Go backend

**Note**: C++ inference and Rust telemetry are macOS-specific and not included in web deployment. The web version uses Ollama API for generation.

### macOS Desktop
- Build DMG: `./build_dmg.sh`
- Requires macOS ARM64 with Ollama installed

## License

MIT / OverLLM Project
