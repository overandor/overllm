# Production Patch Notes

This branch is a hardening baseline, not a final production release.

## Code changes

- Added `go/pkg/localmodel/runner.go` to provide the missing local-model package used by the Go server.
- Normalized Rust telemetry payloads with Go telemetry ingestion by accepting both `event_type` and `type`.
- Made all Rust telemetry collection opt-in by default.
- Fixed periodic daemon scheduling with deterministic loop counters.

## Process changes

- Added production hardening CI workflow.
- Added URAP-1 adoption manifest.
- Added production hardening checklist.
- Added release gate policy.
- Added security boundary documentation.

## Not fixed in this branch

- Mock proof endpoints still need a direct server patch.
- OverAgent API-key/admin endpoints still need auth middleware.
- CI must run and be reviewed before merge.
