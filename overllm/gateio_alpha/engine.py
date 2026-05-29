"""Main orchestrator: runs the 3-minute self-judging alpha loop."""
from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import datetime, timezone
from typing import Any

from overllm.gateio_alpha.gate.client import GateioFuturesClient
from overllm.gateio_alpha.gate.symbols import SymbolUniverse
from overllm.gateio_alpha.features.engine import FeatureEngine
from overllm.gateio_alpha.learning.q_learning import QPolicy
from overllm.gateio_alpha.predictions.judge import ThreeMinuteOutcomeJudge
from overllm.gateio_alpha.predictions.models import Prediction, Side
from overllm.gateio_alpha.predictions.store import PredictionStore
from overllm.gateio_alpha.receipts.hasher import make_prediction_receipt
from overllm.gateio_alpha.risk.governor import RiskGovernor


class AlphaEngine:
    """OverLLM Gate.io 3-Minute Self-Judging Alpha Engine."""

    def __init__(
        self,
        symbols: list[str] | None = None,
        interval_seconds: float = 60.0,
        db_path: str | None = None,
        model_hash: str = "sha256:overllm-local-model-v0",
    ) -> None:
        self.universe = SymbolUniverse(symbols)
        self.client = GateioFuturesClient()
        self.features = FeatureEngine(self.client)
        self.store = PredictionStore(db_path)
        self.judge = ThreeMinuteOutcomeJudge(self.store, self.client)
        self.risk = RiskGovernor()
        self.policy = QPolicy()
        self.model_hash = model_hash
        self.interval = interval_seconds
        self._running = False
        self._task: asyncio.Task[Any] | None = None
        self._last_log: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Engine control
    # ------------------------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._loop())

    def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------
    async def _loop(self) -> None:
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                self._last_log["last_error"] = str(exc)
            # Judge pending regardless of prediction success
            try:
                self.judge.tick()
            except Exception as exc:
                self._last_log["last_judge_error"] = str(exc)
            await asyncio.sleep(self.interval)

    async def _tick(self) -> None:
        for symbol in self.universe.all():
            try:
                features = self.features.build(symbol)
            except Exception as exc:
                self._last_log["last_feature_error"] = {symbol: str(exc)}
                continue

            action, confidence = self.policy.select_action(features, symbol)
            side = self._action_to_side(action)

            allowed, veto_reason = self.risk.check(symbol, features, confidence)
            if not allowed:
                self._last_log["last_veto"] = {symbol: veto_reason}
                continue

            pred_id = f"pred_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}_{symbol}"
            pred = Prediction(
                prediction_id=pred_id,
                symbol=symbol,
                created_at=datetime.now(timezone.utc),
                horizon_seconds=180,
                side=side,
                confidence=confidence,
                reference_price=features["reference_price"],
                spread_bps=features["spread_bps"],
                features_hash=self.features.hash_features(features),
                model_hash=self.model_hash,
                policy_hash=self.policy.policy_hash,
                reason=f"action={action} regime={features.get('regime_label')} mom={features.get('momentum_score', 0):.3f}",
                status="PENDING_OUTCOME",
            )

            # Receipt
            receipt = make_prediction_receipt(pred.model_dump())
            pred.receipt_hash = receipt["hash"]

            self.store.insert_prediction(pred)
            self.risk.record_prediction(symbol)
            self._last_log["last_prediction"] = pred.model_dump()

    # ------------------------------------------------------------------
    # Manual / API helpers
    # ------------------------------------------------------------------
    def predict_once(self, symbol: str) -> dict[str, Any]:
        features = self.features.build(symbol)
        action, confidence = self.policy.select_action(features, symbol)
        side = self._action_to_side(action)
        allowed, veto_reason = self.risk.check(symbol, features, confidence)
        if not allowed:
            return {"veto": True, "reason": veto_reason, "features": features}

        pred_id = f"pred_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}_{symbol}"
        pred = Prediction(
            prediction_id=pred_id,
            symbol=symbol,
            created_at=datetime.now(timezone.utc),
            horizon_seconds=180,
            side=side,
            confidence=confidence,
            reference_price=features["reference_price"],
            spread_bps=features["spread_bps"],
            features_hash=self.features.hash_features(features),
            model_hash=self.model_hash,
            policy_hash=self.policy.policy_hash,
            reason=f"action={action} regime={features.get('regime_label')}",
            status="PENDING_OUTCOME",
        )
        receipt = make_prediction_receipt(pred.model_dump())
        pred.receipt_hash = receipt["hash"]
        self.store.insert_prediction(pred)
        self.risk.record_prediction(symbol)
        return {
            "prediction": pred.model_dump(),
            "receipt": receipt,
            "features": features,
        }

    def judge_pending(self) -> list[dict[str, Any]]:
        outcomes = self.judge.tick()
        # Update Q-learning
        for out in outcomes:
            pred = self.store.get_prediction(out.prediction_id)
            if pred:
                try:
                    next_features = self.features.build(pred.symbol)
                except Exception:
                    next_features = {}
                self.policy.update(
                    features={"side": pred.side.value, "confidence": pred.confidence},  # simplified
                    symbol=pred.symbol,
                    action=self._side_to_action(pred.side, pred.confidence),
                    reward=out.reward,
                    next_features=next_features if next_features else None,
                )
                self.policy.record_confidence_outcome(
                    pred.confidence,
                    out.outcome in ("WIN", "PREPARE_WIN"),
                )
                self.risk.update_session_pnl(out.net_return_bps)
        return [o.model_dump() for o in outcomes]

    def status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "interval_seconds": self.interval,
            "symbols": self.universe.all(),
            "policy_epsilon": self.policy.epsilon,
            "policy_hash": self.policy.policy_hash,
            "session_net_bps": self.risk._session_net_bps,
            "last_log": self._last_log,
            "live_trading_enabled": self.risk._live_trading_enabled,
            "truth_labels": {
                "runtime": "real",
                "telemetry": "real",
                "gateio_data": "real if fetched live",
                "prediction_mode": "paper",
                "live_trading": "disabled",
                "model_quality": "experimental",
                "tunnel": "demo-grade unless named production tunnel",
                "receipts": "real only if hashes are generated and stored",
                "devnet_settlement": "real only if transaction signatures are produced",
            },
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _action_to_side(action: str) -> Side:
        if action == "LONG":
            return Side.LONG
        if action == "SHORT":
            return Side.SHORT
        if action == "PREPARE_LONG":
            return Side.PREPARE_LONG
        if action == "PREPARE_SHORT":
            return Side.PREPARE_SHORT
        return Side.LONG

    @staticmethod
    def _side_to_action(side: Side, confidence: float) -> str:
        if side == Side.LONG:
            return "LONG"
        if side == Side.SHORT:
            return "SHORT"
        if side == Side.PREPARE_LONG:
            return "PREPARE_LONG"
        if side == Side.PREPARE_SHORT:
            return "PREPARE_SHORT"
        return "LONG"
