CREATE TABLE IF NOT EXISTS instruments (
    id              SERIAL PRIMARY KEY,
    symbol          TEXT        NOT NULL UNIQUE,
    tiingo_ticker   TEXT,
    name            TEXT,
    asset_type      TEXT        NOT NULL DEFAULT 'stock',
    exchange        TEXT,
    currency        TEXT        NOT NULL DEFAULT 'USD',
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_instruments_symbol ON instruments (symbol);
CREATE INDEX IF NOT EXISTS idx_instruments_active ON instruments (is_active) WHERE is_active = TRUE;

COMMENT ON TABLE instruments IS 'Watchlist instruments for Tiingo ingestion';
