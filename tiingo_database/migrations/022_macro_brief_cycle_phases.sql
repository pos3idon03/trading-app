ALTER TABLE macro_briefs
    ADD COLUMN IF NOT EXISTS situation_phase TEXT,
    ADD COLUMN IF NOT EXISTS outlook_phase TEXT;

COMMENT ON COLUMN macro_briefs.situation_phase IS 'Business-cycle phase for current situation (Expansion, Peak, etc.)';
COMMENT ON COLUMN macro_briefs.outlook_phase IS 'Expected near-term business-cycle phase from outlook forecaster';
