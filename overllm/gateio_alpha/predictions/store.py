"""Append-only prediction store backed by SQLite."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from overllm.gateio_alpha.predictions.models import JudgedPrediction, OutcomeRecord, Prediction

SCHEMA = """
CREATE TABLE IF NOT EXISTS predictions (
    prediction_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    created_at TEXT NOT NULL,
    horizon_seconds INTEGER NOT NULL,
    side TEXT NOT NULL,
    confidence REAL NOT NULL,
    reference_price REAL NOT NULL,
    spread_bps REAL NOT NULL,
    features_hash TEXT NOT NULL,
    model_hash TEXT NOT NULL,
    policy_hash TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    receipt_hash TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
    prediction_id TEXT PRIMARY KEY,
    judged_at TEXT NOT NULL,
    exit_reference_price REAL NOT NULL,
    gross_return_bps REAL NOT NULL,
    estimated_fee_bps REAL NOT NULL,
    estimated_slippage_bps REAL NOT NULL,
    net_return_bps REAL NOT NULL,
    outcome TEXT NOT NULL,
    reward REAL NOT NULL,
    model_update_applied INTEGER NOT NULL,
    receipt_hash TEXT
);

CREATE INDEX IF NOT EXISTS idx_pred_symbol ON predictions(symbol);
CREATE INDEX IF NOT EXISTS idx_pred_status ON predictions(status);
CREATE INDEX IF NOT EXISTS idx_pred_created ON predictions(created_at);
"""


class PredictionStore:
    """Thread-safe, append-only store. No deletions."""

    def __init__(self, db_path: str | None = None) -> None:
        if db_path is None:
            db_path = str(Path.home() / ".overllm" / "alpha_predictions.db")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA)

    # ------------------------------------------------------------------
    # Predictions
    # ------------------------------------------------------------------
    def insert_prediction(self, pred: Prediction) -> None:
        conn = self._conn()
        conn.execute(
            """
            INSERT INTO predictions VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                pred.prediction_id,
                pred.symbol,
                pred.created_at.isoformat(),
                pred.horizon_seconds,
                pred.side.value,
                pred.confidence,
                pred.reference_price,
                pred.spread_bps,
                pred.features_hash,
                pred.model_hash,
                pred.policy_hash,
                pred.reason,
                pred.status,
                pred.receipt_hash,
            ),
        )
        conn.commit()

    def get_prediction(self, prediction_id: str) -> Prediction | None:
        row = self._conn().execute(
            "SELECT * FROM predictions WHERE prediction_id = ?", (prediction_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_prediction(row)

    def list_pending(self, symbol: str | None = None) -> list[Prediction]:
        sql = "SELECT * FROM predictions WHERE status = 'PENDING_OUTCOME'"
        params: tuple[Any, ...] = ()
        if symbol:
            sql += " AND symbol = ?"
            params = (symbol,)
        sql += " ORDER BY created_at ASC"
        rows = self._conn().execute(sql, params).fetchall()
        return [self._row_to_prediction(r) for r in rows]

    def list_history(
        self, symbol: str | None = None, limit: int = 500
    ) -> list[Prediction]:
        sql = "SELECT * FROM predictions"
        params: tuple[Any, ...] = ()
        if symbol:
            sql += " WHERE symbol = ?"
            params = (symbol,)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params = (*params, limit)
        rows = self._conn().execute(sql, params).fetchall()
        return [self._row_to_prediction(r) for r in rows]

    def update_status(self, prediction_id: str, status: str) -> None:
        self._conn().execute(
            "UPDATE predictions SET status = ? WHERE prediction_id = ?",
            (status, prediction_id),
        )
        self._conn().commit()

    # ------------------------------------------------------------------
    # Outcomes
    # ------------------------------------------------------------------
    def insert_outcome(self, out: OutcomeRecord) -> None:
        self._conn().execute(
            """
            INSERT INTO outcomes VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                out.prediction_id,
                out.judged_at.isoformat(),
                out.exit_reference_price,
                out.gross_return_bps,
                out.estimated_fee_bps,
                out.estimated_slippage_bps,
                out.net_return_bps,
                out.outcome.value,
                out.reward,
                int(out.model_update_applied),
                out.receipt_hash,
            ),
        )
        self._conn().commit()

    def get_judged(self, prediction_id: str) -> JudgedPrediction | None:
        pred = self.get_prediction(prediction_id)
        if not pred:
            return None
        row = self._conn().execute(
            "SELECT * FROM outcomes WHERE prediction_id = ?", (prediction_id,)
        ).fetchone()
        if not row:
            return None
        return JudgedPrediction(
            prediction=pred,
            outcome=self._row_to_outcome(row),
        )

    def list_judged(
        self, symbol: str | None = None, limit: int = 500
    ) -> list[JudgedPrediction]:
        sql = """
            SELECT p.*, o.* FROM predictions p
            JOIN outcomes o ON p.prediction_id = o.prediction_id
        """
        params: tuple[Any, ...] = ()
        if symbol:
            sql += " WHERE p.symbol = ?"
            params = (symbol,)
        sql += " ORDER BY p.created_at DESC LIMIT ?"
        params = (*params, limit)
        rows = self._conn().execute(sql, params).fetchall()
        return [
            JudgedPrediction(
                prediction=self._row_to_prediction(r),
                outcome=self._row_to_outcome(r),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def performance_stats(self, symbol: str | None = None) -> dict[str, Any]:
        sql = """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN outcome IN ('WIN','PREPARE_WIN') THEN 1 ELSE 0 END) as wins,
                SUM(net_return_bps) as total_net_bps,
                AVG(net_return_bps) as avg_net_bps,
                AVG(reward) as avg_reward
            FROM outcomes
        """
        params: tuple[Any, ...] = ()
        if symbol:
            sql += " WHERE prediction_id IN (SELECT prediction_id FROM predictions WHERE symbol = ?)"
            params = (symbol,)
        row = self._conn().execute(sql, params).fetchone()
        total = row["total"] or 0
        wins = row["wins"] or 0
        return {
            "total": total,
            "wins": wins,
            "losses": total - wins,
            "accuracy": wins / total if total else 0.0,
            "total_net_bps": row["total_net_bps"] or 0.0,
            "avg_net_bps": row["avg_net_bps"] or 0.0,
            "avg_reward": row["avg_reward"] or 0.0,
        }

    def accuracy_by_symbol(self) -> dict[str, dict[str, Any]]:
        rows = self._conn().execute(
            """
            SELECT
                p.symbol,
                COUNT(*) as total,
                SUM(CASE WHEN o.outcome IN ('WIN','PREPARE_WIN') THEN 1 ELSE 0 END) as wins,
                AVG(o.net_return_bps) as avg_net_bps
            FROM predictions p
            JOIN outcomes o ON p.prediction_id = o.prediction_id
            GROUP BY p.symbol
            """
        ).fetchall()
        return {
            r["symbol"]: {
                "total": r["total"],
                "wins": r["wins"],
                "accuracy": (r["wins"] / r["total"]) if r["total"] else 0.0,
                "avg_net_bps": r["avg_net_bps"] or 0.0,
            }
            for r in rows
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _row_to_prediction(row: sqlite3.Row) -> Prediction:
        from overllm.gateio_alpha.predictions.models import Side

        return Prediction(
            prediction_id=row["prediction_id"],
            symbol=row["symbol"],
            created_at=datetime.fromisoformat(row["created_at"]),
            horizon_seconds=row["horizon_seconds"],
            side=Side(row["side"]),
            confidence=row["confidence"],
            reference_price=row["reference_price"],
            spread_bps=row["spread_bps"],
            features_hash=row["features_hash"],
            model_hash=row["model_hash"],
            policy_hash=row["policy_hash"],
            reason=row["reason"],
            status=row["status"],
            receipt_hash=row["receipt_hash"],
        )

    @staticmethod
    def _row_to_outcome(row: sqlite3.Row) -> OutcomeRecord:
        from overllm.gateio_alpha.predictions.models import Outcome

        return OutcomeRecord(
            prediction_id=row["prediction_id"],
            judged_at=datetime.fromisoformat(row["judged_at"]),
            exit_reference_price=row["exit_reference_price"],
            gross_return_bps=row["gross_return_bps"],
            estimated_fee_bps=row["estimated_fee_bps"],
            estimated_slippage_bps=row["estimated_slippage_bps"],
            net_return_bps=row["net_return_bps"],
            outcome=Outcome(row["outcome"]),
            reward=row["reward"],
            model_update_applied=bool(row["model_update_applied"]),
            receipt_hash=row["receipt_hash"],
        )
