CREATE TABLE IF NOT EXISTS api_usage_counters (
    bucket_type     TEXT        NOT NULL,
    bucket_start    TIMESTAMPTZ NOT NULL,
    request_count   INTEGER     NOT NULL DEFAULT 0,
    bytes_estimate  BIGINT      NOT NULL DEFAULT 0,
    PRIMARY KEY (bucket_type, bucket_start)
);

COMMENT ON TABLE api_usage_counters IS 'Hourly/daily Tiingo API usage for rate limiting';
