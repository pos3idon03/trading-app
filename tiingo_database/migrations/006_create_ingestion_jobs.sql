CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_type        TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'pending',
    progress        INTEGER     NOT NULL DEFAULT 0,
    params          JSONB,
    result          JSONB,
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON ingestion_jobs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_type ON ingestion_jobs (job_type, created_at DESC);

COMMENT ON TABLE ingestion_jobs IS 'Persistent ingestion job tracking';
