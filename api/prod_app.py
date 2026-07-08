"""Production-candidate ASGI entrypoint for OverLLM.

Run public or pilot deployments with this entrypoint instead of `api.main:app`:

    uvicorn api.prod_app:app --host 0.0.0.0 --port 8000

It imports the existing OverLLM API and adds runtime controls from
`api.prod_controls`: request IDs, security headers, optional API-key protection,
rate limiting, and a readiness endpoint.
"""

from __future__ import annotations

from fastapi.responses import JSONResponse

try:
    from api.main import app
    from api.prod_controls import build_readiness_report, install_prod_controls
except Exception:  # pragma: no cover - supports direct execution from api/
    from main import app
    from prod_controls import build_readiness_report, install_prod_controls

install_prod_controls(app)


@app.get("/ready", tags=["operations"])
async def readiness():
    """Return deployment readiness status for pilot/production gates."""
    report = build_readiness_report()
    status_code = 200 if report["status"] == "ready" else 503
    return JSONResponse(status_code=status_code, content=report)
