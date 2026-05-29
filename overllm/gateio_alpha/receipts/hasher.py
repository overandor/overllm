"""Canonical JSON + SHA256 receipt hasher."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def _canonical_dumps(obj: dict[str, Any]) -> str:
    """Stable JSON without whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def canonical_hash(obj: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_dumps(obj).encode()).hexdigest()


def make_prediction_receipt(prediction: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "type": "prediction",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prediction": prediction,
        "runtime": "overllm-gateio-alpha",
        "version": "0.1.0",
    }
    payload["hash"] = canonical_hash(payload)
    return payload


def make_outcome_receipt(outcome: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "type": "outcome",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "outcome": outcome,
        "runtime": "overllm-gateio-alpha",
        "version": "0.1.0",
    }
    payload["hash"] = canonical_hash(payload)
    return payload
