-- Migration 019: Per-algo attachment signal timeframe
BEGIN;

ALTER TABLE strategy_backtests
    ADD COLUMN IF NOT EXISTS timeframe TEXT;

UPDATE strategy_backtests SET timeframe = '1d' WHERE timeframe IS NULL;

ALTER TABLE strategy_backtests
    ALTER COLUMN timeframe SET DEFAULT '1d',
    ALTER COLUMN timeframe SET NOT NULL;

COMMENT ON COLUMN strategy_backtests.timeframe IS
    'Signal evaluation timeframe for this algo attachment (set from backtest + Strategy)';

COMMIT;
