-- Migration 004: Monte Carlo simulation metadata + results
CREATE TABLE IF NOT EXISTS simulations (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER      NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    timeframe       TEXT         NOT NULL DEFAULT '1d',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    calibration_start TIMESTAMPTZ,
    calibration_end   TIMESTAMPTZ,
    -- Vasicek + jump parameters (stored for reproducibility)
    params          JSONB        NOT NULL,
    -- Simulation configuration
    num_paths       INTEGER      NOT NULL DEFAULT 1000,
    horizon_steps   INTEGER      NOT NULL,
    dt              DOUBLE PRECISION NOT NULL,
    s0              DOUBLE PRECISION NOT NULL,
    -- Result summary (percentiles, stats)
    result_summary  JSONB,
    -- Store compressed path percentiles (5,25,50,75,95) as arrays
    percentile_paths JSONB,
    duration_ms     INTEGER,
    status          TEXT         NOT NULL DEFAULT 'pending',  -- 'pending','running','done','error'
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_sim_asset ON simulations (asset_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_sim_status ON simulations (status);

COMMENT ON TABLE simulations IS 'Monte Carlo simulation runs and their compressed results';
