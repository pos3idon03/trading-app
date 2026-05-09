-- Phase 5: Live trading indicators and signals

CREATE TABLE IF NOT EXISTS live_indicators (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR NOT NULL,
    timeframe       VARCHAR NOT NULL,
    rsi             DOUBLE PRECISION,
    macd            DOUBLE PRECISION,
    macd_signal     DOUBLE PRECISION,
    macd_histogram  DOUBLE PRECISION,
    bb_upper        DOUBLE PRECISION,
    bb_middle       DOUBLE PRECISION,
    bb_lower        DOUBLE PRECISION,
    vwap            DOUBLE PRECISION,
    close_price     DOUBLE PRECISION,
    volume          BIGINT,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_live_indicators_symbol_tf ON live_indicators (symbol, timeframe, created_at DESC);

CREATE TABLE IF NOT EXISTS trading_signals (
    id                  SERIAL PRIMARY KEY,
    symbol              VARCHAR NOT NULL,
    timeframe           VARCHAR NOT NULL,
    action              VARCHAR NOT NULL,
    confidence          DOUBLE PRECISION,
    technical_score     DOUBLE PRECISION,
    risk_score          DOUBLE PRECISION,
    ai_score            DOUBLE PRECISION,
    indicator_snapshot  JSONB,
    risk_data           JSONB,
    ai_signal           JSONB,
    reasoning           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_trading_signals_symbol ON trading_signals (symbol, created_at DESC);
