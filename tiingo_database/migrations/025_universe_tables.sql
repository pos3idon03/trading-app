CREATE TABLE IF NOT EXISTS universe_definitions (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    source      TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS universe_members (
    id              SERIAL PRIMARY KEY,
    universe_id     INTEGER NOT NULL REFERENCES universe_definitions(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,
    effective_from  DATE NOT NULL,
    effective_to    DATE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (universe_id, symbol, effective_from)
);

CREATE INDEX IF NOT EXISTS idx_universe_members_lookup
    ON universe_members (universe_id, effective_from, effective_to);

COMMENT ON TABLE universe_definitions IS 'Named investable universes (e.g. SP500 custom)';
COMMENT ON TABLE universe_members IS 'Point-in-time universe membership for survivorship-correct backtests';
