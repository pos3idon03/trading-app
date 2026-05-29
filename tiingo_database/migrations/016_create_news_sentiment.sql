CREATE TABLE IF NOT EXISTS news_sentiment (
    id                  BIGSERIAL PRIMARY KEY,
    news_article_id     BIGINT      NOT NULL REFERENCES news_articles (id) ON DELETE CASCADE,
    model_name          TEXT        NOT NULL,
    model_version       TEXT        NOT NULL,
    label               TEXT        NOT NULL,
    score_positive      DOUBLE PRECISION NOT NULL,
    score_negative      DOUBLE PRECISION NOT NULL,
    score_neutral       DOUBLE PRECISION NOT NULL,
    confidence          DOUBLE PRECISION NOT NULL,
    text_hash           TEXT        NOT NULL,
    scored_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    error               TEXT,
    UNIQUE (news_article_id, model_name, model_version)
);

CREATE INDEX IF NOT EXISTS idx_news_sentiment_article ON news_sentiment (news_article_id);
CREATE INDEX IF NOT EXISTS idx_news_sentiment_model ON news_sentiment (model_name, model_version);

CREATE TABLE IF NOT EXISTS news_sentiment_daily (
    id                  BIGSERIAL PRIMARY KEY,
    symbol              TEXT        NOT NULL,
    date                DATE        NOT NULL,
    model_name          TEXT        NOT NULL,
    model_version       TEXT        NOT NULL,
    article_count       INTEGER     NOT NULL DEFAULT 0,
    avg_score           DOUBLE PRECISION NOT NULL DEFAULT 0,
    bullish_pct         DOUBLE PRECISION NOT NULL DEFAULT 0,
    bearish_pct         DOUBLE PRECISION NOT NULL DEFAULT 0,
    UNIQUE (symbol, date, model_name, model_version)
);

CREATE INDEX IF NOT EXISTS idx_news_sentiment_daily_symbol_date
    ON news_sentiment_daily (symbol, date DESC);

COMMENT ON TABLE news_sentiment IS 'FinBERT sentiment scores per news article';
COMMENT ON TABLE news_sentiment_daily IS 'Daily per-symbol sentiment rollups for ML and trading';
