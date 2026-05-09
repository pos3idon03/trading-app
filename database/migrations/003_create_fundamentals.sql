-- Migration 003: Fundamentals / macro data hypertable
CREATE TABLE IF NOT EXISTS fundamentals (
    time        TIMESTAMPTZ      NOT NULL,
    asset_id    INTEGER          REFERENCES assets(id) ON DELETE CASCADE,  -- NULL for macro metrics
    metric_name TEXT             NOT NULL,  -- 'pe_ratio','eps','revenue','cpi','fed_funds_rate'
    value       DOUBLE PRECISION NOT NULL,
    period      TEXT,                       -- 'Q1-2024','FY-2023', etc.
    source      TEXT             NOT NULL,
    raw_data    JSONB,                      -- full raw API response for traceability
    CONSTRAINT uq_fundamentals UNIQUE (time, asset_id, metric_name, source)
);

SELECT create_hypertable(
    'fundamentals',
    'time',
    chunk_time_interval => INTERVAL '90 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_fund_asset_metric ON fundamentals (asset_id, metric_name, time DESC);
CREATE INDEX IF NOT EXISTS idx_fund_metric        ON fundamentals (metric_name, time DESC);

COMMENT ON TABLE fundamentals IS 'Fundamental and macro data, hypertable partitioned by time';
