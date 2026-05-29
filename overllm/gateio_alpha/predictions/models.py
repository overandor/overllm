"""Pydantic models for predictions and outcomes."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Side(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    PREPARE_LONG = "PREPARE_LONG"
    PREPARE_SHORT = "PREPARE_SHORT"


class Outcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    PREPARE_WIN = "PREPARE_WIN"
    PREPARE_LOSS = "PREPARE_LOSS"
    INVALID_DATA = "INVALID_DATA"


class Prediction(BaseModel):
    prediction_id: str
    symbol: str
    created_at: datetime
    horizon_seconds: int = 180
    side: Side
    confidence: float = Field(..., ge=0.0, le=1.0)
    reference_price: float
    spread_bps: float
    features_hash: str
    model_hash: str
    policy_hash: str
    reason: str
    status: str = "PENDING_OUTCOME"  # PENDING_OUTCOME | JUDGED
    receipt_hash: str | None = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class OutcomeRecord(BaseModel):
    prediction_id: str
    judged_at: datetime
    exit_reference_price: float
    gross_return_bps: float
    estimated_fee_bps: float = 0.0
    estimated_slippage_bps: float = 0.0
    net_return_bps: float
    outcome: Outcome
    reward: float
    model_update_applied: bool = False
    receipt_hash: str | None = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class JudgedPrediction(BaseModel):
    prediction: Prediction
    outcome: OutcomeRecord
