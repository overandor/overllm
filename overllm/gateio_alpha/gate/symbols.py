"""Symbol universe manager."""
from __future__ import annotations

DEFAULT_SYMBOLS = [
    "BTC_USDT",
    "ETH_USDT",
    "SOL_USDT",
    "DOGE_USDT",
    "PEPE_USDT",
    "WIF_USDT",
]


class SymbolUniverse:
    def __init__(self, symbols: list[str] | None = None) -> None:
        self.symbols = symbols or DEFAULT_SYMBOLS.copy()

    def contract(self, symbol: str) -> str:
        """Map BTC_USDT → BTC_USDT (Gate.io perpetual contract naming)."""
        return symbol

    def all(self) -> list[str]:
        return self.symbols.copy()
