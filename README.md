# Trading App

AI-driven automated trading platform with live data feeds, quantitative modelling, and multi-agent intelligence.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy (async) |
| Database | TimescaleDB (Postgres 16) + pgvector |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Quant Engine | NumPy, SciPy, pandas, vectorbt |
| AI Agents | LangChain, LiteLLM |
| Market Data | Polygon.io, Alpaca, yfinance, FMP |
| Execution | Alpaca |
| Infrastructure | Docker Compose |

## Getting Started

### Prerequisites

- Docker >= 24.0
- Docker Compose >= 2.20

### Setup

```bash
# 1. Clone and enter the project
cd trading-app

# 2. Copy and fill in credentials
cp .env.example .env
# Edit .env with your API keys

# 3. Start all services
docker compose up --build -d

# Ingestion UI: http://localhost:5174
# Tiingo API docs: http://localhost:8002/docs
# Database: localhost:5433
```

Configure in `.env`: `TIINGO_API_KEY`, `FRED_API_KEY`, `TIINGO_FUNDAMENTALS_TIER` (`dow30` or `addon_*`).

### Running Tests

```bash
docker compose exec tiingo_backend pytest tests/ -v

# Or locally
cd tiingo_backend && pip install -r requirements.txt && pytest tests/ -v
```

## Project Structure

```
trading-app/
├── tiingo_backend/             # FastAPI ingestion API + ARQ worker
├── tiingo_frontend/            # React + TypeScript ingestion UI
├── tiingo_database/            # SQL migrations and init scripts
└── docker-compose.yml
```

## Development Phases

| Phase | Status | Description |
|---|---|---|
| 1 | Complete | Data Infrastructure & Foundation |
| 2 | Complete | Quantitative Engine (Vasicek + Monte Carlo) |
| 3 | Complete | Backtesting Framework |
| 4 | Complete | Multi-Agent AI Integration |
| 5 | Complete | Live Technical Indicators & Signal Generation |
| 6 | Complete | Live Execution & Risk Management |

## API Endpoints

### Data Ingestion
- `POST /api/v1/data/ingest` — Trigger data ingestion for asset(s)
- `GET /api/v1/data/ohlcv/{asset_id}` — Retrieve stored OHLCV data
- `GET /api/v1/data/status` — Ingestion pipeline health

### Simulation
- `POST /api/v1/simulation/calibrate/{asset_id}` — Calibrate Vasicek model
- `POST /api/v1/simulation/run` — Run Monte Carlo simulation
- `GET /api/v1/simulation/{sim_id}` — Retrieve simulation results

### Backtesting
- `POST /api/v1/backtest/run` — Execute backtest (historical or simulated data via `simulation_id`)
- `GET /api/v1/backtest/{id}/results` — Retrieve backtest metrics
- `POST /api/v1/backtest/optimize` — Walk-forward parameter optimization
- `GET /api/v1/backtest/{id}/optimization` — Retrieve optimization results

### AI Agents
- `POST /api/v1/agents/analyze` — Run multi-agent research crew (fundamental + macro + sentiment → signal)
- `GET /api/v1/agents/{id}` — Retrieve stored agent analysis and trading signal

### Live Trading (Phase 5)
- `POST /api/v1/live/start` — Start Alpaca WebSocket stream for symbol(s)
- `POST /api/v1/live/stop` — Stop streaming
- `GET /api/v1/live/status` — Stream health and connected symbols
- `GET /api/v1/live/indicators/{symbol}` — Latest technical indicators (RSI, MACD, BB, VWAP)
- `GET /api/v1/live/signals/{symbol}` — Latest aggregated trading signal
- `GET /api/v1/live/signals` — Signal history
- `WebSocket /api/v1/live/ws` — Real-time data push to frontend

### Execution & Risk Management (Phase 6)
- `POST /api/v1/execution/enable` — Enable paper trading execution
- `POST /api/v1/execution/disable` — Activate kill switch (halt all trading)
- `GET /api/v1/execution/status` — Execution status and risk state
- `GET /api/v1/execution/orders` — Order history
- `GET /api/v1/execution/portfolio` — Current portfolio state (positions, P&L)
- `GET /api/v1/execution/risk/config` — Current risk limits
- `PUT /api/v1/execution/risk/config` — Update risk limits
- `GET /api/v1/execution/risk/events` — Risk event log