ALTER TABLE backtest_runs
    ALTER COLUMN start_date TYPE TIMESTAMPTZ USING start_date::TIMESTAMPTZ,
    ALTER COLUMN end_date TYPE TIMESTAMPTZ USING end_date::TIMESTAMPTZ;

COMMENT ON COLUMN backtest_runs.start_date IS 'Backtest range start (UTC); supports intraday';
COMMENT ON COLUMN backtest_runs.end_date IS 'Backtest range end (UTC); supports intraday';
