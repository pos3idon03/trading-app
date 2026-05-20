# Quantitative Engine

Monte Carlo (MC) price models, calibration, walk-forward backtesting, and signal generation for the trading app. All price models share a **compound Poisson jump** layer (`jump_diffusion.py`) fitted from historical log-returns.

Trading signals are **not** hard-coded inside each SDE. Every model produces a **probability of a positive one-step return** (`prob_positive_return`). The backtest engine (`mc_backtest.py`) maps that probability to **BUY**, **SELL**, or **FLAT** using configurable thresholds and position filters.

---

## Architecture

```
OHLCV prices
    → calibration_service.calibrate_from_prices()
        → VasicekParams + MertonParams + OuDeviationParams + JumpParams
    → run_single_step_prob() / dispatch_mc_simulation()
        → 1-step (or multi-step) MC paths
        → prob_positive_return
    → thresholds + filters (mc_backtest / mc_combo)
        → BUY | SELL | FLAT
    → simulate_portfolio() (next-bar open execution)
```

| Module | Role |
|--------|------|
| `vasicek.py` | Estimate mean-reversion parameters on price levels |
| `jump_diffusion.py` | Detect jumps, fit Poisson + log-normal jump sizes |
| `monte_carlo.py` | Vasicek + jump path simulation (additive) |
| `merton_jump_diffusion.py` | GBM + multiplicative jumps |
| `ou_deviation.py` | OU on log(price / rolling MA) + multiplicative jumps |
| `blended_prob.py` | ADX-weighted mix of Merton + OU probabilities |
| `regime_weight.py` | ADX calculation and trend/reversion weight |
| `calibration_service.py` | Fit all param sets from a price window |
| `simulation_runner.py` | Dispatch multi-step simulation by `model_type` |
| `mc_backtest.py` | Walk-forward backtest and signal generation |
| `mc_combo.py` | Combine MC stance with classic algo strategies |
| `mc_intraday.py` | Intraday calibration lookback defaults |

Optimizers (`mc_backtest_optimizer.py`, `mc_simulation_optimizer.py`, job runners) search threshold/path settings; they do not define new SDEs.

---

## Shared: Jump Process

**File:** `jump_diffusion.py`

Fitted once per calibration window from log-returns and reused by every model.

### Parameters (`JumpParams`)

| Parameter | Meaning |
|-----------|---------|
| `lambda_up` | Poisson rate of upward jumps (events per year-fraction `dt`) |
| `lambda_down` | Poisson rate of downward jumps |
| `up.mu`, `up.sigma` | Log-normal parameters for upward jump magnitudes |
| `down.mu`, `down.sigma` | Log-normal parameters for downward jump magnitudes |
| `ci_up`, `ci_down` | Optional 95% confidence intervals on jump log-magnitudes |

### Calibration

1. **Detect jumps:** z-score of each log-return; `|z| > threshold_sigma` (default **3.0**) classifies a jump.
2. **Intensity:** `lambda = count(jumps) / (n_observations * dt)`.
3. **Size distribution:** log-normal fit on `|jump return|` (up) or absolute down-jump magnitudes.

### Simulation

Each time step draws `N ~ Poisson(λ * dt)` jumps; each jump size is `LogNormal(μ, σ)`, summed with sign ±1. Vasicek uses **additive** jumps on price; Merton and OU use **multiplicative** jumps (`S_t * jump_size`).

---

## Model 1: Vasicek + Jump

**Files:** `vasicek.py`, `monte_carlo.py`  
**`model_type`:** `"vasicek"` (default)

### SDE (Euler–Maruyama, additive)

```
dS_t = k(θ_t - S_t) dt + σ dW_t + dJ_up + dJ_down
θ_t  = θ_0 * exp(μ * t * dt)    # μ = 0 → static long-term mean
```

### Parameters (`VasicekParams`)

