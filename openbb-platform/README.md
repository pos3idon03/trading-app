# OpenBB Platform Service

Containerised [OpenBB Platform](https://docs.openbb.co/odp/python) (`v4.7.1`) running as part of the trading-app docker-compose stack.

## What it does

Exposes the OpenBB REST API on **port 6900** with 17 data providers (yfinance, FRED, FMP, SEC, IMF, OECD, BLS, Tiingo, Intrinio, Benzinga, etc.) so that other services (backend, frontend, notebooks) can fetch market and macro data via a single HTTP endpoint.

## Run

From the repo root:

```bash
docker compose up -d openbb
```

Then visit:

- Interactive API docs: http://localhost:6900/docs
- OpenAPI spec: http://localhost:6900/openapi.json
- API root (used as healthcheck): http://localhost:6900/
- Example endpoint: http://localhost:6900/api/v1/equity/price/historical?symbol=AAPL&provider=yfinance

## API keys / user settings

Credentials are sourced **exclusively from the repo-root `.env`** (no secrets in this folder). At container start, [entrypoint.sh](entrypoint.sh) runs [seed_credentials.py](seed_credentials.py) which:

1. Reads recognised env vars (see the mapping table below)
2. Merges them into `/root/.openbb_platform/user_settings.json` (preserving any manually-added settings)
3. Then execs `openbb-api`

The user-settings file lives on the named docker volume `openbb_data`, so it persists across rebuilds.

### .env to OpenBB credential mapping

| `.env` variable | OpenBB credential |
|---|---|
| `FMP_API_KEY` | `fmp_api_key` |
| `FRED_API_KEY` | `fred_api_key` |
| `POLYGON_API_KEY` | `polygon_api_key` |
| `ALPACA_API_KEY` | `alpaca_api_key` |
| `OPENAI_API_KEY` | `openai_api_key` |
| `GEMINI_API_KEY` | `gemini_api_key` |
| `NEWSAPI_KEY` | `newsapi_key` |
| `BENZINGA_API_KEY` | `benzinga_api_key` |
| `BLS_API_KEY` | `bls_api_key` |
| `EIA_API_KEY` | `eia_api_key` |
| `INTRINIO_API_KEY` | `intrinio_api_key` |
| `TIINGO_TOKEN` | `tiingo_token` |
| `TRADINGECONOMICS_API_KEY` | `tradingeconomics_api_key` |
| `CFTC_APP_TOKEN` | `cftc_app_token` |
| `CONGRESS_GOV_API_KEY` | `congress_gov_api_key` |
| `ECONDB_API_KEY` | `econdb_api_key` |

To add a new key: append it to the repo-root `.env` then `docker compose restart openbb`. The seed script picks it up on next start.

### Verify which credentials are loaded

```bash
docker compose logs openbb | grep "Seeded"
# or
docker compose exec openbb python -c "import json; print(sorted(json.load(open('/root/.openbb_platform/user_settings.json'))['credentials']))"
```

## Files

- [Dockerfile](Dockerfile) — `python:3.12-slim` + `pip install openbb` + `openbb-build`
- [requirements.txt](requirements.txt) — pins `openbb==4.7.1`
- [entrypoint.sh](entrypoint.sh) — seeds credentials then `exec openbb-api`
- [seed_credentials.py](seed_credentials.py) — maps `.env` vars to `user_settings.json`
- [tests/test_seed_credentials.py](tests/test_seed_credentials.py) — 12 unit tests for the seed logic
- [.dockerignore](.dockerignore)

## Rebuild after pinning a new version

```bash
docker compose build --no-cache openbb
docker compose up -d openbb
```
