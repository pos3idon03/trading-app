CREATE TABLE IF NOT EXISTS news_sentiment_enrichment (
    id                  BIGSERIAL PRIMARY KEY,
    news_article_id     BIGINT      NOT NULL REFERENCES news_articles (id) ON DELETE CASCADE,
    provider            TEXT        NOT NULL DEFAULT 'gemini',
    model_name          TEXT        NOT NULL,
    model_version       TEXT        NOT NULL,
    finbert_label       TEXT        NOT NULL,
    refined_label       TEXT        NOT NULL,
    refined_confidence  DOUBLE PRECISION NOT NULL,
    score_positive      DOUBLE PRECISION NOT NULL,
    score_negative      DOUBLE PRECISION NOT NULL,
    score_neutral       DOUBLE PRECISION NOT NULL,
    rationale           TEXT,
    citations           JSONB,
    search_queries      JSONB,
    raw_response        JSONB,
    analyzed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error               TEXT,
    UNIQUE (news_article_id, model_name, model_version)
);

CREATE INDEX IF NOT EXISTS idx_news_sentiment_enrichment_article
    ON news_sentiment_enrichment (news_article_id);

COMMENT ON TABLE news_sentiment_enrichment IS 'Gemini grounded sentiment refinement for FinBERT-neutral articles';
