-- Migration 012: Company profiles — qualitative fundamental data per asset
CREATE TABLE IF NOT EXISTS company_profiles (
    asset_id         INTEGER PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
    sector           TEXT,
    industry         TEXT,
    business_summary TEXT,
    website          TEXT,
    country          TEXT,
    employees        INTEGER,
    officers         JSONB    DEFAULT '[]'::jsonb,
    source           TEXT     NOT NULL DEFAULT 'yfinance',
    fetched_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_company_profiles_sector   ON company_profiles (sector);
CREATE INDEX IF NOT EXISTS idx_company_profiles_industry ON company_profiles (industry);

COMMENT ON TABLE company_profiles IS 'Qualitative company data: sector, industry, summary, officers';
