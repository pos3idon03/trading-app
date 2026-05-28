-- Tiingo ingestion database bootstrap
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

\i /docker-entrypoint-initdb.d/migrations/001_create_instruments.sql
\i /docker-entrypoint-initdb.d/migrations/002_create_ohlcv.sql
\i /docker-entrypoint-initdb.d/migrations/003_create_news.sql
\i /docker-entrypoint-initdb.d/migrations/004_create_fundamentals.sql
\i /docker-entrypoint-initdb.d/migrations/005_create_macro.sql
\i /docker-entrypoint-initdb.d/migrations/006_create_ingestion_jobs.sql
\i /docker-entrypoint-initdb.d/migrations/007_create_api_usage.sql
\i /docker-entrypoint-initdb.d/migrations/008_add_ohlcv_corporate_fields.sql
\i /docker-entrypoint-initdb.d/migrations/009_create_backtest_runs.sql
\i /docker-entrypoint-initdb.d/migrations/011_create_ml_models.sql
\i /docker-entrypoint-initdb.d/migrations/012_macro_release_dates.sql
\i /docker-entrypoint-initdb.d/migrations/013_create_trading_execution.sql
\i /docker-entrypoint-initdb.d/migrations/014_execution_evaluations.sql
