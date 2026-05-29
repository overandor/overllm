"""Risk governor: vetoes predictions before they are emitted."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class RiskGovernor:
    """All vetoes return (allowed: bool, reason: str)."""

    def __init__(
        self,
        max_spread_bps: float = 50.0,
        max_volatility_5m: float = 0.05,
        max_drawdown_bps: float = -200.0,
        min_confidence: float = 0.0,
        stale_data_seconds: float = 180.0,
        cooldown_seconds: float = 10.0,
    ) -> None:
        self.max_spread_bps = max_spread_bps
        self.max_volatility_5m = max_volatility_5m
        self.max_drawdown_bps = max_drawdown_bps
        self.min_confidence = min_confidence
        self.stale_data_seconds = stale_data_seconds
        self.cooldown_seconds = cooldown_seconds
        self._last_prediction_time: dict[str, datetime] = {}
        self._session_net_bps: float = 0.0
        self._live_trading_enabled: bool = False  # HARD DISABLED BY DEFAULT

    # ------------------------------------------------------------------
    # Vetoes
    # ------------------------------------------------------------------
    def check(
        self,
        symbol: str,
        features: dict[str, Any],
        confidence: float,
        current_time: datetime | None = None,
    ) -> tuple[bool, str]:
        now = current_time or datetime.now(timezone.utc)

        # 1. Live trading hard-disabled
        if self._live_trading_enabled:
            return (False, "LIVE_TRADING_HARD_DISABLED")

        # 2. Stale data veto
        data_ts = features.get("timestamp", 0)
        if data_ts:
            # Robust to ms vs s
            if data_ts > 1e12:
                data_ts = data_ts / 1000
            age = now.timestamp() - data_ts
            if age > self.stale_data_seconds:
                return (False, f"STALE_DATA:{age:.0f}s")

        # 3. High spread veto
        spread = features.get("spread_bps", 0.0)
        if spread > self.max_spread_bps:
            return (False, f"HIGH_SPREAD:{spread:.1f}bps")

        # 4. Volatility shock veto
        vol = features.get("volatility_5m", 0.0)
        if vol > self.max_volatility_5m:
            return (False, f"VOLATILITY_SHOCK:{vol:.4f}")

        # 5. Drawdown veto (session-level)
        if self._session_net_bps < self.max_drawdown_bps:
            return (False, f"DRAWDOWN:{self._session_net_bps:.1f}bps")

        # 6. Duplicate / cooldown veto
        last = self._last_prediction_time.get(symbol)
        if last:
            elapsed = (now - last).total_seconds()
            if elapsed < self.cooldown_seconds:
                return (False, f"COOLDOWN:{elapsed:.0f}s")

        # 7. API degradation veto (placeholder — checked upstream)
        # 8. Confidence floor
        if confidence < self.min_confidence:
            return (False, f"LOW_CONFIDENCE:{confidence:.2f}")

        return (True, "PASS")

    def record_prediction(self, symbol: str, time: datetime | None = None) -> None:
        self._last_prediction_time[symbol] = time or datetime.now(timezone.utc)

    def update_session_pnl(self, net_bps: float) -> None:
        self._session_net_bps += net_bps

    def reset_session(self) -> None:
        self._session_net_bps = 0.0
        self._last_prediction_time.clear()
