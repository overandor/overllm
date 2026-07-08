# Release Gate Policy

OverLLM cannot be labeled production-ready until the release gate passes.

## Required checks

- GitHub Actions production-hardening workflow passes on the release commit.
- Native Go agent compiles and tests.
- Rust telemetry crate compiles and tests.
- OverML tests pass.
- C++ engine builds on macOS.
- UI builds.
- Python API imports successfully.

## Required evidence

- Commit SHA.
- Build logs.
- Test logs.
- One end-to-end receipt.
- Signed release artifact checksums.
- Telemetry consent documentation.
- Admin/authentication documentation.

## Blockers

A release is blocked if any of these are true:

- A public endpoint returns mock proof data as if it were valid proof.
- Admin endpoints can issue or list API keys without authentication.
- Telemetry collects app/file/process/network data without opt-in.
- The local model runner is unavailable but the release claims local inference works.
- A fork claims production readiness without publishing its adoption manifest.
