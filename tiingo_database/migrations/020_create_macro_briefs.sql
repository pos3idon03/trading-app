CREATE TABLE IF NOT EXISTS macro_briefs (
    id               BIGSERIAL PRIMARY KEY,
    as_of            DATE,
    situation        TEXT NOT NULL,
    outlook          TEXT NOT NULL,
    data_fingerprint TEXT NOT NULL,
    model_name       TEXT NOT NULL,
    generated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_macro_briefs_generated_at
    ON macro_briefs (generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_macro_briefs_fingerprint
    ON macro_briefs (data_fingerprint);

COMMENT ON TABLE macro_briefs IS 'Gemini-generated macro overview briefs keyed by overview data fingerprint';
