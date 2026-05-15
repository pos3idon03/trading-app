-- Migration 018: Make backtest and optimization runs stateless.
-- Converts strategy_backtests to store strategy definitions directly,
-- then drops the now-unused backtest_results and optimization_runs tables.

BEGIN;

-- 1. Add new definition columns to strategy_backtests
ALTER TABLE strategy_backtests
    ADD COLUMN IF NOT EXISTS strategy_name TEXT,
    ADD COLUMN IF NOT EXISTS params        JSONB;

-- 2. Backfill from backtest_results for any existing linked rows
UPDATE strategy_backtests sb
SET strategy_name = br.strategy_name,
    params        = br.params
FROM backtest_results br
WHERE sb.backtest_id = br.id;

-- 3. Remove orphaned rows that had no matching backtest_result
DELETE FROM strategy_backtests WHERE strategy_name IS NULL;

-- 4. Enforce NOT NULL now that all rows are populated
ALTER TABLE strategy_backtests
    ALTER COLUMN strategy_name SET NOT NULL;

-- 5. Drop old unique constraint and FK column
ALTER TABLE strategy_backtests
    DROP CONSTRAINT IF EXISTS strategy_backtests_strategy_id_backtest_id_key,
    DROP COLUMN IF EXISTS backtest_id;

-- 6. Add new uniqueness: one entry per strategy card per strategy name
ALTER TABLE strategy_backtests
    ADD CONSTRAINT strategy_backtests_strategy_id_strategy_name_key
    UNIQUE (strategy_id, strategy_name);

-- 7. Drop the now-unused tables
DROP TABLE IF EXISTS backtest_results;
DROP TABLE IF EXISTS optimization_runs;

COMMIT;
