CREATE TABLE IF NOT EXISTS backtest_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrument_id   INTEGER NOT NULL REFERENCES instruments(id) ON DELETE CASCADE,
    symbol          TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    params          JSONB NOT NULL DEFAULT '{}'::jsonb,
    timeframe       TEXT NOT NULL DEFAULT '1d',
    start_date      DATE,
    end_date        DATE,
    initial_cash    NUMERIC(18, 2) NOT NULL DEFAULT 10000,
    commission_bps  NUMERIC(10, 4) NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'pending',
    metrics         JSONB,
    equity_curve    JSONB,
    trades          JSONB,
    benchmark       JSONB,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_backtest_runs_symbol ON backtest_runs (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_runs_status ON backtest_runs (status, created_at DESC);

COMMENT ON TABLE backtest_runs IS 'Stored single-asset backtest runs and results';
