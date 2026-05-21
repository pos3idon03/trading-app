CREATE TABLE IF NOT EXISTS macro_series (
    series_id       TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    frequency       TEXT,
    category        TEXT NOT NULL DEFAULT 'general',
    is_enabled      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS macro_observations (
    series_id       TEXT             NOT NULL REFERENCES macro_series(series_id) ON DELETE CASCADE,
    obs_date        DATE             NOT NULL,
    value           DOUBLE PRECISION,
    CONSTRAINT uq_macro_obs UNIQUE (series_id, obs_date)
);

SELECT create_hypertable(
    'macro_observations',
    'obs_date',
    chunk_time_interval => INTERVAL '365 days',
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_macro_obs_series ON macro_observations (series_id, obs_date DESC);

COMMENT ON TABLE macro_series IS 'FRED macro series catalog';
COMMENT ON TABLE macro_observations IS 'FRED observation values';
