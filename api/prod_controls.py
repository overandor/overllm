"""Runtime production controls for OverLLM.

This module adds deployment-grade controls without changing OverLLM's core claim
boundary. It is intentionally small, dependency-light, and safe by default:

- request IDs for traceability;
- basic security headers;
- optional API-key protection for sensitive endpoints;
- in-memory per-client rate limiting;
- readiness reporting for production-candidate deployments.

The API key feature is opt-in: set OVERLLM_API_KEY. Public demo deployments can
remain open, but production deployments should set it and place the service
behind a real gateway/WAF.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

SENSITIVE_PATH_PREFIXES = (
    "/api/finance",
    "/api/files",
    "/api/generate",
    "/api/terminal",
    "/api/gate",
    "/inference",
    "/train",
    "/test",
)

PUBLIC_PATHS = (
    "/",
    "/health",
    "/ready",
    "/docs",
    "/openapi.json",
)

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-store",
}


@dataclass(frozen=True)
class RuntimeControlConfig:
    deployment_class: str
    api_key_configured: bool
    auth_required: bool
    rate_limit_enabled: bool
    rate_limit_per_minute: int
    cors_origins: list[str]
    terminal_enabled: bool
    file_root: str
    ledger_secret_configured: bool
    approval_gate_required: bool
    live_trading_enabled: bool
    autonomous_outbound_enabled: bool
    release_sha: str
    operator_contact: str


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str) -> list[str]:
    return [part.strip() for part in os.getenv(name, "").split(",") if part.strip()]


def runtime_control_config() -> RuntimeControlConfig:
    deployment_class = os.getenv("OVERLLM_DEPLOYMENT_CLASS", "local-demo").strip() or "local-demo"
    api_key = os.getenv("OVERLLM_API_KEY", "")
    rate_limit_per_minute = int(os.getenv("OVERLLM_RATE_LIMIT_PER_MINUTE", "60"))
    return RuntimeControlConfig(
        deployment_class=deployment_class,
        api_key_configured=bool(api_key),
        auth_required=_env_flag("OVERLLM_REQUIRE_API_KEY", "1" if api_key else "0"),
        rate_limit_enabled=_env_flag("OVERLLM_RATE_LIMIT_ENABLED", "1"),
        rate_limit_per_minute=max(rate_limit_per_minute, 1),
        cors_origins=_csv_env("OVERLLM_CORS_ORIGINS"),
        terminal_enabled=_env_flag("OVERLLM_ENABLE_TERMINAL", "0"),
        file_root=str(Path(os.getenv("OVERLLM_FILE_ROOT", ".")).resolve()),
        ledger_secret_configured=bool(os.getenv("OVERLLM_LEDGER_SECRET", "")),
        approval_gate_required=_env_flag("OVERLLM_APPROVAL_GATE_REQUIRED", "1"),
        live_trading_enabled=_env_flag("OVERLLM_LIVE_TRADING_ENABLED", "0"),
        autonomous_outbound_enabled=_env_flag("OVERLLM_AUTONOMOUS_OUTBOUND_ENABLED", "0"),
        release_sha=os.getenv("OVERLLM_RELEASE_SHA", ""),
        operator_contact=os.getenv("OVERLLM_OPERATOR_CONTACT", ""),
    )


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _is_sensitive_path(path: str, prefixes: Iterable[str] = SENSITIVE_PATH_PREFIXES) -> bool:
    return any(path == prefix or path.startswith(f"{prefix}/") for prefix in prefixes)


def _is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or path.startswith("/static/")


def _authorized(request: Request, configured_key: str) -> bool:
    if not configured_key:
        return False
    supplied = request.headers.get("x-overllm-api-key", "")
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        supplied = auth.split(" ", 1)[1].strip()
    return secrets.compare_digest(supplied, configured_key)


class InMemoryRateLimiter:
    """Small sliding-window limiter for single-process demos/pilots.

    Production deployments behind multiple workers should also use gateway-level
    rate limiting. This guard still prevents accidental local abuse and gives a
    concrete runtime control without adding Redis or another dependency.
    """

    def __init__(self, limit_per_minute: int):
        self.limit_per_minute = max(limit_per_minute, 1)
        self.window_seconds = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        now = now or time.time()
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= self.limit_per_minute:
            return False
        hits.append(now)
        return True


class ProductionControlMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config_factory: Callable[[], RuntimeControlConfig] = runtime_control_config):
        super().__init__(app)
        self.config_factory = config_factory
        config = config_factory()
        self.rate_limiter = InMemoryRateLimiter(config.rate_limit_per_minute)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req-{uuid.uuid4().hex[:16]}"
        config = self.config_factory()
        path = request.url.path
        client = _client_id(request)

        if config.rate_limit_enabled and not _is_public_path(path):
            if not self.rate_limiter.allow(f"{client}:{path}"):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limited",
                        "request_id": request_id,
                        "limit_per_minute": config.rate_limit_per_minute,
                    },
                    headers={"X-Request-ID": request_id},
                )

        if config.auth_required and _is_sensitive_path(path):
            if not _authorized(request, os.getenv("OVERLLM_API_KEY", "")):
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "unauthorized",
                        "request_id": request_id,
                        "detail": "Sensitive OverLLM endpoint requires X-OverLLM-API-Key or Bearer token.",
                    },
                    headers={"X-Request-ID": request_id, "WWW-Authenticate": "Bearer"},
                )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-OverLLM-Deployment-Class"] = config.deployment_class
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


def build_readiness_report() -> dict:
    config = runtime_control_config()
    checks: dict[str, dict[str, str | bool]] = {}

    def add(name: str, ok: bool, detail: str) -> None:
        checks[name] = {"ok": ok, "detail": detail}

    production_like = config.deployment_class in {"controlled-pilot", "public-demo", "production"}
    production = config.deployment_class == "production"

    add("terminal_disabled", not config.terminal_enabled, "Public terminal execution must remain disabled.")
    add("cors_allowlisted", bool(config.cors_origins), "Set explicit OVERLLM_CORS_ORIGINS for browser deployments.")
    add("approval_gate_required", config.approval_gate_required, "Outbound actions require a human approval gate by default.")
    add("live_trading_disabled", not config.live_trading_enabled, "Live trading/financial movement must be disabled unless separately reviewed.")
    add("autonomous_outbound_disabled", not config.autonomous_outbound_enabled, "Autonomous outbound actions must be disabled unless separately approved.")
    add("file_root_scoped", bool(config.file_root), "OVERLLM_FILE_ROOT resolves to a concrete path.")
    add("rate_limit_enabled", config.rate_limit_enabled, "Runtime rate limiting should be enabled.")

    if production_like:
        add("api_key_configured", config.api_key_configured, "Set OVERLLM_API_KEY for sensitive endpoints in pilot/public/prod.")
        add("ledger_secret_configured", config.ledger_secret_configured, "Set OVERLLM_LEDGER_SECRET for signed diligence evidence.")
    else:
        add("api_key_configured", True, "Optional for local demos.")
        add("ledger_secret_configured", True, "Optional for unsigned local demos.")

    if production:
        add("release_sha_recorded", bool(config.release_sha), "Set OVERLLM_RELEASE_SHA for production deploy traceability.")
        add("operator_contact_recorded", bool(config.operator_contact), "Set OVERLLM_OPERATOR_CONTACT for incident ownership.")
    else:
        add("release_sha_recorded", True, "Required only for production class.")
        add("operator_contact_recorded", True, "Required only for production class.")

    ready = all(bool(item["ok"]) for item in checks.values())
    return {
        "status": "ready" if ready else "not_ready",
        "deployment_class": config.deployment_class,
        "production_ready": ready and production,
        "pilot_ready": ready and production_like,
        "controls": {
            "auth_required": config.auth_required,
            "api_key_configured": config.api_key_configured,
            "rate_limit_enabled": config.rate_limit_enabled,
            "rate_limit_per_minute": config.rate_limit_per_minute,
            "cors_origins_count": len(config.cors_origins),
            "file_root": config.file_root,
        },
        "checks": checks,
    }


def install_prod_controls(app) -> None:
    app.add_middleware(ProductionControlMiddleware)
