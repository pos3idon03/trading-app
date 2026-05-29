ALTER TABLE trading_deployments
    ADD COLUMN IF NOT EXISTS peak_strategy_profit_pct NUMERIC(12, 6);
