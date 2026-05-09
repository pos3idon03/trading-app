-- Migration 001: assets lookup table
CREATE TABLE IF NOT EXISTS assets (
    id          SERIAL PRIMARY KEY,
    symbol      TEXT        NOT NULL UNIQUE,
    name        TEXT,
    asset_type  TEXT        NOT NULL DEFAULT 'stock',  -- 'stock','etf','crypto','forex'
    exchange    TEXT,
    currency    TEXT        NOT NULL DEFAULT 'USD',
    is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_assets_symbol ON assets (symbol);
CREATE INDEX IF NOT EXISTS idx_assets_type   ON assets (asset_type);

COMMENT ON TABLE assets IS 'Master list of tradeable instruments';
