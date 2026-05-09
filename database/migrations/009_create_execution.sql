-- Phase 6: Execution and risk management

CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL PRIMARY KEY,
    symbol          VARCHAR NOT NULL,
    side            VARCHAR NOT NULL,
    qty             DOUBLE PRECISION NOT NULL,
    order_type      VARCHAR NOT NULL DEFAULT 'market',
    limit_price     DOUBLE PRECISION,
    stop_price      DOUBLE PRECISION,
    status          VARCHAR NOT NULL DEFAULT 'pending',
    alpaca_order_id VARCHAR,
    filled_price    DOUBLE PRECISION,
    filled_qty      DOUBLE PRECISION,
    filled_at       TIMESTAMPTZ,
    signal_id       INTEGER REFERENCES trading_signals(id),
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_symbol ON orders (symbol, created_at DESC);
CREATE INDEX idx_orders_status ON orders (status);

CREATE TABLE IF NOT EXISTS risk_events (
    id          SERIAL PRIMARY KEY,
    event_type  VARCHAR NOT NULL,
    severity    VARCHAR NOT NULL DEFAULT 'warning',
    symbol      VARCHAR,
    description TEXT NOT NULL,
    details     JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_risk_events_type ON risk_events (event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id              SERIAL PRIMARY KEY,
    equity          DOUBLE PRECISION NOT NULL,
    cash            DOUBLE PRECISION NOT NULL,
    buying_power    DOUBLE PRECISION NOT NULL,
    daily_pnl       DOUBLE PRECISION,
    daily_pnl_pct   DOUBLE PRECISION,
    total_positions INTEGER NOT NULL DEFAULT 0,
    positions       JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_portfolio_snapshots_time ON portfolio_snapshots (created_at DESC);
