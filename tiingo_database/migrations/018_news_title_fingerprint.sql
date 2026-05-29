ALTER TABLE news_articles
    ADD COLUMN IF NOT EXISTS title_fingerprint TEXT;

CREATE INDEX IF NOT EXISTS idx_news_title_fingerprint_published
    ON news_articles (title_fingerprint, published_at DESC)
    WHERE title_fingerprint IS NOT NULL;

COMMENT ON COLUMN news_articles.title_fingerprint IS 'SHA-256 of normalized title for near-duplicate detection';
