"""Gate.io public futures REST client."""
from __future__ import annotations

import time
from typing import Any

import httpx

GATEIO_FUTURES_BASE = "https://api.gateio.ws/api/v4"


class GateioFuturesClient:
    """Public futures REST client (no auth required for market data)."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout
        self._last_call = 0.0
        self._rate_limit_interval = 0.05  # 20 r/s conservative

    def _throttle(self) -> None:
        now = time.time()
        elapsed = now - self._last_call
        if elapsed < self._rate_limit_interval:
            time.sleep(self._rate_limit_interval - elapsed)
        self._last_call = time.time()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._throttle()
        url = f"{GATEIO_FUTURES_BASE}{path}"
        resp = httpx.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Contracts / Tickers
    # ------------------------------------------------------------------
    def list_contracts(self, settle: str = "usdt") -> list[dict]:
        return self._get(f"/futures/{settle}/contracts")

    def get_ticker(self, contract: str, settle: str = "usdt") -> dict:
        return self._get(f"/futures/{settle}/tickers", params={"contract": contract})

    def list_tickers(self, settle: str = "usdt") -> list[dict]:
        return self._get(f"/futures/{settle}/tickers")

    # ------------------------------------------------------------------
    # Candles
    # ------------------------------------------------------------------
    def get_candlesticks(
        self,
        contract: str,
        interval: str = "1m",
        limit: int = 100,
        settle: str = "usdt",
    ) -> list[dict]:
        """Return Gate.io futures candlestick list [{t, o, h, l, c, v, sum}]."""
        return self._get(
            f"/futures/{settle}/candlesticks",
            params={"contract": contract, "interval": interval, "limit": limit},
        )

    # ------------------------------------------------------------------
    # Order Book
    # ------------------------------------------------------------------
    def get_order_book(
        self, contract: str, limit: int = 20, settle: str = "usdt"
    ) -> dict:
        return self._get(
            f"/futures/{settle}/order_book",
            params={"contract": contract, "limit": limit},
        )

    # ------------------------------------------------------------------
    # Trades
    # ------------------------------------------------------------------
    def get_trades(
        self, contract: str, limit: int = 100, settle: str = "usdt"
    ) -> list[dict]:
        return self._get(
            f"/futures/{settle}/trades",
            params={"contract": contract, "limit": limit},
        )

    # ------------------------------------------------------------------
    # Funding Rate
    # ------------------------------------------------------------------
    def get_funding_rate(self, contract: str, settle: str = "usdt") -> list[dict]:
        return self._get(
            f"/futures/{settle}/funding_rate",
            params={"contract": contract, "limit": 1},
        )
