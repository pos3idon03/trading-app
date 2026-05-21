CREATE TABLE IF NOT EXISTS news_articles (
    id              BIGSERIAL PRIMARY KEY,
    published_at    TIMESTAMPTZ NOT NULL,
    title           TEXT        NOT NULL,
    url             TEXT        NOT NULL UNIQUE,
    description     TEXT,
    source          TEXT        NOT NULL DEFAULT 'tiingo',
    tickers         TEXT[]      NOT NULL DEFAULT '{}',
    tags            TEXT[]      NOT NULL DEFAULT '{}',
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles (published_at DESC);
CREATE INDEX IF NOT EXISTS idx_news_tickers ON news_articles USING GIN (tickers);

COMMENT ON TABLE news_articles IS 'Tiingo news articles';
