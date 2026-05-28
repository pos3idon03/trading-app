# Foundation model backtesting

Zero-shot walk-forward backtests using [TimesFM](https://research.google/blog/a-decoder-only-foundation-model-for-time-series-forecasting/) and [Chronos](https://github.com/amazon-science/chronos-forecasting). This modality is **separate from ML** (no sklearn training, no Trading Models inventory).

## Enable

1. Install optional dependencies:

   ```bash
   cd tiingo_backend
   pip install -r requirements.txt -r requirements-foundation.txt
   ```

2. Install TimesFM from source (until a PyPI release ships 2.5):

   ```bash
   git clone https://github.com/google-research/timesfm.git
   cd timesfm && pip install -e ".[torch]"
   ```

3. Set environment variables (e.g. in `.env`):

   ```env
   FOUNDATION_MODELS_ENABLED=true
   FOUNDATION_DEVICE=cpu
   # FOUNDATION_DEVICE=cuda
   # FOUNDATION_MODEL_CACHE_DIR=/path/to/hf/cache
   ```

4. Restart the API and ARQ worker so both load the new settings.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/backtest/foundation/models` | Catalog (503 if disabled) |
| `POST` | `/api/v1/backtest/foundation/preview` | Async forecast preview (202) |
| `POST` | `/api/v1/backtest/foundation/run` | Async walk-forward backtest (202) |
| `GET` | `/api/v1/backtest/foundation/{run_id}/results` | Results + `foundation_summary` |

Job types: `foundation_preview`, `foundation_backtest`.

## UI

Sidebar → **Backtesting** → **Foundation Models** (`/backtesting/foundation`).

## Runtime notes

- Each decision bar runs one model inference (slow on CPU; GPU recommended for long histories).
- First `context_length` bars are warmup (`hold` only).
- Checkpoints download from Hugging Face on first use (~400MB–1GB per model).
- CI/default installs keep `FOUNDATION_MODELS_ENABLED=false` so unit tests do not require `torch`.

## Docker / CI

- Use a optional image stage or profile that adds `requirements-foundation.txt` and TimesFM source install.
- Do not enable foundation jobs in CI unless GPU runners and model cache are available.
