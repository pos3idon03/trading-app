ALTER TABLE backtest_runs
    ADD COLUMN IF NOT EXISTS universe_id INTEGER REFERENCES universe_definitions(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS symbol_list JSONB;

COMMENT ON COLUMN backtest_runs.universe_id IS 'Optional universe for multi-symbol backtests';
COMMENT ON COLUMN backtest_runs.symbol_list IS 'Explicit symbol list when not using universe_id';
