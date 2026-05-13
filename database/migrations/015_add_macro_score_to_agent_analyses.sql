-- Add macro_score column to agent_analyses table.
-- This stores the numeric macro environment score produced by the macro agent
-- (-1.0 = very bearish, +1.0 = very bullish) as a dedicated column, matching
-- the existing conviction_score and sentiment_score columns.

ALTER TABLE agent_analyses
    ADD COLUMN IF NOT EXISTS macro_score DOUBLE PRECISION;
