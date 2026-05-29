"""FastAPI router for the Gate.io Alpha Engine."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from overllm.gateio_alpha.engine import AlphaEngine
from overllm.gateio_alpha.predictions.store import PredictionStore

router = APIRouter(tags=["gateio-alpha"])

# Global engine instance (managed by lifespan in main.py)
_engine: AlphaEngine | None = None


def set_engine(engine: AlphaEngine) -> None:
    global _engine
    _engine = engine


# ------------------------------------------------------------------
# Models
# ------------------------------------------------------------------
class PredictRequest(BaseModel):
    symbol: str


class StartRequest(BaseModel):
    interval_seconds: float = 60.0


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@router.get("/status")
def alpha_status() -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    return _engine.status()


@router.post("/predict/once")
def predict_once(req: PredictRequest) -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    return _engine.predict_once(req.symbol)


@router.post("/engine/start")
def start_engine(req: StartRequest | None = None) -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    _engine.start()
    return {"status": "started", "running": _engine.is_running}


@router.post("/engine/stop")
def stop_engine() -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    _engine.stop()
    return {"status": "stopped", "running": _engine.is_running}


@router.get("/predictions/live")
def live_predictions() -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    store = _engine.store
    pending = store.list_pending()
    return {
        "predictions": [p.model_dump() for p in pending],
        "count": len(pending),
    }


@router.get("/predictions/pending")
def pending_predictions(symbol: str | None = None) -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    store = _engine.store
    pending = store.list_pending(symbol=symbol)
    return {
        "predictions": [p.model_dump() for p in pending],
        "count": len(pending),
    }


@router.get("/predictions/history")
def prediction_history(symbol: str | None = None, limit: int = 200) -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    store = _engine.store
    history = store.list_history(symbol=symbol, limit=limit)
    return {
        "predictions": [p.model_dump() for p in history],
        "count": len(history),
    }


@router.get("/predictions/{prediction_id}")
def get_prediction(prediction_id: str) -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    store = _engine.store
    judged = store.get_judged(prediction_id)
    if judged:
        return {"judged": True, **judged.model_dump()}
    pred = store.get_prediction(prediction_id)
    if pred:
        return {"judged": False, "prediction": pred.model_dump()}
    raise HTTPException(status_code=404, detail="Prediction not found")


@router.get("/performance")
def performance(symbol: str | None = None) -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    store = _engine.store
    stats = store.performance_stats(symbol=symbol)
    by_symbol = store.accuracy_by_symbol()
    return {
        "stats": stats,
        "accuracy_by_symbol": by_symbol,
        "calibration": _engine.policy.calibration_stats() if _engine else {},
    }


@router.get("/receipts")
def list_receipts(symbol: str | None = None, limit: int = 200) -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    store = _engine.store
    judged = store.list_judged(symbol=symbol, limit=limit)
    return {
        "receipts": [
            {
                "prediction_id": j.prediction.prediction_id,
                "prediction_receipt_hash": j.prediction.receipt_hash,
                "outcome_receipt_hash": j.outcome.receipt_hash,
                "side": j.prediction.side.value,
                "outcome": j.outcome.outcome.value,
                "net_return_bps": j.outcome.net_return_bps,
            }
            for j in judged
        ],
        "count": len(judged),
    }


@router.post("/judge/pending")
def judge_pending() -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    outcomes = _engine.judge_pending()
    return {"judged": len(outcomes), "outcomes": outcomes}


@router.get("/model")
def model_info() -> dict[str, Any]:
    if not _engine:
        raise HTTPException(status_code=503, detail="Alpha engine not initialized")
    return {
        "model_hash": _engine.model_hash,
        "policy_hash": _engine.policy.policy_hash,
        "policy_epsilon": _engine.policy.epsilon,
        "q_table_size": len(_engine.policy.q_table),
    }