| Parameter | Meaning |
|-----------|---------|
| `k` | Mean reversion speed |
| `theta` | Long-term mean level θ₀ |
| `sigma` | Diffusion (volatility of innovations) |
| `mu` | Drift of the mean-reversion target; `θ_t = θ_0 * e^(μ t dt)` |
| `r_squared` | OLS fit quality (internal) |

### Calibration (`estimate_mean_reversion_params`)

Discrete regression on price levels:

```
ΔS = α + β S(t)   →   k = -β/dt,  θ = α/(k·dt),  σ = std(residuals)/√dt
μ  = mean(log returns) / dt
```

Requires at least **30** observations.

### Signal metric

`run_simulation(..., steps=1)` → `stats.prob_positive_return`:

```
prob_positive_return = mean( (S_T - s0) / s0 > 0 ) over MC paths
```

One-step forward distribution from current close `s0`.

---

## Model 2: Merton Jump-Diffusion

**File:** `merton_jump_diffusion.py`  
**`model_type`:** `"merton"`

### SDE (multiplicative)

```
dS_t = μ S_t dt + σ S_t dW_t + S_t dJ_up + S_t dJ_down
S_{t+1} = max(S_t + μ S_t dt + σ S_t dW_t + jump terms, 0)
```

### Parameters (`MertonParams`)

| Parameter | Meaning |
|-----------|---------|
| `mu` | Annualized drift: `mean(log_returns) / dt` |
| `sigma` | Annualized volatility: `std(log_returns) / √dt` |

Plus shared `JumpParams` (multiplicative application).

### Calibration

From the same log-return series as jumps (`_calibrate_merton_params` in `calibration_service.py`). No separate price-level regression.

### Signal metric

Same as Vasicek: 1-step MC → fraction of paths with terminal price above `s0`. Stored as `prob_trend` when used inside the blended model.

---

## Model 3: OU Deviation (mean reversion to MA)

**File:** `ou_deviation.py`  
**`model_type`:** `"ou_deviation"`

Mean-reversion on **log deviation from a rolling moving average**, not on raw price.

### State variable

```
X_t = log(S_t / MA_t)     MA_t = rolling mean of close (window = ma_window)
```

### SDE on deviation (then map back to price)

```
dX_t = κ (θ - X_t) dt + σ dW_t
S_{t+1} = MA_level * exp(X_{t+1}) + multiplicative price jumps
```

`MA_level` is held **fixed** over the simulation horizon (last MA at calibration).

### Parameters (`OuDeviationParams`)

| Parameter | Meaning |
|-----------|---------|
| `kappa` | Mean reversion speed on `X` |
| `theta` | Long-run mean of log deviation |
| `sigma` | Volatility of `X` |
| `ma_window` | Rolling MA length (default **20**) |
| `ma_level` | MA value at end of calibration window |
| `x0` | Current `log(s0 / ma_level)` |

### Calibration

OLS on valid `X` series: `ΔX = α + β X(t)` → `κ = -β/dt`, `θ = α/(κ·dt)`, `σ = std(residuals)/√dt`. Needs **30+** deviation observations (so effective history ≥ `ma_window` + 30).

### Signal metric

`run_single_step_ou_prob` / 1-step `run_ou_deviation_simulation` → `prob_positive_return`. Stored as `prob_reversion` in blended mode.

---

## Model 4: Blended (regime-weighted)

**Files:** `blended_prob.py`, `regime_weight.py`  
**`model_type`:** `"blended"`

Combines **trend** (Merton) and **reversion** (OU deviation) probabilities using **ADX** as a regime indicator.

### Effective probability

```
w_trend = trend_weight_from_adx(adx, adx_low=15, adx_high=25)   # clipped to [0, 1]
p_trend = Merton 1-step prob_positive_return
p_rev   = OU     1-step prob_positive_return
p_eff   = w_trend * p_trend + (1 - w_trend) * p_rev
```

