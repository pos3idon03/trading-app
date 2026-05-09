CREATE TABLE IF NOT EXISTS agent_analyses (
    id                  SERIAL PRIMARY KEY,
    symbol              VARCHAR NOT NULL,
    llm                 VARCHAR NOT NULL DEFAULT 'gpt-4o-mini',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    signal              JSONB,
    fundamental_report  TEXT,
    macro_report        TEXT,
    sentiment_report    TEXT,
    bias                VARCHAR,
    conviction_score    DOUBLE PRECISION,
    sentiment_score     DOUBLE PRECISION,
    duration_ms         INTEGER,
    status              VARCHAR NOT NULL DEFAULT 'pending',
    error_message       TEXT
);

CREATE INDEX IF NOT EXISTS ix_agent_analyses_symbol ON agent_analyses(symbol);
CREATE INDEX IF NOT EXISTS ix_agent_analyses_status ON agent_analyses(status);
CREATE INDEX IF NOT EXISTS ix_agent_analyses_created_at ON agent_analyses(created_at DESC);
