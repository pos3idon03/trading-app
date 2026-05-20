-- Migration 021: Background jobs for MC backtest walk-forward optimization
CREATE TABLE IF NOT EXISTS mc_backtest_optimize_jobs (
    id                  SERIAL PRIMARY KEY,
    asset_id            INTEGER      NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    symbol              TEXT         NOT NULL,
    request             JSONB        NOT NULL,
    status              TEXT         NOT NULL DEFAULT 'pending',
    progress_pct        DOUBLE PRECISION NOT NULL DEFAULT 0,
    progress_message    TEXT,
    completed_steps     INTEGER      NOT NULL DEFAULT 0,
    total_steps         INTEGER,
    result              JSONB,
    error_message       TEXT,
    duration_ms         INTEGER,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mc_bt_opt_jobs_status
    ON mc_backtest_optimize_jobs (status, created_at DESC);

COMMENT ON TABLE mc_backtest_optimize_jobs IS
    'Async walk-forward MC backtest optimization jobs with progress tracking';
