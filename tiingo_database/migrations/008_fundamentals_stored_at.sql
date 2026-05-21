ALTER TABLE fundamentals
    ADD COLUMN IF NOT EXISTS stored_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_fund_inst_stored_at
    ON fundamentals (instrument_id, stored_at DESC);
