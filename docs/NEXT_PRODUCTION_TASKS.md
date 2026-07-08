# Next Production Tasks

The hardening baseline reduces risk, but production requires the next patch set.

## Patch set 2

1. Patch `go/pkg/server/server.go` so mock proof endpoints return `501 not_configured` instead of fake success.
2. Add auth middleware to OverAgent admin endpoints.
3. Add integration test for telemetry normalization.
4. Add integration test for localmodel runner validation.
5. Add release artifact checksum generation.
6. Add one sample signed receipt.

## Patch set 3

1. Add consent CLI/UI for telemetry.
2. Add dashboard release gate status.
3. Add Docker/Compose for cloud demo with explicit CORS and file-root policy.
4. Add versioned releases.
