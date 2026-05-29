DROP INDEX IF EXISTS idx_trading_deployments_active_symbol;

ALTER TABLE execution_orders
    ADD COLUMN IF NOT EXISTS filled_qty NUMERIC(18, 6);
