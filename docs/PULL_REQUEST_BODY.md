# PR: Production Hardening Baseline

## Summary

This branch begins production hardening for OverLLM. It does not claim final production readiness.

## Changes

- Adds missing Go local model runner package.
- Normalizes Rust/Go telemetry schema.
- Makes telemetry opt-in by default.
- Fixes daemon periodic timer bug.
- Adds CI gates across Go, Rust, OverML, C++, UI, and Python API.
- Adds production status, release gate, security boundary, adoption manifest, and patch notes.

## Remaining blockers

- Proof mock endpoints must be converted to explicit `not_configured` errors or real proof verification.
- OverAgent admin endpoints need authentication.
- CI must run and pass.
- Signed sample receipt still needed.
