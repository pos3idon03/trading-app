TRUNCATE market_sentiment_snapshots;

ALTER TABLE market_sentiment_snapshots
    ALTER COLUMN score TYPE DOUBLE PRECISION;
