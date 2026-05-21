CREATE TABLE IF NOT EXISTS ohlcv (
    time            TIMESTAMPTZ      NOT NULL,
    instrument_id   INTEGER          NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    timeframe       TEXT             NOT NULL,
    open            DOUBLE PRECISION NOT NULL,
    high            DOUBLE PRECISION NOT NULL,
    low             DOUBLE PRECISION NOT NULL,
    close           DOUBLE PRECISION NOT NULL,
    volume          BIGINT           NOT NULL DEFAULT 0,
    vwap            DOUBLE PRECISION,
    trade_count     INTEGER,
    source          TEXT             NOT NULL,
    CONSTRAINT uq_ohlcv UNIQUE (time, instrument_id, timeframe, source)
);

SELECT create_hypertable(
    'ohlcv',
    'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_inst_tf_time
    ON ohlcv (instrument_id, timeframe, time DESC);

ALTER TABLE ohlcv SET (timescaledb.enable_columnstore = true);
CALL add_columnstore_policy('ohlcv', INTERVAL '30 days');

COMMENT ON TABLE ohlcv IS 'OHLCV bars from Tiingo EOD, IEX, crypto, and websocket';
