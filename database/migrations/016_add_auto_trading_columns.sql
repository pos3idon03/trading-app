-- Migration 016: Add auto-trading threshold configuration and position sizing to trading_strategies

-- Monte Carlo thresholds (single set: above threshold = BUY signal, below = SELL signal)
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS mc_min_prob_positive DOUBLE PRECISION;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS mc_max_drawdown      DOUBLE PRECISION;

-- AI Agent thresholds
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS ai_min_conviction DOUBLE PRECISION;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS ai_min_sentiment  DOUBLE PRECISION;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS ai_min_macro      DOUBLE PRECISION;

-- Signal combination mode across enabled sections: 'all' | 'majority' | 'any'
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS combination_mode VARCHAR(20) NOT NULL DEFAULT 'all';

-- Auto-trading lifecycle flags
-- auto_trading_enabled: asset appears on Auto-Trading dashboard
-- auto_trading_started: trading engine is actively running for this asset
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS auto_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS auto_trading_started BOOLEAN NOT NULL DEFAULT FALSE;

-- Position sizing (both nullable; if both NULL the system calculates dynamically)
-- max_amount_per_position takes priority when both are set
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS max_amount_per_position DOUBLE PRECISION;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS max_pct_of_capital      DOUBLE PRECISION;

CREATE INDEX IF NOT EXISTS idx_trading_strategies_auto_enabled
    ON trading_strategies (auto_trading_enabled)
    WHERE auto_trading_enabled = TRUE;

COMMENT ON COLUMN trading_strategies.mc_min_prob_positive    IS 'Min Prob. Positive Return to generate a BUY signal (0–1)';
COMMENT ON COLUMN trading_strategies.mc_max_drawdown         IS 'Max Mean Max Drawdown threshold; above this generates SELL signal (0–1)';
COMMENT ON COLUMN trading_strategies.ai_min_conviction       IS 'Min Conviction Score for a BUY signal (0–1)';
COMMENT ON COLUMN trading_strategies.ai_min_sentiment        IS 'Min Sentiment Score for a BUY signal (-1 to 1)';
COMMENT ON COLUMN trading_strategies.ai_min_macro            IS 'Min Macro Score for a BUY signal (-1 to 1)';
COMMENT ON COLUMN trading_strategies.combination_mode        IS 'How section signals combine: all | majority | any';
COMMENT ON COLUMN trading_strategies.auto_trading_enabled    IS 'Whether this asset is shown on the Auto-Trading dashboard';
COMMENT ON COLUMN trading_strategies.auto_trading_started    IS 'Whether the trading engine is actively running for this asset';
COMMENT ON COLUMN trading_strategies.max_amount_per_position IS 'Hard cap in dollars per position (takes priority over pct)';
COMMENT ON COLUMN trading_strategies.max_pct_of_capital      IS 'Max % of available uninvested capital per position (0–100)';
