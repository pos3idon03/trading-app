ALTER TABLE execution_evaluations
    ADD COLUMN IF NOT EXISTS explainability JSONB NOT NULL DEFAULT '{}';

ALTER TABLE trading_deployments
    ADD COLUMN IF NOT EXISTS last_explainability JSONB NOT NULL DEFAULT '{}';
