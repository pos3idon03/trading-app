CREATE TABLE IF NOT EXISTS fundamentals (
    time            TIMESTAMPTZ      NOT NULL,
    instrument_id   INTEGER          REFERENCES instruments(id) ON DELETE CASCADE,
    metric_name     TEXT             NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    period          TEXT,
    statement_type  TEXT,
    source          TEXT             NOT NULL DEFAULT 'tiingo',
    raw_data        JSONB,
    CONSTRAINT uq_fundamentals UNIQUE (time, instrument_id, metric_name, source)
);

SELECT create_hypertable(
    'fundamentals',
    'time',
    chunk_time_interval => INTERVAL '90 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_fund_inst_metric ON fundamentals (instrument_id, metric_name, time DESC);

COMMENT ON TABLE fundamentals IS 'Tiingo fundamental metrics per instrument';
