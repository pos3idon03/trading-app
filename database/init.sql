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
\i /docker-entrypoint-initdb.d/migrations/006_create_optimization_results.sql
\i /docker-entrypoint-initdb.d/migrations/007_create_agent_analyses.sql
\i /docker-entrypoint-initdb.d/migrations/008_create_live_trading.sql
\i /docker-entrypoint-initdb.d/migrations/009_create_execution.sql
\i /docker-entrypoint-initdb.d/migrations/010_add_provider_used_to_agent_analyses.sql
\i /docker-entrypoint-initdb.d/migrations/011_add_asset_id_fk.sql
\i /docker-entrypoint-initdb.d/migrations/012_create_company_profiles.sql
