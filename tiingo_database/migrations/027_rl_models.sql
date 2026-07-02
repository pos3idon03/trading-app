CREATE TABLE IF NOT EXISTS rl_models (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    model_type      TEXT NOT NULL DEFAULT 'rl_ddqn',
    symbol          TEXT,
    timeframe       TEXT NOT NULL DEFAULT '1d',
    hyperparams     JSONB NOT NULL DEFAULT '{}'::jsonb,
    state_schema    JSONB NOT NULL DEFAULT '{}'::jsonb,
    train_metrics   JSONB,
    artifact_path   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rl_models_symbol ON rl_models (symbol, created_at DESC);

COMMENT ON TABLE rl_models IS 'Persisted reinforcement-learning trading agents (DDQN)';
