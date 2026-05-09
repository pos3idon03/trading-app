"""Signal aggregator: combines technical indicators, Monte Carlo risk, and AI agent signals."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_WEIGHTS = {
    "technical": 0.40,
    "risk": 0.25,
    "ai": 0.35,
}

RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0
CONFIDENCE_THRESHOLD = 0.55


@dataclass
class RiskBounds:
    """Risk constraints from Monte Carlo simulation."""
    current_price: float
    p5: float | None = None
    p25: float | None = None
    p50: float | None = None
    p75: float | None = None
    p95: float | None = None
    max_drawdown: float | None = None

    def to_dict(self) -> dict:
        return {
            "current_price": self.current_price,
            "p5": self.p5,
            "p25": self.p25,
            "p50": self.p50,
            "p75": self.p75,
            "p95": self.p95,
            "max_drawdown": self.max_drawdown,
        }


@dataclass
class AISignalInput:
    """AI agent signal data."""
    bias: str | None = None
    conviction_score: float | None = None
    sentiment_score: float | None = None

    def to_dict(self) -> dict:
        return {
            "bias": self.bias,
            "conviction_score": self.conviction_score,
            "sentiment_score": self.sentiment_score,
        }


@dataclass
class AggregatedSignal:
    symbol: str
    timeframe: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    technical_score: float
    risk_score: float
    ai_score: float
    reasoning: str
    indicator_snapshot: dict | None = None
    risk_data: dict | None = None
    ai_signal: dict | None = None


def score_technical_indicators(indicators: dict) -> tuple[float, list[str]]:
    """Score technical indicators on -1 (bearish) to +1 (bullish) scale."""
    signals: list[float] = []
    reasons: list[str] = []

    rsi = indicators.get("rsi")
    if rsi is not None:
        rsi_score = _score_rsi(rsi)
        signals.append(rsi_score)
        reasons.append(f"RSI={rsi:.1f} ({'oversold' if rsi < RSI_OVERSOLD else 'overbought' if rsi > RSI_OVERBOUGHT else 'neutral'})")

    macd_hist = indicators.get("macd_histogram")
    if macd_hist is not None:
        macd_score = _score_macd(macd_hist, indicators.get("macd"), indicators.get("macd_signal"))
        signals.append(macd_score)
        reasons.append(f"MACD_hist={macd_hist:.4f} ({'bullish' if macd_score > 0 else 'bearish'})")

    bb_pct = indicators.get("bb_percent")
    if bb_pct is not None:
        bb_score = _score_bollinger(bb_pct)
        signals.append(bb_score)
        reasons.append(f"BB%={bb_pct:.2f} ({'oversold' if bb_pct < 0.2 else 'overbought' if bb_pct > 0.8 else 'neutral'})")

    vwap = indicators.get("vwap")
    close = indicators.get("close_price")
    if vwap is not None and close is not None and vwap > 0:
        vwap_score = _score_vwap(close, vwap)
        signals.append(vwap_score)
        reasons.append(f"Price {'above' if close > vwap else 'below'} VWAP ({close:.2f} vs {vwap:.2f})")

    if not signals:
        return 0.0, ["No technical indicators available"]

    return sum(signals) / len(signals), reasons


def _score_rsi(rsi: float) -> float:
    if rsi < RSI_OVERSOLD:
        return min(1.0, (RSI_OVERSOLD - rsi) / 20.0)
    elif rsi > RSI_OVERBOUGHT:
        return max(-1.0, (RSI_OVERBOUGHT - rsi) / 20.0)
    return 0.0


def _score_macd(histogram: float, macd: float | None, signal: float | None) -> float:
    if histogram > 0:
        return min(1.0, histogram / abs(histogram + 0.001))
    elif histogram < 0:
        return max(-1.0, histogram / abs(histogram + 0.001))
    return 0.0


def _score_bollinger(bb_percent: float) -> float:
    if bb_percent < 0.2:
        return min(1.0, (0.2 - bb_percent) / 0.2)
    elif bb_percent > 0.8:
        return max(-1.0, -(bb_percent - 0.8) / 0.2)
    return 0.0


def _score_vwap(close: float, vwap: float) -> float:
    diff_pct = (close - vwap) / vwap
    return max(-1.0, min(1.0, diff_pct * 10))


def score_risk_bounds(risk: RiskBounds) -> tuple[float, list[str]]:
    """Score risk from Monte Carlo percentiles. Positive = room to grow, negative = risky."""
    reasons: list[str] = []
    price = risk.current_price

    if risk.p50 is None:
        return 0.0, ["No Monte Carlo data available"]

    upside = (risk.p75 - price) / price if risk.p75 else 0.0
    downside = (price - risk.p25) / price if risk.p25 else 0.0
    score = max(-1.0, min(1.0, (upside - downside) * 5))

    reasons.append(f"MC upside={upside:.2%}, downside={downside:.2%}")

    if risk.max_drawdown is not None:
        reasons.append(f"MC max_drawdown={risk.max_drawdown:.2%}")
        if risk.max_drawdown > 0.15:
            score -= 0.3

    return max(-1.0, min(1.0, score)), reasons


def score_ai_signal(ai: AISignalInput) -> tuple[float, list[str]]:
    """Convert AI agent bias and conviction to a score."""
    reasons: list[str] = []

    if ai.bias is None:
        return 0.0, ["No AI signal available"]

    bias_map = {"bullish": 1.0, "bearish": -1.0, "neutral": 0.0}
    direction = bias_map.get(ai.bias.lower(), 0.0)
    conviction = ai.conviction_score if ai.conviction_score is not None else 0.5
    score = direction * min(1.0, conviction / 10.0)

    reasons.append(f"AI bias={ai.bias}, conviction={conviction:.1f}")

    if ai.sentiment_score is not None:
        sentiment_adj = (ai.sentiment_score - 5.0) / 10.0
        score = score * 0.7 + sentiment_adj * 0.3
        reasons.append(f"Sentiment={ai.sentiment_score:.1f}/10")

    return max(-1.0, min(1.0, score)), reasons


def aggregate_signal(
    symbol: str,
    timeframe: str,
    indicators: dict | None = None,
    risk_bounds: RiskBounds | None = None,
    ai_input: AISignalInput | None = None,
    weights: dict | None = None,
) -> AggregatedSignal:
    """Combine all signal sources into a single BUY/SELL/HOLD decision."""
    w = weights or DEFAULT_WEIGHTS.copy()
    all_reasons: list[str] = []

    tech_score, tech_reasons = _compute_component(
        indicators, score_technical_indicators, w, "technical", all_reasons
    )
    risk_score, risk_reasons = _compute_risk_component(
        risk_bounds, w, all_reasons
    )
    ai_score, ai_reasons = _compute_ai_component(
        ai_input, w, all_reasons
    )

    all_reasons.extend(tech_reasons)
    all_reasons.extend(risk_reasons)
    all_reasons.extend(ai_reasons)

    composite = (
        tech_score * w["technical"]
        + risk_score * w["risk"]
        + ai_score * w["ai"]
    )

    action, confidence = _decide_action(composite)

    return AggregatedSignal(
        symbol=symbol,
        timeframe=timeframe,
        action=action,
        confidence=round(confidence, 4),
        technical_score=round(tech_score, 4),
        risk_score=round(risk_score, 4),
        ai_score=round(ai_score, 4),
        reasoning=" | ".join(all_reasons),
        indicator_snapshot=indicators,
        risk_data=risk_bounds.to_dict() if risk_bounds else None,
        ai_signal=ai_input.to_dict() if ai_input else None,
    )


def _compute_component(indicators, scorer_fn, w, key, all_reasons):
    if indicators is not None:
        score, reasons = scorer_fn(indicators)
        return score, reasons
    w_remaining = w.pop(key, 0)
    _redistribute_weights(w, w_remaining)
    return 0.0, ["No technical indicators"]


def _compute_risk_component(risk_bounds, w, all_reasons):
    if risk_bounds is not None:
        score, reasons = score_risk_bounds(risk_bounds)
        return score, reasons
    w_remaining = w.pop("risk", 0)
    _redistribute_weights(w, w_remaining)
    return 0.0, ["No Monte Carlo risk data"]


def _compute_ai_component(ai_input, w, all_reasons):
    if ai_input is not None:
        score, reasons = score_ai_signal(ai_input)
        return score, reasons
    w_remaining = w.pop("ai", 0)
    _redistribute_weights(w, w_remaining)
    return 0.0, ["No AI signal"]


def _redistribute_weights(w: dict, amount: float) -> None:
    remaining_keys = [k for k in w if w[k] > 0]
    if remaining_keys:
        share = amount / len(remaining_keys)
        for k in remaining_keys:
            w[k] += share


def _decide_action(composite: float) -> tuple[str, float]:
    confidence = abs(composite)
    if composite > 0 and confidence >= CONFIDENCE_THRESHOLD:
        return "BUY", confidence
    elif composite < 0 and confidence >= CONFIDENCE_THRESHOLD:
        return "SELL", confidence
    return "HOLD", confidence
