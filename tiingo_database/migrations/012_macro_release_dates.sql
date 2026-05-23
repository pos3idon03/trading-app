-- ALFRED initial-release dates for point-in-time macro joins in ML
ALTER TABLE macro_observations
    ADD COLUMN IF NOT EXISTS release_date DATE;

CREATE INDEX IF NOT EXISTS idx_macro_obs_release
    ON macro_observations (series_id, release_date);

COMMENT ON COLUMN macro_observations.release_date IS
    'First FRED/ALFRED vintage date when obs_date value became publicly known';
