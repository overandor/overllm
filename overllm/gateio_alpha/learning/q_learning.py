"""Online Q-learning policy with confidence calibration."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

import numpy as np

ACTIONS = [
    "LONG",
    "SHORT",
    "PREPARE_LONG",
    "PREPARE_SHORT",
]


def _discretize(value: float, bins: list[float]) -> int:
    for i, b in enumerate(bins):
        if value <= b:
            return i
    return len(bins)


class StateEncoder:
    """Handcrafted state buckets for fast online learning."""

    def __init__(self) -> None:
        self.return_bins = [-0.01, -0.003, 0.003, 0.01]
        self.vol_bins = [0.005, 0.01, 0.02, 0.05]
        self.mom_bins = [-0.5, -0.1, 0.1, 0.5]
        self.spread_bins = [5.0, 15.0, 30.0, 60.0]
        self.regime_map = {
            "low_vol_chop": 0,
            "low_vol_trend": 1,
            "high_vol_chop": 2,
            "high_vol_trend": 3,
        }

    def encode(self, features: dict[str, Any], symbol: str) -> tuple[int, ...]:
        r = _discretize(features.get("return_5m", 0.0), self.return_bins)
        v = _discretize(features.get("volatility_5m", 0.0), self.vol_bins)
        m = _discretize(features.get("momentum_score", 0.0), self.mom_bins)
        s = _discretize(features.get("spread_bps", 0.0), self.spread_bins)
        reg = self.regime_map.get(features.get("regime_label", "low_vol_chop"), 0)
        sym = hash(symbol) % 8  # bucket symbol
        return (r, v, m, s, reg, sym)


class QPolicy:
    """Tabular Q-learning with epsilon-greedy exploration and symbol/regime memory."""

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount: float = 0.95,
        epsilon: float = 0.15,
        epsilon_decay: float = 0.9995,
        epsilon_min: float = 0.05,
        state_encoder: StateEncoder | None = None,
    ) -> None:
        self.lr = learning_rate
        self.gamma = discount
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.encoder = state_encoder or StateEncoder()
        self.q_table: dict[tuple[int, ...], dict[str, float]] = {}
        self.confidence_history: list[tuple[float, bool]] = []  # (confidence, was_win)
        self.visit_counts: dict[tuple[int, ...], int] = {}
        self._policy_hash = self._compute_policy_hash()

    # ------------------------------------------------------------------
    # Action selection
    # ------------------------------------------------------------------
    def select_action(self, features: dict[str, Any], symbol: str) -> tuple[str, float]:
        state = self.encoder.encode(features, symbol)
        if state not in self.q_table:
            self.q_table[state] = {a: 0.0 for a in ACTIONS}
            self.visit_counts[state] = 0

        self.visit_counts[state] += 1

        if random.random() < self.epsilon:
            action = random.choice(ACTIONS)
        else:
            action = max(self.q_table[state], key=self.q_table[state].get)  # type: ignore[arg-type]

        # Confidence calibration
        confidence = self._calibrate_confidence(state, action)
        return action, confidence

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(
        self,
        features: dict[str, Any],
        symbol: str,
        action: str,
        reward: float,
        next_features: dict[str, Any] | None = None,
    ) -> None:
        state = self.encoder.encode(features, symbol)
        q = self.q_table.setdefault(state, {a: 0.0 for a in ACTIONS})

        if next_features:
            next_state = self.encoder.encode(next_features, symbol)
            q_next = self.q_table.setdefault(next_state, {a: 0.0 for a in ACTIONS})
            max_next = max(q_next.values())
        else:
            max_next = 0.0

        td_target = reward + self.gamma * max_next
        td_error = td_target - q[action]
        q[action] += self.lr * td_error

        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
        self._policy_hash = self._compute_policy_hash()

    def record_confidence_outcome(self, confidence: float, win: bool) -> None:
        self.confidence_history.append((confidence, win))
        if len(self.confidence_history) > 5000:
            self.confidence_history = self.confidence_history[-4000:]

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------
    def _calibrate_confidence(self, state: tuple[int, ...], action: str) -> float:
        q = self.q_table.get(state, {})
        if not q:
            return 0.5
        best = max(q.values())
        worst = min(q.values())
        spread = best - worst + 1e-6
        raw = (q[action] - worst) / spread
        # Temperature scaling with visit count
        visits = self.visit_counts.get(state, 1)
        temperature = max(0.5, 2.0 / math.log1p(visits + 1))
        calibrated = 1.0 / (1.0 + math.exp(-raw * temperature))
        return round(float(calibrated), 4)

    def calibration_stats(self) -> dict[str, Any]:
        if not self.confidence_history:
            return {"bins": [], "reliability": 0.0}
        bins = [[] for _ in range(5)]  # 0-0.2, 0.2-0.4, ...
        for conf, win in self.confidence_history:
            idx = min(int(conf * 5), 4)
            bins[idx].append(1 if win else 0)
        reliabilities = []
        for i, b in enumerate(bins):
            if b:
                reliabilities.append({
                    "range": f"{i*0.2:.1f}-{(i+1)*0.2:.1f}",
                    "predicted": (i + 0.5) * 0.2,
                    "actual": sum(b) / len(b),
                    "count": len(b),
                })
        return {
            "bins": reliabilities,
            "reliability": sum(r["actual"] for r in reliabilities) / len(reliabilities) if reliabilities else 0.0,
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        data = {
            "q_table": {str(k): v for k, v in self.q_table.items()},
            "epsilon": self.epsilon,
            "confidence_history": self.confidence_history,
            "visit_counts": {str(k): v for k, v in self.visit_counts.items()},
        }
        Path(path).write_text(json.dumps(data, default=str))

    def load(self, path: str) -> None:
        raw = json.loads(Path(path).read_text())
        self.q_table = {
            tuple(int(x) for x in k.strip("()").split(",") if x.strip()): v
            for k, v in raw.get("q_table", {}).items()
        }
        self.epsilon = raw.get("epsilon", self.epsilon)
        self.confidence_history = raw.get("confidence_history", [])
        self.visit_counts = {
            tuple(int(x) for x in k.strip("()").split(",") if x.strip()): v
            for k, v in raw.get("visit_counts", {}).items()
        }
        self._policy_hash = self._compute_policy_hash()

    def _compute_policy_hash(self) -> str:
        import hashlib
        canonical = json.dumps({k: v for k, v in sorted(self.q_table.items())}, sort_keys=True, default=str)
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    @property
    def policy_hash(self) -> str:
        return self._policy_hash
