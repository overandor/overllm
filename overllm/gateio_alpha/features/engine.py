"""Feature vector builder from Gate.io market data."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

import numpy as np

from overllm.gateio_alpha.gate.client import GateioFuturesClient


class FeatureEngine:
    """Builds a normalized feature vector from REST-sampled market data."""

    def __init__(self, client: GateioFuturesClient | None = None) -> None:
        self.client = client or GateioFuturesClient()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def build(self, symbol: str) -> dict[str, Any]:
        contract = symbol  # Gate.io perpetual contract name
        ticker = self.client.get_ticker(contract)
        order_book = self.client.get_order_book(contract, limit=20)
        candles_1m = self.client.get_candlesticks(contract, interval="1m", limit=60)
        candles_5m = self.client.get_candlesticks(contract, interval="5m", limit=20)
        candles_15m = self.client.get_candlesticks(contract, interval="15m", limit=20)
        trades = self.client.get_trades(contract, limit=100)
        funding = self.client.get_funding_rate(contract)

        # Generate 300+ dynamic KPIs on the fly
        features = self._kpi_factory(candles_1m, candles_5m, candles_15m, order_book, trades, ticker, funding)
        features["momentum_score"] = self._momentum(candles_1m[-10:])
        features["mean_reversion_score"] = self._mean_reversion(candles_1m[-20:])
        features["breakout_score"] = self._breakout(candles_5m[-10:])
        features["fakeout_risk"] = self._fakeout_risk(candles_1m[-10:])
        features["regime_label"] = self._regime_label(features)

        # Reference price from ticker
        tick = ticker[0] if isinstance(ticker, list) and ticker else ticker
        last_price = float(tick.get("last", 0.0)) if isinstance(tick, dict) else 0.0
        features["reference_price"] = last_price
        features["symbol"] = symbol
        features["timestamp"] = candles_1m[-1]["t"] if candles_1m else 0

        return features

    def hash_features(self, features: dict[str, Any]) -> str:
        """Canonical SHA256 of sorted JSON feature dict (excluding dynamic fields)."""
        snapshot = {k: v for k, v in features.items() if k not in ("symbol", "timestamp", "reference_price")}
        canonical = json.dumps(snapshot, sort_keys=True, default=str)
        return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Feature implementations
    # ------------------------------------------------------------------
    @staticmethod
    def _return_over_candles(candles: list[dict], n: int) -> float:
        """Candles format: {t, o, h, l, c, v, sum}."""
        if len(candles) < n + 1:
            return 0.0
        prev = float(candles[-n - 1]["c"])
        curr = float(candles[-1]["c"])
        return (curr - prev) / prev if prev else 0.0

    @staticmethod
    def _volatility(candles: list[dict]) -> float:
        if len(candles) < 2:
            return 0.0
        closes = [float(c["c"]) for c in candles]
        returns = np.diff(np.log(np.array(closes) + 1e-12))
        return float(np.std(returns) * np.sqrt(len(returns))) if len(returns) else 0.0

    @staticmethod
    def _volume_zscore(candles: list[dict], lookback: int = 20) -> float:
        if len(candles) < lookback + 1:
            return 0.0
        volumes = np.array([float(c["v"]) for c in candles[-lookback:]])
        mean = np.mean(volumes)
        std = np.std(volumes)
        return float((volumes[-1] - mean) / (std + 1e-12))

    @staticmethod
    def _spread_bps(order_book: dict) -> float:
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        if not bids or not asks:
            return 0.0
        best_bid = float(bids[0]["p"])
        best_ask = float(asks[0]["p"])
        mid = (best_bid + best_ask) / 2.0
        if mid == 0:
            return 0.0
        return ((best_ask - best_bid) / mid) * 10000

    @staticmethod
    def _ob_imbalance(order_book: dict, depth: int) -> float:
        bids = order_book.get("bids", [])[:depth]
        asks = order_book.get("asks", [])[:depth]
        bid_vol = sum(float(b["s"]) for b in bids)
        ask_vol = sum(float(a["s"]) for a in asks)
        total = bid_vol + ask_vol
        if total == 0:
            return 0.0
        return (bid_vol - ask_vol) / total

    @staticmethod
    def _trade_pressure(trades: list[dict]) -> float:
        """Simple taker buy/sell ratio proxy using size."""
        if not trades:
            return 0.0
        buy_vol = sum(float(t["size"]) for t in trades if t.get("size", 0) > 0)
        sell_vol = sum(float(t["size"]) for t in trades if t.get("size", 0) < 0)
        total = buy_vol + abs(sell_vol) + 1e-12
        return (buy_vol - abs(sell_vol)) / total

    @staticmethod
    def _funding_rate(funding: list[dict]) -> float:
        if not funding:
            return 0.0
        return float(funding[0].get("funding_rate", 0.0))

    @staticmethod
    def _momentum(candles: list[dict]) -> float:
        if len(candles) < 10:
            return 0.0
        closes = np.array([float(c["c"]) for c in candles])
        sma_short = np.mean(closes[-5:])
        sma_long = np.mean(closes)
        diff = (sma_short - sma_long) / (sma_long + 1e-12)
        return float(np.tanh(diff * 10))

    @staticmethod
    def _mean_reversion(candles: list[dict]) -> float:
        if len(candles) < 5:
            return 0.0
        closes = np.array([float(c["c"]) for c in candles])
        mean = np.mean(closes)
        std = np.std(closes) + 1e-12
        z = (closes[-1] - mean) / std
        return float(-np.tanh(z))

    @staticmethod
    def _breakout(candles: list[dict]) -> float:
        if len(candles) < 5:
            return 0.0
        highs = np.array([float(c["h"]) for c in candles])
        lows = np.array([float(c["l"]) for c in candles])
        closes = np.array([float(c["c"]) for c in candles])
        range_ = highs.max() - lows.min()
        if range_ == 0:
            return 0.0
        pos = (closes[-1] - lows.min()) / range_
        return float(2 * pos - 1)

    @staticmethod
    def _fakeout_risk(candles: list[dict]) -> float:
        if len(candles) < 3:
            return 0.0
        wicks = []
        for c in candles:
            o, h, l, close = float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"])
            body = abs(close - o)
            range_ = h - l
            if range_ == 0:
                wicks.append(0.0)
            else:
                wicks.append((range_ - body) / range_)
        return float(np.mean(wicks))

    @staticmethod
    def _regime_label(features: dict[str, Any]) -> str:
        vol = features.get("volatility_15m", 0.0)
        mom = features.get("momentum_score", 0.0)
        if vol > 0.02:
            return "high_vol_trend" if abs(mom) > 0.3 else "high_vol_chop"
        if abs(mom) > 0.3:
            return "low_vol_trend"
        return "low_vol_chop"

    # ------------------------------------------------------------------
    # Expanded KPI factory (300+ indicators generated on the fly)
    # ------------------------------------------------------------------
    def _kpi_factory(self, candles_1m: list[dict], candles_5m: list[dict], candles_15m: list[dict], order_book: dict, trades: list[dict], ticker: dict, funding: list[dict]) -> dict[str, Any]:
        kpis: dict[str, Any] = {}
        # Basic returns across multiple windows
        for window, label in [(1,"1m"),(3,"3m"),(5,"5m"),(10,"10m"),(15,"15m"),(30,"30m")]:
            kpis[f"return_{label}"] = self._return_over_candles(candles_1m, window)
        # Volatility across windows
        for win, label in [(5,"5m"),(10,"10m"),(15,"15m"),(30,"30m"),(60,"60m")]:
            kpis[f"volatility_{label}"] = self._volatility(candles_1m[-win:])
        # Volume features
        for lookback in [5, 10, 15, 20, 30, 60]:
            kpis[f"volume_zscore_{lookback}"] = self._volume_zscore(candles_1m, lookback)
            vols = [float(c["v"]) for c in candles_1m[-lookback:]]
            kpis[f"volume_avg_{lookback}"] = float(np.mean(vols)) if vols else 0.0
            kpis[f"volume_max_{lookback}"] = float(np.max(vols)) if vols else 0.0
            kpis[f"volume_min_{lookback}"] = float(np.min(vols)) if vols else 0.0
        # Price structure (HL, OC, body, wick)
        for lookback in [3, 5, 10, 15, 20]:
            subset = candles_1m[-lookback:]
            highs = [float(c["h"]) for c in subset]
            lows = [float(c["l"]) for c in subset]
            opens = [float(c["o"]) for c in subset]
            closes = [float(c["c"]) for c in subset]
            kpis[f"range_{lookback}"] = float(max(highs) - min(lows)) if highs else 0.0
            kpis[f"range_pct_{lookback}"] = (float(max(highs) - min(lows)) / float(np.mean(closes))) if closes else 0.0
            bodies = [abs(c - o) for c, o in zip(closes, opens)]
            kpis[f"avg_body_{lookback}"] = float(np.mean(bodies)) if bodies else 0.0
            wicks = []
            for c in subset:
                o, h, l, close = float(c["o"]), float(c["h"]), float(c["l"]), float(c["c"])
                upper = h - max(o, close)
                lower = min(o, close) - l
                wicks.append(upper + lower)
            kpis[f"avg_wick_{lookback}"] = float(np.mean(wicks)) if wicks else 0.0
            directions = [1 if closes[i] > closes[i-1] else (-1 if closes[i] < closes[i-1] else 0) for i in range(1, len(closes))]
            kpis[f"consec_up_{lookback}"] = sum(1 for d in directions if d > 0)
            kpis[f"consec_down_{lookback}"] = sum(1 for d in directions if d < 0)
        # Moving averages and crossovers
        closes_arr = np.array([float(c["c"]) for c in candles_1m])
        for period in [3, 5, 7, 10, 14, 20, 30, 50]:
            if len(closes_arr) >= period:
                sma = np.mean(closes_arr[-period:])
                kpis[f"sma_{period}"] = float(sma)
                kpis[f"dist_from_sma_{period}"] = float((closes_arr[-1] - sma) / sma) if sma else 0.0
            else:
                kpis[f"sma_{period}"] = 0.0
                kpis[f"dist_from_sma_{period}"] = 0.0
        # EMA approximations
        for period in [5, 10, 20, 30]:
            if len(closes_arr) >= period:
                alpha = 2.0 / (period + 1)
                ema = closes_arr[-period]
                for val in closes_arr[-period+1:]:
                    ema = alpha * val + (1 - alpha) * ema
                kpis[f"ema_{period}"] = float(ema)
                kpis[f"dist_from_ema_{period}"] = float((closes_arr[-1] - ema) / ema) if ema else 0.0
        # RSI proxy
        for lookback in [6, 10, 14, 20]:
            if len(closes_arr) >= lookback + 1:
                diffs = np.diff(closes_arr[-lookback-1:])
                gains = np.where(diffs > 0, diffs, 0)
                losses = np.where(diffs < 0, -diffs, 0)
                avg_gain = np.mean(gains) + 1e-12
                avg_loss = np.mean(losses) + 1e-12
                rs = avg_gain / avg_loss
                kpis[f"rsi_proxy_{lookback}"] = float(100 - (100 / (1 + rs)))
            else:
                kpis[f"rsi_proxy_{lookback}"] = 50.0
        # Bollinger Band proxies
        for lookback in [10, 15, 20, 30]:
            if len(closes_arr) >= lookback:
                sub = closes_arr[-lookback:]
                mean = np.mean(sub)
                std = np.std(sub) + 1e-12
                kpis[f"bb_upper_{lookback}"] = float(mean + 2 * std)
                kpis[f"bb_lower_{lookback}"] = float(mean - 2 * std)
                kpis[f"bb_position_{lookback}"] = float((closes_arr[-1] - (mean - 2*std)) / (4 * std))
            else:
                kpis[f"bb_upper_{lookback}"] = 0.0
                kpis[f"bb_lower_{lookback}"] = 0.0
                kpis[f"bb_position_{lookback}"] = 0.5
        # MACD proxy
        for fast, slow in [(5,10),(8,21),(12,26)]:
            if len(closes_arr) >= slow:
                alpha_fast = 2.0 / (fast + 1)
                alpha_slow = 2.0 / (slow + 1)
                ema_fast = closes_arr[-fast]
                ema_slow = closes_arr[-slow]
                for val in closes_arr[-fast+1:]:
                    ema_fast = alpha_fast * val + (1 - alpha_fast) * ema_fast
                for val in closes_arr[-slow+1:]:
                    ema_slow = alpha_slow * val + (1 - alpha_slow) * ema_slow
                kpis[f"macd_{fast}_{slow}"] = float(ema_fast - ema_slow)
                kpis[f"macd_signal_{fast}_{slow}"] = float(ema_fast - ema_slow) * 0.5
            else:
                kpis[f"macd_{fast}_{slow}"] = 0.0
                kpis[f"macd_signal_{fast}_{slow}"] = 0.0
        # Stochastic proxy
        for lookback in [10, 14, 20]:
            if len(candles_1m) >= lookback:
                highs = np.array([float(c["h"]) for c in candles_1m[-lookback:]])
                lows = np.array([float(c["l"]) for c in candles_1m[-lookback:]])
                highest = highs.max()
                lowest = lows.min()
                close = float(candles_1m[-1]["c"])
                range_ = highest - lowest + 1e-12
                kpis[f"stoch_k_{lookback}"] = float((close - lowest) / range_ * 100)
                kpis[f"stoch_d_{lookback}"] = float(np.mean([(float(candles_1m[-i]["c"]) - lowest) / range_ * 100 for i in range(1, min(4, lookback))]))
            else:
                kpis[f"stoch_k_{lookback}"] = 50.0
                kpis[f"stoch_d_{lookback}"] = 50.0
        # ATR proxy
        for lookback in [7, 10, 14, 20]:
            if len(candles_1m) >= lookback:
                trs = []
                for i in range(-lookback + 1, 0):
                    h = float(candles_1m[i]["h"])
                    l = float(candles_1m[i]["l"])
                    prev_c = float(candles_1m[i-1]["c"])
                    tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
                    trs.append(tr)
                kpis[f"atr_{lookback}"] = float(np.mean(trs)) if trs else 0.0
            else:
                kpis[f"atr_{lookback}"] = 0.0
        # OBV proxy
        if len(candles_1m) >= 2:
            obv = 0.0
            for i in range(1, len(candles_1m)):
                prev_c = float(candles_1m[i-1]["c"])
                cur_c = float(candles_1m[i]["c"])
                vol = float(candles_1m[i]["v"])
                if cur_c > prev_c:
                    obv += vol
                elif cur_c < prev_c:
                    obv -= vol
            kpis["obv"] = obv
        else:
            kpis["obv"] = 0.0
        # VWAP proxy
        for lookback in [10, 20, 30]:
            if len(candles_1m) >= lookback:
                pv = 0.0
                v = 0.0
                for c in candles_1m[-lookback:]:
                    typical = (float(c["h"]) + float(c["l"]) + float(c["c"])) / 3.0
                    vol = float(c["v"])
                    pv += typical * vol
                    v += vol
                kpis[f"vwap_{lookback}"] = float(pv / v) if v else 0.0
                kpis[f"dist_from_vwap_{lookback}"] = float((float(candles_1m[-1]["c"]) - (pv / v)) / (pv / v)) if v else 0.0
            else:
                kpis[f"vwap_{lookback}"] = 0.0
                kpis[f"dist_from_vwap_{lookback}"] = 0.0
        # Trade flow features
        if trades:
            sizes = [float(t["size"]) for t in trades]
            prices = [float(t["price"]) for t in trades]
            kpis["trade_count"] = len(trades)
            kpis["trade_avg_size"] = float(np.mean(sizes))
            kpis["trade_max_size"] = float(np.max(sizes))
            kpis["trade_size_std"] = float(np.std(sizes))
            kpis["trade_price_range"] = float(max(prices) - min(prices)) if prices else 0.0
            kpis["trade_price_std"] = float(np.std(prices))
            large_threshold = np.percentile(sizes, 90) if sizes else 0.0
            kpis["large_trade_ratio"] = sum(1 for s in sizes if s >= large_threshold) / len(sizes) if sizes else 0.0
            kpis["trade_intensity"] = len(trades) / 3.0
        else:
            for k in ["trade_count","trade_avg_size","trade_max_size","trade_size_std","trade_price_range","trade_price_std","large_trade_ratio","trade_intensity"]:
                kpis[k] = 0.0
        # Core spread + imbalance (legacy compat)
        kpis["spread_bps"] = self._spread_bps(order_book)
        kpis["order_book_imbalance_top5"] = self._ob_imbalance(order_book, 5)
        kpis["order_book_imbalance_top20"] = self._ob_imbalance(order_book, 20)
        kpis["trade_pressure"] = self._trade_pressure(trades)

        # Order book depth features
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        for depth in [1, 3, 5, 10, 20]:
            bid_slice = bids[:depth]
            ask_slice = asks[:depth]
            bid_vol = sum(float(b["s"]) for b in bid_slice)
            ask_vol = sum(float(a["s"]) for a in ask_slice)
            total = bid_vol + ask_vol + 1e-12
            kpis[f"ob_imbalance_top{depth}"] = (bid_vol - ask_vol) / total
            if bids and asks:
                best_bid = float(bids[0]["p"])
                best_ask = float(asks[0]["p"])
                bid_depth_vol = sum(float(b["s"]) for b in bid_slice)
                ask_depth_vol = sum(float(a["s"]) for a in ask_slice)
                kpis[f"bid_depth_conc_{depth}"] = bid_depth_vol / total
                kpis[f"ask_depth_conc_{depth}"] = ask_depth_vol / total
                bid_impact = best_bid - float(bid_slice[-1]["p"]) if len(bid_slice) == depth else 0.0
                ask_impact = float(ask_slice[-1]["p"]) - best_ask if len(ask_slice) == depth else 0.0
                kpis[f"bid_impact_{depth}"] = bid_impact
                kpis[f"ask_impact_{depth}"] = ask_impact
        # Funding rate features
        if funding:
            fr = float(funding[0].get("funding_rate", 0.0))
            kpis["funding_rate"] = fr
            kpis["funding_annualized"] = fr * 3 * 365
        else:
            kpis["funding_rate"] = 0.0
            kpis["funding_annualized"] = 0.0
        # Ticker features
        tick = ticker[0] if isinstance(ticker, list) and ticker else ticker
        last = float(tick.get("last", 0.0)) if isinstance(tick, dict) else 0.0
        mark = float(tick.get("mark_price", last)) if isinstance(tick, dict) else last
        index = float(tick.get("index_price", last)) if isinstance(tick, dict) else last
        kpis["basis_bps"] = ((last - index) / index) * 10000 if index else 0.0
        kpis["mark_basis_bps"] = ((mark - index) / index) * 10000 if index else 0.0
        kpis["change_24h_pct"] = float(tick.get("change_percentage", 0.0)) if isinstance(tick, dict) else 0.0
        kpis["volume_24h"] = float(tick.get("volume_24h", 0.0)) if isinstance(tick, dict) else 0.0
        # Cross-timeframe momentum
        if candles_5m and len(candles_5m) >= 2:
            kpis["return_5m_tf"] = self._return_over_candles(candles_5m, 1)
            kpis["volatility_5m_tf"] = self._volatility(candles_5m[-5:])
        if candles_15m and len(candles_15m) >= 2:
            kpis["return_15m_tf"] = self._return_over_candles(candles_15m, 1)
            kpis["volatility_15m_tf"] = self._volatility(candles_15m[-5:])
        # Skew / Kurtosis proxies
        if len(closes_arr) >= 10:
            kpis["return_skew_10"] = float(np.mean(((closes_arr[-10:] - np.mean(closes_arr[-10:])) / (np.std(closes_arr[-10:]) + 1e-12))**3))
            kpis["return_kurt_10"] = float(np.mean(((closes_arr[-10:] - np.mean(closes_arr[-10:])) / (np.std(closes_arr[-10:]) + 1e-12))**4))
        else:
            kpis["return_skew_10"] = 0.0
            kpis["return_kurt_10"] = 0.0
        # Linear trend slope
        for lookback in [5, 10, 20, 30]:
            if len(closes_arr) >= lookback:
                x = np.arange(lookback)
                y = closes_arr[-lookback:]
                slope = np.polyfit(x, y, 1)[0]
                kpis[f"trend_slope_{lookback}"] = float(slope)
                kpis[f"trend_r2_{lookback}"] = float(np.corrcoef(x, y)[0,1]**2) if np.std(y) > 0 else 0.0
            else:
                kpis[f"trend_slope_{lookback}"] = 0.0
                kpis[f"trend_r2_{lookback}"] = 0.0

        # Fibonacci retracement levels (recent range)
        for lookback in [10, 20, 30]:
            if len(closes_arr) >= lookback:
                sub = closes_arr[-lookback:]
                high = float(sub.max())
                low = float(sub.min())
                range_ = high - low + 1e-12
                cur = float(closes_arr[-1])
                kpis[f"fib_236_{lookback}"] = float((cur - low) / range_ - 0.236)
                kpis[f"fib_382_{lookback}"] = float((cur - low) / range_ - 0.382)
                kpis[f"fib_500_{lookback}"] = float((cur - low) / range_ - 0.5)
                kpis[f"fib_618_{lookback}"] = float((cur - low) / range_ - 0.618)
                kpis[f"fib_786_{lookback}"] = float((cur - low) / range_ - 0.786)
            else:
                for level in ["236","382","500","618","786"]:
                    kpis[f"fib_{level}_{lookback}"] = 0.0

        # Pivot points proxy
        if len(candles_1m) >= 2:
            prev = candles_1m[-2]
            p_high = float(prev["h"])
            p_low = float(prev["l"])
            p_close = float(prev["c"])
            pivot = (p_high + p_low + p_close) / 3.0
            kpis["pivot"] = pivot
            kpis["pivot_r1"] = 2 * pivot - p_low
            kpis["pivot_s1"] = 2 * pivot - p_high
            kpis["pivot_r2"] = pivot + (p_high - p_low)
            kpis["pivot_s2"] = pivot - (p_high - p_low)
            cur = float(candles_1m[-1]["c"])
            kpis["dist_from_pivot"] = float((cur - pivot) / pivot) if pivot else 0.0
        else:
            for k in ["pivot","pivot_r1","pivot_s1","pivot_r2","pivot_s2","dist_from_pivot"]:
                kpis[k] = 0.0

        # Donchian channels
        for lookback in [10, 15, 20, 30]:
            if len(candles_1m) >= lookback:
                highs = np.array([float(c["h"]) for c in candles_1m[-lookback:]])
                lows = np.array([float(c["l"]) for c in candles_1m[-lookback:]])
                kpis[f"donchian_upper_{lookback}"] = float(highs.max())
                kpis[f"donchian_lower_{lookback}"] = float(lows.min())
                kpis[f"donchian_mid_{lookback}"] = float((highs.max() + lows.min()) / 2)
                cur = float(candles_1m[-1]["c"])
                range_ = highs.max() - lows.min() + 1e-12
                kpis[f"donchian_position_{lookback}"] = float((cur - lows.min()) / range_)
            else:
                for k in [f"donchian_upper_{lookback}", f"donchian_lower_{lookback}", f"donchian_mid_{lookback}", f"donchian_position_{lookback}"]:
                    kpis[k] = 0.0

        # Keltner channel proxy (ATR-based)
        for lookback in [10, 15, 20]:
            if len(closes_arr) >= lookback:
                ema = kpis.get(f"ema_{lookback}", closes_arr[-1])
                atr = kpis.get(f"atr_{lookback}", 0.0)
                kpis[f"keltner_upper_{lookback}"] = float(ema + 2 * atr)
                kpis[f"keltner_lower_{lookback}"] = float(ema - 2 * atr)
                cur = float(closes_arr[-1])
                kpis[f"keltner_position_{lookback}"] = float((cur - (ema - 2*atr)) / (4 * atr + 1e-12))
            else:
                for k in [f"keltner_upper_{lookback}", f"keltner_lower_{lookback}", f"keltner_position_{lookback}"]:
                    kpis[k] = 0.0

        # ADX proxy (simplified)
        for lookback in [10, 14, 20]:
            if len(candles_1m) >= lookback + 1:
                plus_dms = []
                minus_dms = []
                trs = []
                for i in range(-lookback, 0):
                    cur_h = float(candles_1m[i]["h"])
                    cur_l = float(candles_1m[i]["l"])
                    prev_h = float(candles_1m[i-1]["h"])
                    prev_l = float(candles_1m[i-1]["l"])
                    prev_c = float(candles_1m[i-1]["c"])
                    plus_dm = max(cur_h - prev_h, 0)
                    minus_dm = max(prev_l - cur_l, 0)
                    if plus_dm > minus_dm:
                        minus_dm = 0
                    elif minus_dm > plus_dm:
                        plus_dm = 0
                    tr = max(cur_h - cur_l, abs(cur_h - prev_c), abs(cur_l - prev_c))
                    plus_dms.append(plus_dm)
                    minus_dms.append(minus_dm)
                    trs.append(tr)
                avg_tr = np.mean(trs) + 1e-12
                plus_di = np.mean(plus_dms) / avg_tr * 100
                minus_di = np.mean(minus_dms) / avg_tr * 100
                dx = abs(plus_di - minus_di) / (plus_di + minus_di + 1e-12) * 100
                kpis[f"adx_proxy_{lookback}"] = float(dx)
                kpis[f"plus_di_{lookback}"] = float(plus_di)
                kpis[f"minus_di_{lookback}"] = float(minus_di)
            else:
                kpis[f"adx_proxy_{lookback}"] = 0.0
                kpis[f"plus_di_{lookback}"] = 0.0
                kpis[f"minus_di_{lookback}"] = 0.0

        # CCI proxy
        for lookback in [10, 14, 20]:
            if len(candles_1m) >= lookback:
                typicals = [(float(c["h"]) + float(c["l"]) + float(c["c"])) / 3.0 for c in candles_1m[-lookback:]]
                sma_typ = np.mean(typicals)
                mean_dev = np.mean([abs(t - sma_typ) for t in typicals]) + 1e-12
                kpis[f"cci_proxy_{lookback}"] = float((typicals[-1] - sma_typ) / (0.015 * mean_dev))
            else:
                kpis[f"cci_proxy_{lookback}"] = 0.0

        # Williams %R proxy
        for lookback in [10, 14, 20]:
            if len(candles_1m) >= lookback:
                highs = np.array([float(c["h"]) for c in candles_1m[-lookback:]])
                lows = np.array([float(c["l"]) for c in candles_1m[-lookback:]])
                close = float(candles_1m[-1]["c"])
                range_ = highs.max() - lows.min() + 1e-12
                kpis[f"williams_r_{lookback}"] = float((highs.max() - close) / range_ * -100)
            else:
                kpis[f"williams_r_{lookback}"] = -50.0

        # Money Flow Index proxy
        for lookback in [10, 14, 20]:
            if len(candles_1m) >= lookback:
                pos_flow = 0.0
                neg_flow = 0.0
                for i in range(-lookback, 0):
                    typical = (float(candles_1m[i]["h"]) + float(candles_1m[i]["l"]) + float(candles_1m[i]["c"])) / 3.0
                    prev_typical = (float(candles_1m[i-1]["h"]) + float(candles_1m[i-1]["l"]) + float(candles_1m[i-1]["c"])) / 3.0 if i > -len(candles_1m) else typical
                    raw_money = typical * float(candles_1m[i]["v"])
                    if typical > prev_typical:
                        pos_flow += raw_money
                    else:
                        neg_flow += raw_money
                total_flow = pos_flow + neg_flow + 1e-12
                kpis[f"mfi_proxy_{lookback}"] = float(100 - (100 / (1 + pos_flow / neg_flow)))
            else:
                kpis[f"mfi_proxy_{lookback}"] = 50.0

        # Parabolic SAR proxy (simplified)
        if len(candles_1m) >= 5:
            highs = [float(c["h"]) for c in candles_1m[-5:]]
            lows = [float(c["l"]) for c in candles_1m[-5:]]
            kpis["psar_proxy"] = float((max(highs) + min(lows)) / 2)
            kpis["dist_from_psar"] = float((float(candles_1m[-1]["c"]) - kpis["psar_proxy"]) / kpis["psar_proxy"]) if kpis["psar_proxy"] else 0.0
        else:
            kpis["psar_proxy"] = 0.0
            kpis["dist_from_psar"] = 0.0

        # Rate of Change (ROC)
        for lookback in [5, 10, 15, 20]:
            if len(closes_arr) >= lookback + 1:
                kpis[f"roc_{lookback}"] = float((closes_arr[-1] - closes_arr[-lookback - 1]) / (closes_arr[-lookback - 1] + 1e-12))
            else:
                kpis[f"roc_{lookback}"] = 0.0

        # Price acceleration (second derivative)
        if len(closes_arr) >= 3:
            v1 = closes_arr[-1] - closes_arr[-2]
            v2 = closes_arr[-2] - closes_arr[-3]
            kpis["price_acceleration"] = float(v1 - v2)
        else:
            kpis["price_acceleration"] = 0.0

        # Accumulation/Distribution proxy
        if len(candles_1m) >= 2:
            ad = 0.0
            for c in candles_1m:
                h = float(c["h"])
                l = float(c["l"])
                close = float(c["c"])
                vol = float(c["v"])
                range_ = h - l + 1e-12
                mfm = ((close - l) - (h - close)) / range_
                ad += mfm * vol
            kpis["ad_proxy"] = ad
        else:
            kpis["ad_proxy"] = 0.0

        # Chaikin Money Flow proxy
        for lookback in [10, 14, 20]:
            if len(candles_1m) >= lookback:
                ad_sum = 0.0
                vol_sum = 0.0
                for c in candles_1m[-lookback:]:
                    h = float(c["h"])
                    l = float(c["l"])
                    close = float(c["c"])
                    vol = float(c["v"])
                    range_ = h - l + 1e-12
                    ad_sum += ((close - l) - (h - close)) / range_ * vol
                    vol_sum += vol
                kpis[f"cmf_proxy_{lookback}"] = float(ad_sum / (vol_sum + 1e-12))
            else:
                kpis[f"cmf_proxy_{lookback}"] = 0.0

        # Percentage Price Oscillator proxy
        for fast, slow in [(5,10),(8,21),(12,26)]:
            fast_key = f"sma_{fast}"
            slow_key = f"sma_{slow}"
            if fast_key in kpis and slow_key in kpis:
                kpis[f"ppo_{fast}_{slow}"] = float((kpis[fast_key] - kpis[slow_key]) / (kpis[slow_key] + 1e-12))
            else:
                kpis[f"ppo_{fast}_{slow}"] = 0.0

        # Ultimate Oscillator proxy (simplified)
        if len(candles_1m) >= 10:
            buying_pressures = []
            trs = []
            for i in range(-10, 0):
                close = float(candles_1m[i]["c"])
                low = float(candles_1m[i]["l"])
                prev_close = float(candles_1m[i-1]["c"]) if i > -len(candles_1m) else close
                bp = close - min(low, prev_close)
                tr = max(float(candles_1m[i]["h"]) - float(candles_1m[i]["l"]), abs(float(candles_1m[i]["h"]) - prev_close), abs(float(candles_1m[i]["l"]) - prev_close))
                buying_pressures.append(bp)
                trs.append(tr)
            avg_bp = np.mean(buying_pressures) + 1e-12
            avg_tr = np.mean(trs) + 1e-12
            kpis["ultimate_osc_proxy"] = float(avg_bp / avg_tr * 100)
        else:
            kpis["ultimate_osc_proxy"] = 50.0

        # Market structure (higher highs / lower lows)
        for lookback in [5, 10, 15]:
            if len(candles_1m) >= lookback + 2:
                highs = [float(c["h"]) for c in candles_1m[-lookback:]]
                lows = [float(c["l"]) for c in candles_1m[-lookback:]]
                hh = sum(1 for i in range(1, len(highs)) if highs[i] > highs[i-1])
                ll = sum(1 for i in range(1, len(lows)) if lows[i] < lows[i-1])
                kpis[f"higher_highs_{lookback}"] = hh
                kpis[f"lower_lows_{lookback}"] = ll
            else:
                kpis[f"higher_highs_{lookback}"] = 0
                kpis[f"lower_lows_{lookback}"] = 0

        # Gap features
        if len(candles_1m) >= 2:
            prev_close = float(candles_1m[-2]["c"])
            cur_open = float(candles_1m[-1]["o"])
            kpis["gap_pct"] = float((cur_open - prev_close) / prev_close) if prev_close else 0.0
        else:
            kpis["gap_pct"] = 0.0

        # Intraday range ratio
        if candles_1m:
            cur_h = float(candles_1m[-1]["h"])
            cur_l = float(candles_1m[-1]["l"])
            cur_o = float(candles_1m[-1]["o"])
            cur_c = float(candles_1m[-1]["c"])
            range_ = cur_h - cur_l + 1e-12
            kpis["intraday_range_ratio"] = float(range_ / cur_o) if cur_o else 0.0
            kpis["close_to_high_ratio"] = float((cur_h - cur_c) / range_)
            kpis["close_to_low_ratio"] = float((cur_c - cur_l) / range_)
        else:
            kpis["intraday_range_ratio"] = 0.0
            kpis["close_to_high_ratio"] = 0.0
            kpis["close_to_low_ratio"] = 0.0

        # Variance ratio tests (simplified)
        for short, long in [(3,10),(5,15),(10,30)]:
            if len(candles_1m) >= long:
                var_short = np.var(np.diff(np.log(np.array([float(c["c"]) for c in candles_1m[-short:]]) + 1e-12)))
                var_long = np.var(np.diff(np.log(np.array([float(c["c"]) for c in candles_1m[-long:]]) + 1e-12)))
                kpis[f"variance_ratio_{short}_{long}"] = float((var_short / (var_long + 1e-12)) * (long / short))
            else:
                kpis[f"variance_ratio_{short}_{long}"] = 1.0

        # Additional momentum oscillators
        for lookback in [5, 10, 14, 20]:
            if len(closes_arr) >= lookback + 1:
                diffs = np.diff(closes_arr[-lookback-1:])
                kpis[f"avg_gain_{lookback}"] = float(np.mean(np.where(diffs > 0, diffs, 0)))
                kpis[f"avg_loss_{lookback}"] = float(np.mean(np.where(diffs < 0, -diffs, 0)))
                kpis[f"net_momentum_{lookback}"] = float(np.sum(diffs))
                kpis[f"max_up_streak_{lookback}"] = float(max([sum(1 for _ in g) for k, g in __import__('itertools').groupby(diffs > 0) if k], default=0))
                kpis[f"max_down_streak_{lookback}"] = float(max([sum(1 for _ in g) for k, g in __import__('itertools').groupby(diffs < 0) if k], default=0))
            else:
                kpis[f"avg_gain_{lookback}"] = 0.0
                kpis[f"avg_loss_{lookback}"] = 0.0
                kpis[f"net_momentum_{lookback}"] = 0.0
                kpis[f"max_up_streak_{lookback}"] = 0.0
                kpis[f"max_down_streak_{lookback}"] = 0.0

        # Open interest proxy (not available via public REST, placeholder)
        kpis["open_interest_proxy"] = float(ticker.get("total_size", 0.0)) if isinstance(ticker, dict) else 0.0

        # Liquidation pressure proxy (funding + basis)
        kpis["liq_pressure_proxy"] = float(kpis.get("funding_rate", 0.0) * 10000 + kpis.get("basis_bps", 0.0))

        # Correlation with self (lagged autocorrelation)
        for lag in [1, 3, 5]:
            if len(closes_arr) >= lag + 5:
                x = closes_arr[-lag-5:-lag]
                y = closes_arr[-5:]
                if np.std(x) > 0 and np.std(y) > 0:
                    kpis[f"autocorr_lag{lag}"] = float(np.corrcoef(x, y)[0,1])
                else:
                    kpis[f"autocorr_lag{lag}"] = 0.0
            else:
                kpis[f"autocorr_lag{lag}"] = 0.0

        # VWAP deviations
        for lookback in [10, 20, 30]:
            vwap_key = f"vwap_{lookback}"
            if vwap_key in kpis and kpis[vwap_key] != 0.0:
                kpis[f"vwap_dev_{lookback}"] = float((closes_arr[-1] - kpis[vwap_key]) / kpis[vwap_key])
            else:
                kpis[f"vwap_dev_{lookback}"] = 0.0

        # Historical volatility proxies (annualized)
        for lookback in [10, 20, 30]:
            if len(candles_1m) >= lookback:
                returns = np.diff(np.log(np.array([float(c["c"]) for c in candles_1m[-lookback:]]) + 1e-12))
                kpis[f"hist_vol_annual_{lookback}"] = float(np.std(returns) * np.sqrt(365 * 24 * 60 / lookback))
            else:
                kpis[f"hist_vol_annual_{lookback}"] = 0.0

        # Price distance from recent extremes
        for lookback in [10, 20, 30]:
            if len(candles_1m) >= lookback:
                highs = [float(c["h"]) for c in candles_1m[-lookback:]]
                lows = [float(c["l"]) for c in candles_1m[-lookback:]]
                cur = float(candles_1m[-1]["c"])
                kpis[f"dist_from_high_{lookback}"] = float((max(highs) - cur) / cur) if cur else 0.0
                kpis[f"dist_from_low_{lookback}"] = float((cur - min(lows)) / cur) if cur else 0.0
            else:
                kpis[f"dist_from_high_{lookback}"] = 0.0
                kpis[f"dist_from_low_{lookback}"] = 0.0

        return kpis
