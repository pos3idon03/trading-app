-- Migration 013: Add buy-and-hold benchmark curve to backtest_results
ALTER TABLE backtest_results
    ADD COLUMN IF NOT EXISTS buy_hold_curve JSONB;

COMMENT ON COLUMN backtest_results.buy_hold_curve IS 'Buy-and-hold equity curve normalised to initial_capital for benchmark comparison';
