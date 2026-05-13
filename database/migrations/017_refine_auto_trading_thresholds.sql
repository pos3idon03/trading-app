-- Migration 017: Split MC/AI thresholds into separate BUY/SELL values, add algo_timeframe

-- Monte Carlo: rename single threshold to buy, add sell, drop drawdown
ALTER TABLE trading_strategies RENAME COLUMN mc_min_prob_positive TO mc_buy_prob_positive;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS mc_sell_prob_positive DOUBLE PRECISION;
ALTER TABLE trading_strategies DROP COLUMN IF EXISTS mc_max_drawdown;

-- AI Agent: rename min -> buy, add sell columns
ALTER TABLE trading_strategies RENAME COLUMN ai_min_conviction TO ai_buy_conviction;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS ai_sell_conviction DOUBLE PRECISION;
ALTER TABLE trading_strategies RENAME COLUMN ai_min_sentiment  TO ai_buy_sentiment;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS ai_sell_sentiment  DOUBLE PRECISION;
ALTER TABLE trading_strategies RENAME COLUMN ai_min_macro      TO ai_buy_macro;
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS ai_sell_macro      DOUBLE PRECISION;

-- Algo strategies: configurable trading timeframe
ALTER TABLE trading_strategies ADD COLUMN IF NOT EXISTS algo_timeframe VARCHAR(10) NOT NULL DEFAULT '1d';

COMMENT ON COLUMN trading_strategies.mc_buy_prob_positive   IS 'BUY when Prob. Positive Return is above this value (0–1)';
COMMENT ON COLUMN trading_strategies.mc_sell_prob_positive  IS 'SELL when Prob. Positive Return falls below this value (0–1)';
COMMENT ON COLUMN trading_strategies.ai_buy_conviction      IS 'BUY when Conviction Score is above this value (0–1)';
COMMENT ON COLUMN trading_strategies.ai_sell_conviction     IS 'SELL when Conviction Score falls below this value (0–1)';
COMMENT ON COLUMN trading_strategies.ai_buy_sentiment       IS 'BUY when Sentiment Score is above this value (-1 to 1)';
COMMENT ON COLUMN trading_strategies.ai_sell_sentiment      IS 'SELL when Sentiment Score falls below this value (-1 to 1)';
COMMENT ON COLUMN trading_strategies.ai_buy_macro           IS 'BUY when Macro Score is above this value (-1 to 1)';
COMMENT ON COLUMN trading_strategies.ai_sell_macro          IS 'SELL when Macro Score falls below this value (-1 to 1)';
COMMENT ON COLUMN trading_strategies.algo_timeframe         IS 'Timeframe for algo strategy signals: 1m/5m/15m/30m/1h/3h/1d/1w';
