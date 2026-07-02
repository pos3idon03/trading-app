ALTER TABLE trading_deployments
    ADD COLUMN IF NOT EXISTS last_evaluated_at TIMESTAMPTZ;

UPDATE trading_deployments d
SET last_evaluated_at = sub.max_created
FROM (
    SELECT deployment_id, MAX(created_at) AS max_created
    FROM execution_evaluations
    GROUP BY deployment_id
) sub
WHERE d.id = sub.deployment_id;
