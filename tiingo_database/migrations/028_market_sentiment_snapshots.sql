CREATE TABLE IF NOT EXISTS market_sentiment_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    window_hours    INTEGER     NOT NULL DEFAULT 24,
    score           INTEGER     NOT NULL,
    article_count   INTEGER     NOT NULL DEFAULT 0,
    bullish_count   INTEGER     NOT NULL DEFAULT 0,
    bearish_count   INTEGER     NOT NULL DEFAULT 0,
    neutral_count   INTEGER     NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_market_sentiment_recorded
    ON market_sentiment_snapshots (recorded_at DESC);

COMMENT ON TABLE market_sentiment_snapshots IS 'Rolling watchlist market sentiment snapshots after news_sentiment jobs';
