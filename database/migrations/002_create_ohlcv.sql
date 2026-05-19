-- Migration 002: OHLCV hypertable (TimescaleDB)
CREATE TABLE IF NOT EXISTS ohlcv (
    time        TIMESTAMPTZ      NOT NULL,
    asset_id    INTEGER          NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    timeframe   TEXT             NOT NULL,  -- '1m','5m','15m','30m','1h','4h','1d'
    open        DOUBLE PRECISION NOT NULL,
    high        DOUBLE PRECISION NOT NULL,
    low         DOUBLE PRECISION NOT NULL,
    close       DOUBLE PRECISION NOT NULL,
    volume      BIGINT           NOT NULL DEFAULT 0,
    vwap        DOUBLE PRECISION,
    trade_count INTEGER,
    source      TEXT             NOT NULL,  -- 'polygon','alpaca','yfinance'
    CONSTRAINT uq_ohlcv UNIQUE (time, asset_id, timeframe, source)
);

-- Convert to hypertable partitioned by time (7-day chunks)
SELECT create_hypertable(
    'ohlcv',
    'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Composite index: most queries filter by asset + timeframe + time range
CREATE INDEX IF NOT EXISTS idx_ohlcv_asset_tf_time
    ON ohlcv (asset_id, timeframe, time DESC);

-- Enable columnstore (TimescaleDB 3.x) then set compression policy
ALTER TABLE ohlcv SET (timescaledb.enable_columnstore = true);
CALL add_columnstore_policy('ohlcv', INTERVAL '30 days');

COMMENT ON TABLE ohlcv IS 'OHLCV price data hypertable, partitioned by time';
