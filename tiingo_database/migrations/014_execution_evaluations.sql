ALTER TABLE trading_deployments
    ADD COLUMN IF NOT EXISTS last_blocked_reason TEXT,
    ADD COLUMN IF NOT EXISTS last_probability NUMERIC(8, 6),
    ADD COLUMN IF NOT EXISTS last_outcome TEXT;

CREATE TABLE execution_evaluations (
    id                UUID PRIMARY KEY,
    deployment_id     UUID NOT NULL REFERENCES trading_deployments(id) ON DELETE CASCADE,
    bar_time          TIMESTAMPTZ NOT NULL,
    signal            TEXT NOT NULL,
    probability       NUMERIC(8, 6),
    buy_threshold     NUMERIC(8, 6),
    sell_threshold    NUMERIC(8, 6),
    position_side     TEXT,
    order_intent_side TEXT,
    order_qty         NUMERIC(18, 6),
    outcome           TEXT NOT NULL,
    blocked_reason    TEXT,
    order_id          UUID REFERENCES execution_orders(id) ON DELETE SET NULL,
    warnings          JSONB NOT NULL DEFAULT '[]',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_execution_evaluations_deployment ON execution_evaluations (deployment_id);
CREATE INDEX idx_execution_evaluations_created ON execution_evaluations (created_at DESC);
CREATE INDEX idx_execution_evaluations_symbol_time ON execution_evaluations (deployment_id, bar_time DESC);
