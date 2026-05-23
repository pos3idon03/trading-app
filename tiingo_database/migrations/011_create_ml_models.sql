CREATE TABLE ml_models (
    id              UUID PRIMARY KEY,
    name            TEXT NOT NULL,
    model_type      TEXT NOT NULL,
    feature_mode    TEXT NOT NULL,
    feature_schema  JSONB NOT NULL,
    hyperparams     JSONB NOT NULL DEFAULT '{}',
    train_metrics   JSONB,
    artifact_path   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ml_models_created_at ON ml_models (created_at DESC);
