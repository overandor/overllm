# Production Readiness Audit & Fix Log

This document is the honest, verified account of what's actually solid in
this repo versus what still isn't — not a marketing claim. Every item below
was confirmed by reading the source and, where possible, running the actual
build/test tooling (not by inference from documentation, which had drifted
from the code in several places this audit found).

## Fixed in this pass

| Issue | Where | Severity | Verified by |
|---|---|---|---|
| `go build ./...` failed outright — `server.go` imported `pkg/localmodel`, which didn't exist anywhere in the repo | `go/pkg/server/server.go` | Critical — the entire Go agent could not compile | `go build ./...` now succeeds; `go/pkg/localmodel/localmodel.go` implements the `Runner` interface the rest of the code already assumed (shells out to the compiled C++ inference binary, matches the existing graceful `s.Model == nil` degradation pattern) |
| Telemetry JSON schema mismatch — Rust's `TelemetryEvent` always serializes the type field as `event_type`; Go's struct expected `type`. `json.Unmarshal` doesn't error on unmatched fields, it just leaves them zero-valued, so every ingested event's `Type` was silently `""` and `BuildContext()`'s `switch ev.Type` never matched any case | `go/pkg/agent/agent.go` | Critical — telemetry could flow all day and the "personal context" the whole README is about was always empty | `TestTelemetryEvent_DecodesRustWireFormat`, `TestBuildContext_FormatsIngestedEvents` in `go/pkg/agent/agent_test.go` |
| Telemetry permanently disabled — `telemetry::set_telemetry_enabled` was defined but never called from the daemon entrypoint, so `TELEMETRY_ENABLED` stayed at its default (`false`) forever; `get_active_app`/`get_top_processes`/`get_recent_files`/`get_network_summary` all silently returned nothing | `rust/src/main.rs` | High | Now wired to `OVERLLM_TELEMETRY_ENABLED` (opt-in, default off — this is privacy-sensitive data, so the *safe* default didn't change, only its visibility did), with an explicit startup log line stating which state it's in |
| Timing bug — `tokio::time::Instant::now().elapsed().as_secs() % 30 == 0` creates the `Instant` and reads its elapsed time in the same expression, so `elapsed()` is always ~0 and the modulo is always true. The "every 30s" blockchain check and "every 5 minutes" article ingestion actually ran on every 5-second tick | `rust/src/main.rs` | Medium (correctness/cost, not a compile or security issue) | Code inspection + successful `cargo build`/`cargo test`; replaced with tracked `last_run: Instant` variables compared against elapsed time, the standard pattern — not covered by a dedicated flaky time-based unit test, noted here rather than silently claimed |
| `/api/overagent/keys` had no authentication at all — `GET` returned every issued API key's raw secret, `POST` let anyone mint new keys, both with `Access-Control-Allow-Origin: *` | `go/pkg/server/server.go` | Critical (credential leak + unauthenticated privilege grant) | Now requires `Authorization: Bearer <OVERLLM_ADMIN_TOKEN>`, fails **closed** (503) if no token is configured rather than open, and the `GET` listing masks keys to a preview (`ovllm_0123456789...ffff`) — full secrets are only ever returned once, in the `POST` response, matching normal credential-issuance practice. `go/pkg/server/server_test.go` covers no-token / wrong-token / correct-token+masking |
| No CI coverage for `go/` or `rust/` at all — the broken Go build above shipped straight to `main` because nothing ever ran `go build` on it | `.github/workflows/go.yml`, `.github/workflows/rust.yml` | High (process, not a code bug) | Both workflows run in this PR |

## Still not production-ready (deliberately not touched in this pass)

Scope discipline matters more than a bigger diff here — these are real,
larger efforts, not something to half-fix alongside the above:

- **C++ inference engine is a genuine transformer implementation, but a
  simplified one.** Fixed-size 50-token generation (ignores `maxTokens`),
  a whitespace/punctuation tokenizer, no real backprop-driven training loop
  wired end-to-end. See `cpp/src/inference_main.cpp`.
- **DPO training is approximate at the Go/Python boundary.** The
  `generationLoop`/`GenerateWithWebContext` placeholders described in the
  original audit are real — `go/pkg/agent/agent.go`'s comments say so
  directly. `handleGenerate` (the actual `/api/generate` route) *does* call
  the real `localmodel.Runner` now that it compiles, but the periodic
  `generationLoop` background task is still a logged placeholder, not
  wired to it.
- **Proof/receipt generation falls back to mock data when the Rust proof
  daemon is unavailable**, and does so *honestly* — the fallback path logs
  `"Proof daemon unavailable, using mock receipt"` and the response embeds
  `"proof_signature": "mock_sig"` rather than pretending to be real. That's
  arguably correct behavior for a local-first tool with an optional proof
  backend, not a bug to "fix" by deleting the fallback — but it means proof
  receipts are not yet a dependable guarantee, and should not be marketed
  as one until the daemon path is exercised in CI.
- **Other `/api/overagent/*` and `/api/proof/*` routes still have
  `Access-Control-Allow-Origin: *` with no auth.** Only `/api/overagent/keys`
  was hardened here, because it was the one confirmed to leak credentials
  and grant privilege (minting keys). A full auth/CORS pass across the rest
  of the admin surface is real follow-up work, not done here.
- **C++/CMake build has no CI.** `go.yml` and `rust.yml` cover those two
  toolchains; the C++ engine's build (`cpp/`, via `build.sh`/CMake) is
  macOS/Xcode-specific and untested in CI in this pass.
