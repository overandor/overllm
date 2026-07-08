# Production Status

Current status: `hardening-baseline`.

This means the repository has begun production hardening but must not yet be described as fully production-ready.

## Ready to review

- Missing local model runner package added.
- Telemetry schema normalized.
- Telemetry opt-in enforced in Rust collection functions.
- Daemon timer bug fixed.
- CI workflow added.
- Release gate, security boundary, adoption manifest, and patch notes added.

## Not ready

- Proof endpoints still require direct non-mock enforcement.
- OverAgent admin endpoints still require authentication.
- CI needs to run and pass.
- A signed sample receipt still needs to be generated and committed or attached to a release.