| ADX | `w_trend` | Interpretation |
|-----|-----------|----------------|
| ≤ 15 | 0 | Full weight on OU reversion |
| ≥ 25 | 1 | Full weight on Merton trend |
| Between | Linear interpolation | Mixed regime |

`adx_trend_threshold` in backtest config maps to `adx_high` (default **25**). Low bound is fixed at **15** in `run_blended_step_prob`.

### Extra config (`McBacktestConfig`)

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `adx_period` | 14 | ADX lookback on OHLCV |
| `adx_trend_threshold` | 25.0 | Upper ADX bound for full trend weight |

Blended calibration always fits **both** Merton and OU (+ jumps) in `calibrate_from_prices`.

---

## Calibration (`calibration_service.py`)

`calibrate_from_prices(prices, timeframe, start, end, ou_ma_window=20)` returns `CalibratedModelParams`:

- `vasicek`, `merton`, `ou_deviation`, `jumps`
- `last_price` → simulation start `s0`
- `num_observations`, `calibration_start`, `calibration_end`

`dt` converts bar size to a **fraction of one trading year** (252×6.5h for intraday; `1/252` for daily).

Walk-forward backtest re-calibrates on a rolling window per bar: `calibration_lookback_days` of history ending at each eval bar (minimum **30** bars; OU/blended require **30 + ou_ma_window**).

---

## Buy and Sell Signals

Signals are generated in **`mc_backtest.py`** (and **`mc_combo.py`** when combo mode is on). Models only supply `prob` (and optional `prob_trend`, `prob_reversion`, `regime_weight`).

### Step 1: One-step probability per bar

For each evaluation bar:

1. Slice OHLCV from `bar_time - calibration_lookback_days` to `bar_time`.
2. `calibrate_from_prices(...)` on closes.
3. `run_single_step_prob(...)` with `num_paths` parallel paths.
4. Optional **smoothing:** moving average over `prob_smoothing_bars` → `effective_prob`.

### Step 2: Threshold mapping (`evaluate_mc_signal`)

User thresholds: `buy_threshold`, `sell_threshold` (probabilities in **[0, 1]**).

| Position | Condition | Action |
|----------|-----------|--------|
| Flat | `prob >= buy_threshold` | **BUY** |
| Flat | else | **FLAT** |
| Long | `prob < sell_threshold` | **SELL** |
| Long | else | **FLAT** (hold) |

Hysteresis: typically `buy_threshold > sell_threshold` so the middle band avoids churn.

### Step 3: Entry filters (`_resolve_filtered_action`)

Applied to `effective_prob` in MC-only mode (and analogously in combo via `position_series_to_actions`):

| Config | Default | Effect |
|--------|---------|--------|
| `entry_confirmation_bars` | 1 | BUY only after N consecutive bars with `prob >= buy_threshold` |
| `cooldown_bars` | 0 | After SELL, block new BUY for N bars |
| `min_hold_bars` | 0 | Block SELL until position held N bars |
| `prob_smoothing_bars` | 0 | SMA of raw prob before threshold check |

### Step 4: Execution

`simulate_portfolio`: long-only, all-in. Signal on bar *i* executes at **open of bar i+1** with fee `0.001` default.

### Suggested thresholds

`compute_prob_distribution_stats` on the walk-forward `signal_log`:

- Suggested buy ≈ **75th percentile** of observed probs  
- Suggested sell ≈ **25th percentile**  
- Minimum gap **0.03** between buy and sell  

### Zone stats

`compute_prob_zone_stats` reports % of bars in:

- **Entry zone:** `prob >= buy_threshold`
- **Exit zone:** `prob < sell_threshold`
- **Middle zone:** `sell_threshold <= prob < buy_threshold`

---

## Combo mode (`mc_combo.py`)

When `combo_enabled` and `algo_strategies` are set, MC does not drive actions alone.

