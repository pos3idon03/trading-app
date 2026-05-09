"""Tests for the signal aggregator."""
import pytest

from features.live_trading.signal_aggregator import (
    AISignalInput,
    AggregatedSignal,
    RiskBounds,
    aggregate_signal,
    score_ai_signal,
    score_risk_bounds,
    score_technical_indicators,
)


class TestScoreTechnicalIndicators:
    def test_oversold_rsi_bullish(self):
        indicators = {"rsi": 20.0}
        score, reasons = score_technical_indicators(indicators)
        assert score > 0
        assert any("RSI" in r for r in reasons)

    def test_overbought_rsi_bearish(self):
        indicators = {"rsi": 85.0}
        score, reasons = score_technical_indicators(indicators)
        assert score < 0

    def test_neutral_rsi(self):
        indicators = {"rsi": 50.0}
        score, _ = score_technical_indicators(indicators)
        assert score == 0.0

    def test_positive_macd_histogram(self):
        indicators = {"macd_histogram": 0.5, "macd": 1.0, "macd_signal": 0.5}
        score, _ = score_technical_indicators(indicators)
        assert score > 0

    def test_negative_macd_histogram(self):
        indicators = {"macd_histogram": -0.5, "macd": -1.0, "macd_signal": -0.5}
        score, _ = score_technical_indicators(indicators)
        assert score < 0

    def test_bollinger_oversold(self):
        indicators = {"bb_percent": 0.05}
        score, _ = score_technical_indicators(indicators)
        assert score > 0

    def test_bollinger_overbought(self):
        indicators = {"bb_percent": 0.95}
        score, _ = score_technical_indicators(indicators)
        assert score < 0

    def test_vwap_above(self):
        indicators = {"close_price": 110.0, "vwap": 100.0}
        score, _ = score_technical_indicators(indicators)
        assert score > 0

    def test_vwap_below(self):
        indicators = {"close_price": 90.0, "vwap": 100.0}
        score, _ = score_technical_indicators(indicators)
        assert score < 0

    def test_no_indicators(self):
        score, reasons = score_technical_indicators({})
        assert score == 0.0
        assert "No technical indicators" in reasons[0]

    def test_combined_signals(self):
        indicators = {
            "rsi": 25.0,
            "macd_histogram": 0.3,
            "macd": 0.5,
            "macd_signal": 0.2,
            "bb_percent": 0.1,
            "close_price": 105.0,
            "vwap": 100.0,
        }
        score, reasons = score_technical_indicators(indicators)
        assert score > 0
        assert len(reasons) == 4


class TestScoreRiskBounds:
    def test_favorable_risk(self):
        risk = RiskBounds(current_price=100.0, p25=95.0, p50=105.0, p75=115.0, p95=130.0)
        score, _ = score_risk_bounds(risk)
        assert score > 0

    def test_unfavorable_risk(self):
        risk = RiskBounds(current_price=100.0, p25=80.0, p50=85.0, p75=90.0, p95=95.0)
        score, _ = score_risk_bounds(risk)
        assert score < 0

    def test_no_data(self):
        risk = RiskBounds(current_price=100.0)
        score, reasons = score_risk_bounds(risk)
        assert score == 0.0
        assert "No Monte Carlo" in reasons[0]

    def test_high_drawdown_penalty(self):
        risk = RiskBounds(current_price=100.0, p25=95.0, p50=105.0, p75=115.0, max_drawdown=0.25)
        score, _ = score_risk_bounds(risk)
        assert score < 1.0


class TestScoreAISignal:
    def test_bullish_high_conviction(self):
        ai = AISignalInput(bias="bullish", conviction_score=9.0)
        score, _ = score_ai_signal(ai)
        assert score > 0

    def test_bearish_signal(self):
        ai = AISignalInput(bias="bearish", conviction_score=8.0)
        score, _ = score_ai_signal(ai)
        assert score < 0

    def test_neutral_signal(self):
        ai = AISignalInput(bias="neutral", conviction_score=5.0)
        score, _ = score_ai_signal(ai)
        assert score == 0.0

    def test_no_bias(self):
        ai = AISignalInput()
        score, reasons = score_ai_signal(ai)
        assert score == 0.0
        assert "No AI signal" in reasons[0]

    def test_sentiment_adjustment(self):
        ai = AISignalInput(bias="bullish", conviction_score=7.0, sentiment_score=8.0)
        score, reasons = score_ai_signal(ai)
        assert score > 0
        assert any("Sentiment" in r for r in reasons)


class TestAggregateSignal:
    def test_strong_buy_signal(self):
        indicators = {"rsi": 20.0, "macd_histogram": 0.5, "macd": 1.0, "macd_signal": 0.5, "bb_percent": 0.05}
        risk = RiskBounds(current_price=100.0, p25=95.0, p50=110.0, p75=120.0)
        ai = AISignalInput(bias="bullish", conviction_score=9.0)

        signal = aggregate_signal("AAPL", "1h", indicators, risk, ai)
        assert isinstance(signal, AggregatedSignal)
        assert signal.action == "BUY"
        assert signal.confidence > 0

    def test_hold_on_neutral(self):
        indicators = {"rsi": 50.0}
        signal = aggregate_signal("AAPL", "1h", indicators)
        assert signal.action == "HOLD"

    def test_sell_signal(self):
        indicators = {"rsi": 85.0, "macd_histogram": -0.5, "macd": -1.0, "macd_signal": -0.5, "bb_percent": 0.95}
        risk = RiskBounds(current_price=100.0, p25=70.0, p50=80.0, p75=85.0)
        ai = AISignalInput(bias="bearish", conviction_score=9.0)

        signal = aggregate_signal("AAPL", "1h", indicators, risk, ai)
        assert signal.action == "SELL"

    def test_without_optional_inputs(self):
        signal = aggregate_signal("AAPL", "1h")
        assert signal.action == "HOLD"
        assert signal.symbol == "AAPL"
        assert signal.timeframe == "1h"

    def test_weight_redistribution(self):
        indicators = {"rsi": 20.0, "macd_histogram": 0.5, "macd": 1.0, "macd_signal": 0.5}
        signal = aggregate_signal("AAPL", "1h", indicators)
        assert signal.technical_score > 0
        assert signal.risk_score == 0.0
        assert signal.ai_score == 0.0

    def test_reasoning_populated(self):
        indicators = {"rsi": 25.0}
        signal = aggregate_signal("AAPL", "1h", indicators)
        assert signal.reasoning is not None
        assert len(signal.reasoning) > 0
