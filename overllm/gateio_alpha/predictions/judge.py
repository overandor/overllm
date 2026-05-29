"""ThreeMinuteOutcomeJudge — scores predictions exactly 180s after creation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from overllm.gateio_alpha.gate.client import GateioFuturesClient
from overllm.gateio_alpha.predictions.models import Outcome, OutcomeRecord, Prediction, Side
from overllm.gateio_alpha.predictions.store import PredictionStore
from overllm.gateio_alpha.receipts.hasher import make_outcome_receipt


class ThreeMinuteOutcomeJudge:
    """Fetches exit price, scores net return, writes outcome, updates learning."""

    def __init__(
        self,
        store: PredictionStore,
        client: GateioFuturesClient | None = None,
        fee_bps: float = 5.0,
        slippage_bps: float = 2.0,
        spread_penalty_bps: float = 1.0,
        stale_data_penalty_bps: float = 5.0,
        overtrade_penalty_bps: float = 0.0,
    ) -> None:
        self.store = store
        self.client = client or GateioFuturesClient()
        self.fee_bps = fee_bps
        self.slippage_bps = slippage_bps
        self.spread_penalty_bps = spread_penalty_bps
        self.stale_data_penalty_bps = stale_data_penalty_bps
        self.overtrade_penalty_bps = overtrade_penalty_bps

    def judge(self, prediction: Prediction, exit_price: float | None = None) -> OutcomeRecord:
        """Judge a single prediction. If exit_price is None, fetch live."""
        if exit_price is None:
            ticker = self.client.get_ticker(prediction.symbol)
            tick = ticker[0] if isinstance(ticker, list) and ticker else ticker
            exit_price = float(tick.get("last", 0.0)) if isinstance(tick, dict) else 0.0

        gross = self._gross_return(prediction.side, prediction.reference_price, exit_price)

        # Penalties
        net = (
            gross
            - self.fee_bps
            - self.slippage_bps
            - self.spread_penalty_bps * (prediction.spread_bps / 10.0)
            - self.stale_data_penalty_bps
            - self.overtrade_penalty_bps
        )

        outcome, reward = self._classify(prediction.side, net, gross)

        record = OutcomeRecord(
            prediction_id=prediction.prediction_id,
            judged_at=datetime.now(timezone.utc),
            exit_reference_price=exit_price,
            gross_return_bps=gross,
            estimated_fee_bps=self.fee_bps,
            estimated_slippage_bps=self.slippage_bps,
            net_return_bps=net,
            outcome=outcome,
            reward=reward,
            model_update_applied=False,
        )

        # Receipt
        receipt = make_outcome_receipt(record.model_dump())
        record.receipt_hash = receipt["hash"]

        self.store.insert_outcome(record)
        self.store.update_status(prediction.prediction_id, "JUDGED")
        return record

    def tick(self) -> list[OutcomeRecord]:
        """Judge all predictions whose 180s horizon has elapsed."""
        pending = self.store.list_pending()
        now = datetime.now(timezone.utc)
        judged: list[OutcomeRecord] = []
        for pred in pending:
            elapsed = (now - pred.created_at).total_seconds()
            if elapsed >= pred.horizon_seconds:
                outcome = self.judge(pred)
                judged.append(outcome)
        return judged

    @staticmethod
    def _gross_return(side: Side, entry: float, exit: float) -> float:
        if entry == 0:
            return 0.0
        if side in (Side.LONG, Side.PREPARE_LONG):
            return ((exit - entry) / entry) * 10000
        if side in (Side.SHORT, Side.PREPARE_SHORT):
            return ((entry - exit) / entry) * 10000
        return 0.0

    def _classify(self, side: Side, net: float, gross: float) -> tuple[Outcome, float]:
        is_prepare = side in (Side.PREPARE_LONG, Side.PREPARE_SHORT)
        if net > 0:
            if is_prepare:
                return (Outcome.PREPARE_WIN, net / 200.0)  # reduced reward for prepare signals
            return (Outcome.WIN, net / 100.0)
        if is_prepare:
            return (Outcome.PREPARE_LOSS, net / 200.0)
        return (Outcome.LOSS, net / 100.0)
