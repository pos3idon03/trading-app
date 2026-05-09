ALTER TABLE agent_analyses
    ADD COLUMN IF NOT EXISTS provider_used VARCHAR;
