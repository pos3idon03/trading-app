-- Migration 011: Add asset_id FK to tables that previously only stored a symbol string.
-- Also backfills existing rows and normalises all stored symbols to uppercase.

-- Step 1: normalise all existing asset symbols to uppercase so the backfill
-- JOIN below works regardless of how data was inserted in the past.
UPDATE assets
    SET symbol = UPPER(symbol)
    WHERE symbol != UPPER(symbol);

-- ─── agent_analyses ──────────────────────────────────────────────────────────
ALTER TABLE agent_analyses
    ADD COLUMN IF NOT EXISTS asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL;

UPDATE agent_analyses aa
    SET asset_id = a.id
    FROM assets a
    WHERE UPPER(aa.symbol) = a.symbol
      AND aa.asset_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_agent_analyses_asset_id ON agent_analyses(asset_id);

-- ─── live_indicators ─────────────────────────────────────────────────────────
ALTER TABLE live_indicators
    ADD COLUMN IF NOT EXISTS asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL;

UPDATE live_indicators li
    SET asset_id = a.id
    FROM assets a
    WHERE UPPER(li.symbol) = a.symbol
      AND li.asset_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_live_indicators_asset_id ON live_indicators(asset_id);

-- ─── trading_signals ─────────────────────────────────────────────────────────
ALTER TABLE trading_signals
    ADD COLUMN IF NOT EXISTS asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL;

UPDATE trading_signals ts
    SET asset_id = a.id
    FROM assets a
    WHERE UPPER(ts.symbol) = a.symbol
      AND ts.asset_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_trading_signals_asset_id ON trading_signals(asset_id);

-- ─── orders ──────────────────────────────────────────────────────────────────
ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL;

UPDATE orders o
    SET asset_id = a.id
    FROM assets a
    WHERE UPPER(o.symbol) = a.symbol
      AND o.asset_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_orders_asset_id ON orders(asset_id);

-- ─── risk_events ─────────────────────────────────────────────────────────────
-- symbol is already nullable here, so asset_id is also nullable.
ALTER TABLE risk_events
    ADD COLUMN IF NOT EXISTS asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL;

UPDATE risk_events re
    SET asset_id = a.id
    FROM assets a
    WHERE re.symbol IS NOT NULL
      AND UPPER(re.symbol) = a.symbol
      AND re.asset_id IS NULL;

CREATE INDEX IF NOT EXISTS ix_risk_events_asset_id ON risk_events(asset_id);