1. **`prob_to_stance`:** `prob >= buy` → Buy; `prob < sell` → Sell; else Neutral (no position-state hysteresis at stance level).
2. **Algo legs:** classic strategies (RSI, MACD, etc.) on their timeframes, aligned to the execution timeframe.
3. **`combine_stances`:** weighted vote (`combination_mode`: `and` / `or` / weighted, `threshold`, `mc_leg_weight`).
4. **`position_series_to_actions`:** same confirmation / cooldown / min-hold filters on the **combined** long/flat series.

---

## Multi-step simulation (UI forward paths)

**File:** `simulation_runner.dispatch_mc_simulation`

Uses `horizon_steps` and `num_paths` for charts and distribution stats—not for per-bar backtest signals. Backtest always uses **1-step** MC per bar.

`compute_return_distribution` (Vasicek only) decomposes simulated log-returns into mean-reversion vs jump KDE components for charts.

---

## Model selection guide

| Goal | Model | Rationale |
|------|-------|-----------|
| Mean reversion to a level with jumps | `vasicek` | OU on price toward θ with optional drifting θ |
| Trend / drift-following | `merton` | GBM-style growth with jumps |
| Reversion to moving average | `ou_deviation` | Explicit fair-value band via MA |
| Adapt to trend vs range | `blended` | ADX switches weight between Merton and OU |

---

## Key defaults

| Setting | Value |
|---------|-------|
| Min calibration bars | 30 |
| Default OU MA window | 20 |
| Jump detection z-threshold | 3.0 σ |
| Default ADX period | 14 |
| ADX blend band | 15 – 25 |
| Max backtest eval bars | 1000 |
| Default fees | 0.1% |

---

## Multi-timeframe analysis (MTFA)

**Module:** `mc_mtf.py`

| Config field | Purpose |
|--------------|---------|
| `regime_timeframe` | Higher TF for ADX / `w_trend` (e.g. `4h` when executing on `15m`) |
| `structure_timeframe` | Optional mid TF for structure veto |
| `mtf_gate_enabled` | Block BUY when HTF regime disagrees with `model_type` |
| `regime_min_trend_weight` | Min HTF trend weight for Merton/blended long entries (default 0.3) |

OHLCV is loaded at the **finest** TF among execution, regime, and structure (`mc_data_load_timeframe`). HTF series are resampled and forward-filled onto execution bars.

For **blended** mode, HTF ADX / `regime_w_trend` drives `w_trend_override` in `run_blended_step_prob`.

## Machine learning layer

**Modules:** `mc_features.py`, `ml/threshold_model.py`, `ml/regime_model.py`, `ml/surrogate_model.py`, `ml/train_models.py`

| Mode | Config | Behavior |
|------|--------|----------|
| Static thresholds | `threshold_mode: static` | Fixed `buy_threshold` / `sell_threshold` |
| Walk-forward percentiles | `threshold_mode: suggested_percentile` | Per-bar thresholds from expanding prob history (no lookahead) |
| ML dynamic | `threshold_mode: ml_dynamic` + `ml_threshold_model_path` | Ridge model predicts thresholds from MTF features |
| ADX regime | `regime_mode: adx` | Default blended weighting |
| ML regime | `regime_mode: ml` + `ml_regime_model_path` | Learned `w_trend` for blended blend |
| Surrogate | `use_surrogate: true` + `ml_surrogate_model_path` | Fast prob approximation; `surrogate_sample_pct` fraction validated against full MC |

**Training workflow:**

1. `POST /simulation/backtest/export-features` — writes walk-forward CSV under `backend/data/mc_ml_models/`
2. `python -m features.quantitative_engine.ml.train_models features_<asset>_<tf>.csv`
3. Point backtest request at `threshold_model.pkl`, `regime_model.pkl`, or `surrogate_model.pkl`

## Related API types

DTOs live in `backend/dtos/simulation_dto.py`: `VasicekParams`, `MertonParams`, `OuDeviationParams`, `JumpParams`, `CalibratedModelParams`, `McBacktestRequest`, `SimulationRequest`.

Routes are wired through `backend/routes/monte_carlo.py`.
