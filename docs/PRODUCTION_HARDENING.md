# Production Hardening Checklist

This document separates what has been hardened from what still blocks a production release.

## Hardened in `prod/hardening-baseline`

- Added a local model runner package at `go/pkg/localmodel` so `server.go` no longer imports a missing package.
- Normalized telemetry schema compatibility between the Rust daemon (`event_type`) and Go agent (`type`).
- Made telemetry fully opt-in through `OVERLLM_TELEMETRY=1`.
- Kept anonymization on by default through `OVERLLM_ANONYMIZE=true`.
- Fixed daemon periodic scheduling so 30-second and 5-minute jobs no longer run every loop.
- Added CI gates for Go, Rust telemetry, OverML, C++, UI, and Python API import checks.

## Production blockers still remaining

These must be resolved before calling OverLLM production-ready:

1. Replace mock proof endpoints in `go/pkg/server/server.go` with explicit `not_configured` errors or real proof verification.
2. Add authentication and authorization to all OverAgent admin endpoints, especially API-key issuing/listing.
3. Add integration tests for `prompt -> local model -> receipt -> dashboard`.
4. Publish one signed sample receipt and the exact command sequence that produced it.
5. Add a telemetry consent UI or CLI flow instead of relying only on environment variables.
6. Verify CI results on GitHub Actions and pin any failing toolchain versions.
7. Add release artifacts and checksums for binaries / DMG packages.
8. Document operational security boundaries for local file access, command execution, proof storage, and API deployment.

## Release gate

A production release must not be cut until all CI jobs pass and the remaining blockers above are either closed or explicitly scoped out of the release.
