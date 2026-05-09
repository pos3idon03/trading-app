-- Migration 005: Backtest run metadata and metrics
CREATE TABLE IF NOT EXISTS backtest_results (
    id              SERIAL PRIMARY KEY,
    asset_id        INTEGER      NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    strategy_name   TEXT         NOT NULL,
    timeframe       TEXT         NOT NULL,
    start_date      TIMESTAMPTZ  NOT NULL,
    end_date        TIMESTAMPTZ  NOT NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    -- Strategy hyperparameters
    params          JSONB        NOT NULL,
    -- Performance metrics
    sharpe_ratio    DOUBLE PRECISION,
    sortino_ratio   DOUBLE PRECISION,
    max_drawdown    DOUBLE PRECISION,
    win_rate        DOUBLE PRECISION,
    profit_factor   DOUBLE PRECISION,
    total_return    DOUBLE PRECISION,
    annualized_return DOUBLE PRECISION,
    num_trades      INTEGER,
    -- Full equity curve and trade log compressed as JSONB
    equity_curve    JSONB,
    trade_log       JSONB,
    duration_ms     INTEGER,
    status          TEXT         NOT NULL DEFAULT 'pending',
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_bt_asset_strategy ON backtest_results (asset_id, strategy_name, created_at DESC);

COMMENT ON TABLE backtest_results IS 'Backtesting runs with full metrics and equity curves';
