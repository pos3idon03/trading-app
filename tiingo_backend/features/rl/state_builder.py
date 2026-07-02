"""Assemble normalized RL observation vectors from OHLCV + indicators."""

from __future__ import annotations

from dataclasses import dataclass, field

from features.backtesting.indicators import (
    compute_bollinger_bands,
    compute_macd,
    compute_rsi,
)


@dataclass
class StateBuilder:
    state_window: int = 32
    mean_: list[float] = field(default_factory=list)
    std_: list[float] = field(default_factory=list)

    def fit(self, vectors: list[list[float]]) -> None:
        if not vectors:
            return
        dim = len(vectors[0])
        self.mean_ = [0.0] * dim
        self.std_ = [1.0] * dim
        for j in range(dim):
            col = [row[j] for row in vectors]
            m = sum(col) / len(col)
            v = sum((x - m) ** 2 for x in col) / len(col)
            self.mean_[j] = m
            self.std_[j] = max(v ** 0.5, 1e-9)

    def transform(self, vector: list[float]) -> list[float]:
        if not self.mean_:
            return vector
        return [(v - m) / s for v, m, s in zip(vector, self.mean_, self.std_)]

    def _bar_returns(self, closes: list[float], index: int) -> list[float]:
        start = max(0, index - self.state_window + 1)
        window = closes[start : index + 1]
        rets = []
        for i in range(1, len(window)):
            if window[i - 1] > 0:
                rets.append((window[i] / window[i - 1]) - 1.0)
        while len(rets) < self.state_window:
            rets.insert(0, 0.0)
        return rets[-self.state_window :]

    def _ohlcv_features(self, bars: list[dict], index: int) -> list[float]:
        start = max(0, index - self.state_window + 1)
        window = bars[start : index + 1]
        closes = [float(b["close"]) for b in window]
        rets = self._bar_returns(closes, len(closes) - 1)
        last = window[-1]
        close = float(last["close"]) or 1.0
        hl = (float(last["high"]) - float(last["low"])) / close
        oc = (close - float(last["open"])) / close
        vol_norm = float(last.get("volume") or 0.0) / max(
            float(window[-2].get("volume") or 1.0) if len(window) > 1 else 1.0,
            1.0,
        )
        return rets + [hl, oc, min(vol_norm, 5.0)]

    def _indicator_scalars(self, bars: list[dict], index: int) -> list[float]:
        closes = [float(b["close"]) for b in bars]
        highs = [float(b["high"]) for b in bars]
        lows = [float(b["low"]) for b in bars]
        close = closes[index] or 1.0
        rsi_vals = compute_rsi(closes, 14)
        macd_line, macd_signal, macd_hist = compute_macd(closes)
        _, upper, lower = compute_bollinger_bands(closes, 20, 2.0)
        rsi = (rsi_vals[index] or 50.0) / 100.0
        m_line = (macd_line[index] or 0.0) / close
        m_sig = (macd_signal[index] or 0.0) / close
        m_hist = (macd_hist[index] or 0.0) / close
        u, l = upper[index], lower[index]
        bb_pct = 0.5
        if u is not None and l is not None and (u - l) > 0:
            bb_pct = (close - l) / (u - l)
        return [rsi, m_line, m_sig, m_hist, bb_pct]

    def build_state(
        self,
        bars: list[dict],
        index: int,
        *,
        position_flag: float,
        position_age: float,
        unrealized_pnl_pct: float,
        cash_weight: float,
        drawdown_pct: float,
        realized_vol: float,
        sentiment_score: float = 0.0,
    ) -> list[float]:
        market = self._ohlcv_features(bars, index) + self._indicator_scalars(bars, index)
        position = [
            position_flag,
            position_age,
            unrealized_pnl_pct,
            cash_weight,
            drawdown_pct / 100.0,
            realized_vol,
            sentiment_score,
        ]
        return self.transform(market + position)

    def build_state_legacy(
        self,
        closes: list[float],
        index: int,
        **kwargs,
    ) -> list[float]:
        bars = [
            {"open": c, "high": c, "low": c, "close": c, "volume": 0.0}
            for c in closes
        ]
        return self.build_state(bars, index, **kwargs)
