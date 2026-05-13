-- Migration 014: Trading strategies per asset with linked backtest results
CREATE TABLE IF NOT EXISTS trading_strategies (
    id         SERIAL      PRIMARY KEY,
    asset_id   INTEGER     NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    is_active  BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(asset_id)
);

CREATE INDEX IF NOT EXISTS idx_trading_strategies_asset ON trading_strategies (asset_id);

CREATE TABLE IF NOT EXISTS strategy_backtests (
    id          SERIAL      PRIMARY KEY,
    strategy_id INTEGER     NOT NULL REFERENCES trading_strategies(id) ON DELETE CASCADE,
    backtest_id INTEGER     NOT NULL REFERENCES backtest_results(id) ON DELETE CASCADE,
    added_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(strategy_id, backtest_id)
);

CREATE INDEX IF NOT EXISTS idx_strategy_backtests_strategy ON strategy_backtests (strategy_id);

COMMENT ON TABLE trading_strategies IS 'One strategy card per asset; aggregates MC, AI agent, financials and algo backtest results';
COMMENT ON TABLE strategy_backtests IS 'Many-to-many link between a trading strategy card and its attached backtest runs';
