CREATE TABLE trading_deployments (
    id                      UUID PRIMARY KEY,
    model_id                UUID NOT NULL REFERENCES ml_models(id) ON DELETE RESTRICT,
    symbol                  TEXT NOT NULL,
    timeframe               TEXT NOT NULL DEFAULT '1d',
    status                  TEXT NOT NULL DEFAULT 'draft',
    trading_mode            TEXT NOT NULL DEFAULT 'paper',
    allocation_pct          NUMERIC(8, 4) NOT NULL DEFAULT 100,
    hyperparams_snapshot    JSONB NOT NULL DEFAULT '{}',
    last_evaluated_bar_time TIMESTAMPTZ,
    last_signal             TEXT,
    last_error              TEXT,
    activated_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trading_deployments_status ON trading_deployments (status);
CREATE INDEX idx_trading_deployments_symbol ON trading_deployments (symbol);
CREATE UNIQUE INDEX idx_trading_deployments_active_symbol
    ON trading_deployments (symbol, trading_mode)
    WHERE status = 'active';

CREATE TABLE execution_orders (
    id                UUID PRIMARY KEY,
    deployment_id     UUID NOT NULL REFERENCES trading_deployments(id) ON DELETE CASCADE,
    alpaca_order_id   TEXT UNIQUE,
    symbol            TEXT NOT NULL,
    side              TEXT NOT NULL,
    qty               NUMERIC(18, 6) NOT NULL,
    order_type        TEXT NOT NULL DEFAULT 'market',
    status            TEXT NOT NULL DEFAULT 'pending',
    signal            TEXT NOT NULL,
    bar_time          TIMESTAMPTZ NOT NULL,
    filled_avg_price  NUMERIC(18, 6),
    submitted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    filled_at         TIMESTAMPTZ,
    error_message     TEXT
);

CREATE INDEX idx_execution_orders_deployment ON execution_orders (deployment_id);
CREATE INDEX idx_execution_orders_submitted ON execution_orders (submitted_at DESC);
CREATE UNIQUE INDEX idx_execution_orders_deployment_bar
    ON execution_orders (deployment_id, bar_time);

CREATE TABLE execution_settings (
    id                    SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    kill_switch_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
    day_start_equity      NUMERIC(18, 2),
    day_start_date        DATE,
    orders_this_minute    INTEGER NOT NULL DEFAULT 0,
    minute_window_start   TIMESTAMPTZ,
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO execution_settings (id) VALUES (1);
