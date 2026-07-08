# Security Boundary

OverLLM is local-first research software. This document states the minimum security boundary for production hardening.

## Telemetry

Telemetry is disabled by default. Enable it only with:

```bash
OVERLLM_TELEMETRY=1 ./overllm-telemetry
```

Anonymization is enabled by default. Disable it only for private local debugging:

```bash
OVERLLM_ANONYMIZE=false OVERLLM_TELEMETRY=1 ./overllm-telemetry
```

## Local inference

The Go server calls the standalone C++ inference binary through `go/pkg/localmodel`. This keeps the model runtime in a bounded child process instead of loading mutable native state into the HTTP server process.

Required environment variables when defaults are not valid:

```bash
OVERLLM_INFERENCE_BINARY=./overllm_inference
OVERLLM_VOCAB_PATH=./vocab.txt
OVERLLM_MODEL_PATH=./models/overllm.bin
OVERLLM_MODEL_TIMEOUT=60s
```

## Proof endpoints

Proof endpoints must not return mock proof as valid proof. If proof infrastructure is missing, endpoints must return `not_configured`, `partial`, or an error status.

## Admin endpoints

Endpoints that issue/list API keys or expose agent memory must be protected before public deployment. Do not expose the local Go server directly to the public internet.

## Cloud demo

The cloud API is separate from the offline local agent. Deploy it only with explicit CORS origins, locked-down file roots, and disabled terminal execution.
