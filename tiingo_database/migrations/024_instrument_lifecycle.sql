ALTER TABLE instruments
    ADD COLUMN IF NOT EXISTS delisted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delist_reason TEXT;

COMMENT ON COLUMN instruments.delisted_at IS 'When the instrument ceased trading (if known)';
COMMENT ON COLUMN instruments.delist_reason IS 'bankrupt, acquired, merged, etc.';
