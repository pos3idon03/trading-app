CREATE TABLE IF NOT EXISTS optimization_runs (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    strategy_name   VARCHAR NOT NULL,
    timeframe       VARCHAR NOT NULL,
    start_date      TIMESTAMPTZ NOT NULL,
    end_date        TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    param_grid      JSONB NOT NULL,
    n_splits        INTEGER NOT NULL,
    optimize_metric VARCHAR NOT NULL,
    best_params     JSONB,
    best_metric     DOUBLE PRECISION,
    all_results     JSONB,
    duration_ms     INTEGER,
    status          VARCHAR NOT NULL DEFAULT 'pending',
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS ix_optimization_runs_asset_id ON optimization_runs(asset_id);
CREATE INDEX IF NOT EXISTS ix_optimization_runs_status ON optimization_runs(status);
