-- ─────────────────────────────────────────────────────────────────────────────
-- Bootstrap: enable required extensions
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Run migration files in order
\i /docker-entrypoint-initdb.d/migrations/001_create_assets.sql
\i /docker-entrypoint-initdb.d/migrations/002_create_ohlcv.sql
\i /docker-entrypoint-initdb.d/migrations/003_create_fundamentals.sql
\i /docker-entrypoint-initdb.d/migrations/004_create_simulations.sql
\i /docker-entrypoint-initdb.d/migrations/005_create_backtest_results.sql
