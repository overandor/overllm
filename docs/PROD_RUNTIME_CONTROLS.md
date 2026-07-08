# Production Runtime Controls

OverLLM now has a production-candidate ASGI entrypoint:

```bash
uvicorn api.prod_app:app --host 0.0.0.0 --port 8000
```

Use `api.prod_app:app` for controlled pilots, public demos, and production-candidate deployments. The older `api.main:app` remains useful for local development, but the production entrypoint adds runtime controls that are expected in operated environments.

## Controls added

| Control | What it does | Why it matters |
|---|---|---|
| Request ID | Adds or propagates `X-Request-ID` | Makes logs and incidents traceable. |
| Security headers | Adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Cache-Control` | Gives public deployments safer browser defaults. |
| Optional API-key guard | Protects sensitive paths when `OVERLLM_API_KEY` / `OVERLLM_REQUIRE_API_KEY` are configured | Prevents public access to generation, files, finance exports, and other sensitive API paths. |
| Rate limiting | In-memory per-client/per-path sliding-window limiter | Prevents accidental local/public abuse without adding Redis. |
| Readiness endpoint | Adds `/ready` with deployment-class checks | Gives Render/Fly/VM/Kubernetes-style platforms a deploy gate. |

## Sensitive paths

When API-key auth is required, the production middleware protects:

- `/api/finance*`
- `/api/files*`
- `/api/generate*`
- `/api/terminal*`
- `/api/gate*`
- `/inference*`
- `/train*`
- `/test*`

Public paths remain open:

- `/`
- `/health`
- `/ready`
- `/docs`
- `/openapi.json`
- `/static/*`

## Environment variables

| Variable | Default | Production guidance |
|---|---|---|
| `OVERLLM_API_KEY` | empty | Set through deployment secret store for pilot/public/prod. |
| `OVERLLM_REQUIRE_API_KEY` | `1` if key is set, else `0` | Set to `1` in controlled-pilot/public-demo/production deployments. |
| `OVERLLM_RATE_LIMIT_ENABLED` | `1` | Keep enabled. Add gateway-level limiting for serious production. |
| `OVERLLM_RATE_LIMIT_PER_MINUTE` | `60` | Tune per deployment. |
| `OVERLLM_DEPLOYMENT_CLASS` | `local-demo` | Use `controlled-pilot`, `public-demo`, or `production` when appropriate. |
| `OVERLLM_RELEASE_SHA` | empty | Required for production readiness. |
| `OVERLLM_OPERATOR_CONTACT` | empty | Required for production readiness. |
| `OVERLLM_LEDGER_SECRET` | empty | Required for signed evidence outside local demos. |
| `OVERLLM_CORS_ORIGINS` | localhost defaults in main API | Must be explicit for browser deployments. |
| `OVERLLM_ENABLE_TERMINAL` | `0` | Must remain `0` in public deployments. |
| `OVERLLM_APPROVAL_GATE_REQUIRED` | `1` | Must remain `1` unless separately threat-modeled. |
| `OVERLLM_LIVE_TRADING_ENABLED` | `0` | Must remain `0` unless separately reviewed. |
| `OVERLLM_AUTONOMOUS_OUTBOUND_ENABLED` | `0` | Must remain `0` unless separately approved. |

## API-key usage

Send either header:

```bash
X-OverLLM-API-Key: <secret>
```

or:

```bash
Authorization: Bearer <secret>
```

Do not put the key in URLs, client-side code, public repos, browser-visible config, logs, screenshots, or READMEs.

## Readiness behavior

`/ready` returns:

- HTTP 200 when the selected deployment class has its required controls configured;
- HTTP 503 when required controls are missing.

For local demos, API key and ledger secret are optional. For controlled pilots, public demos, and production-candidate deployments, the readiness check expects stronger controls.

Production readiness is still not automatic. A production deployment also needs the gates in `PRODUCTION_READY.md`: release tag, CI, monitoring, backup/restore, rollback, incident owner, truthful claims, and evidence integrity.

## Minimal controlled-pilot env

```bash
OVERLLM_DEPLOYMENT_CLASS=controlled-pilot
OVERLLM_REQUIRE_API_KEY=1
OVERLLM_API_KEY=<set-in-secret-store>
OVERLLM_RATE_LIMIT_ENABLED=1
OVERLLM_RATE_LIMIT_PER_MINUTE=60
OVERLLM_CORS_ORIGINS=https://your-demo.example
OVERLLM_LEDGER_SECRET=<set-in-secret-store>
OVERLLM_ENABLE_TERMINAL=0
OVERLLM_APPROVAL_GATE_REQUIRED=1
OVERLLM_LIVE_TRADING_ENABLED=0
OVERLLM_AUTONOMOUS_OUTBOUND_ENABLED=0
```

Then run:

```bash
uvicorn api.prod_app:app --host 0.0.0.0 --port 8000
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready
```
