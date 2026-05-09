import { useEffect, useState } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
} from 'recharts';
import { backtestApi, dataApi } from '../api/endpoints';
import type {
  AssetItem,
  BacktestResponse,
  OptimizationResponse,
  OptimizationSummary,
} from '../api/types';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';

const STRATEGIES = [
  { value: 'ma_crossover', label: 'MA Crossover' },
  { value: 'mean_reversion', label: 'Mean Reversion' },
  { value: 'breakout', label: 'Breakout (Volatility Expansion)' },
  { value: 'trend_pullback', label: 'Trend-Following with Pullbacks' },
  { value: 'gap_fade', label: 'Gap Fade' },
  { value: 'vrp_harvest', label: 'VRP Harvest' },
];

const OPTIMIZE_METRICS = [
  { value: 'sharpe_ratio', label: 'Sharpe Ratio' },
  { value: 'sortino_ratio', label: 'Sortino Ratio' },
  { value: 'total_return', label: 'Total Return' },
  { value: 'profit_factor', label: 'Profit Factor' },
];

const DEFAULT_MA_PARAMS = { fast_window: 10, slow_window: 50 };
const DEFAULT_MR_PARAMS = { lookback: 20, z_threshold: 2.0 };
const DEFAULT_BREAKOUT_PARAMS = { bb_window: 20, bb_std: 2.0, squeeze_lookback: 120, donchian_window: 20 };
const DEFAULT_TREND_PULLBACK_PARAMS = { adx_period: 14, adx_threshold: 25.0, stoch_period: 14, stoch_smooth: 3, oversold: 20.0, overbought: 80.0 };
const DEFAULT_GAP_FADE_PARAMS = { gap_threshold: 0.03, min_gap_fill_bars: 5 };
const DEFAULT_VRP_HARVEST_PARAMS = { rv_window: 20, iv_proxy_window: 60, z_entry: -1.0, z_exit: 0.5 };

const DEFAULT_MA_GRID = { fast_window: [5, 10, 20], slow_window: [30, 50, 100] };
const DEFAULT_MR_GRID = { lookback: [10, 20, 30], z_threshold: [1.5, 2.0, 2.5] };
const DEFAULT_BREAKOUT_GRID = { bb_window: [15, 20, 25], squeeze_lookback: [60, 120, 180], donchian_window: [15, 20, 25] };
const DEFAULT_TREND_PULLBACK_GRID = { adx_period: [10, 14, 20], adx_threshold: [20.0, 25.0, 30.0], oversold: [15.0, 20.0, 25.0] };
const DEFAULT_GAP_FADE_GRID = { gap_threshold: [0.02, 0.03, 0.05] };
const DEFAULT_VRP_HARVEST_GRID = { rv_window: [10, 20, 30], iv_proxy_window: [40, 60, 90], z_entry: [-1.5, -1.0, -0.5] };

const DEFAULT_PARAMS_MAP: Record<string, Record<string, number>> = {
  ma_crossover: DEFAULT_MA_PARAMS,
  mean_reversion: DEFAULT_MR_PARAMS,
  breakout: DEFAULT_BREAKOUT_PARAMS,
  trend_pullback: DEFAULT_TREND_PULLBACK_PARAMS,
  gap_fade: DEFAULT_GAP_FADE_PARAMS,
  vrp_harvest: DEFAULT_VRP_HARVEST_PARAMS,
};

const DEFAULT_GRID_MAP: Record<string, Record<string, number[]>> = {
  ma_crossover: DEFAULT_MA_GRID,
  mean_reversion: DEFAULT_MR_GRID,
  breakout: DEFAULT_BREAKOUT_GRID,
  trend_pullback: DEFAULT_TREND_PULLBACK_GRID,
  gap_fade: DEFAULT_GAP_FADE_GRID,
  vrp_harvest: DEFAULT_VRP_HARVEST_GRID,
};

type TabId = 'backtest' | 'optimize';

function fmt(v: number | undefined | null, decimals = 4, suffix = '') {
  if (v === null || v === undefined) return '—';
  return `${v.toFixed(decimals)}${suffix}`;
}

function fmtPct(v: number | undefined | null) {
  if (v === null || v === undefined) return '—';
  return `${(v * 100).toFixed(2)}%`;
}

function ParamGridEditor({
  grid,
  onChange,
}: {
  grid: Record<string, number[]>;
  onChange: (g: Record<string, number[]>) => void;
}) {
  const handleValueChange = (key: string, raw: string) => {
    const nums = raw
      .split(',')
      .map((s) => parseFloat(s.trim()))
      .filter((n) => !isNaN(n));
    onChange({ ...grid, [key]: nums });
  };

  return (
    <div className="space-y-2">
      {Object.entries(grid).map(([key, values]) => (
        <div key={key} className="flex items-center gap-3">
          <span className="text-slate-300 text-xs font-mono w-28 shrink-0">{key}</span>
          <input
            type="text"
            className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-brand-500 flex-1"
            value={values.join(', ')}
            onChange={(e) => handleValueChange(key, e.target.value)}
            placeholder="comma-separated values"
          />
        </div>
      ))}
    </div>
  );
}

function OptimizationResultsTable({ results, metric }: { results: OptimizationSummary[]; metric: string }) {
  const sorted = [...results].sort((a, b) => b.avg_oos_metric - a.avg_oos_metric);
  const max = sorted[0]?.avg_oos_metric ?? 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b border-slate-700">
            {sorted[0] &&
              Object.keys(sorted[0].params).map((k) => (
                <th key={k} className="px-3 py-2 text-slate-400 font-medium">
                  {k}
                </th>
              ))}
            <th className="px-3 py-2 text-slate-400 font-medium">Avg OOS {metric}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const isInf = !isFinite(row.avg_oos_metric);
            const pct = isInf ? 0 : Math.max(0, row.avg_oos_metric / max);
            return (
              <tr key={i} className={`border-b border-slate-800 ${i === 0 ? 'bg-brand-500/10' : ''}`}>
                {Object.values(row.params).map((v, j) => (
                  <td key={j} className="px-3 py-2 font-mono text-slate-200">
                    {String(v)}
                  </td>
                ))}
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 rounded-full bg-slate-700 flex-1 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${isInf ? 'bg-slate-600' : 'bg-brand-500'}`}
                        style={{ width: `${pct * 100}%` }}
                      />
                    </div>
                    <span className={`font-mono w-16 text-right ${isInf ? 'text-slate-500' : i === 0 ? 'text-brand-400' : 'text-slate-300'}`}>
                      {isInf ? '—' : row.avg_oos_metric.toFixed(4)}
                    </span>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function BacktestPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [activeTab, setActiveTab] = useState<TabId>('backtest');

  // Backtest state
  const [symbol, setSymbol] = useState('');
  const [strategy, setStrategy] = useState('ma_crossover');
  const [startDate, setStartDate] = useState('2022-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [btResult, setBtResult] = useState<BacktestResponse | null>(null);
  const [btLoading, setBtLoading] = useState(false);
  const [btError, setBtError] = useState<string | null>(null);

  // Optimization state
  const [optSymbol, setOptSymbol] = useState('');
  const [optStrategy, setOptStrategy] = useState('ma_crossover');
  const [optStartDate, setOptStartDate] = useState('2020-01-01');
  const [optEndDate, setOptEndDate] = useState('2024-12-31');
  const [paramGrid, setParamGrid] = useState<Record<string, number[]>>(DEFAULT_MA_GRID);
  const [nSplits, setNSplits] = useState(5);
  const [optimizeMetric, setOptimizeMetric] = useState('sharpe_ratio');
  const [optResult, setOptResult] = useState<OptimizationResponse | null>(null);
  const [optLoading, setOptLoading] = useState(false);
  const [optError, setOptError] = useState<string | null>(null);

  useEffect(() => {
    dataApi.getAssets().then((resp) => {
      const active = resp.assets.filter((a) => a.is_active);
      setAssets(active);
      if (active.length > 0) {
        setSymbol(active[0].symbol);
        setOptSymbol(active[0].symbol);
      }
    });
  }, []);

  const strategyParams = DEFAULT_PARAMS_MAP[strategy] ?? DEFAULT_MA_PARAMS;

  const handleStrategyChange = (s: string) => {
    setStrategy(s);
  };

  const handleOptStrategyChange = (s: string) => {
    setOptStrategy(s);
    setParamGrid(DEFAULT_GRID_MAP[s] ?? DEFAULT_MA_GRID);
  };

  const runBacktest = async () => {
    if (!symbol) return;
    setBtLoading(true);
    setBtError(null);
    try {
      const resp = await backtestApi.run({
        symbol,
        strategy_name: strategy,
        timeframe: '1d',
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        strategy_params: strategyParams,
        initial_capital: 100_000,
      });
      setBtResult(resp);
    } catch (err) {
      setBtError((err as Error).message);
    } finally {
      setBtLoading(false);
    }
  };

  const runOptimization = async () => {
    if (!optSymbol) return;
    setOptLoading(true);
    setOptError(null);
    try {
      const resp = await backtestApi.optimize({
        symbol: optSymbol,
        strategy_name: optStrategy,
        timeframe: '1d',
        start_date: new Date(optStartDate).toISOString(),
        end_date: new Date(optEndDate).toISOString(),
        param_grid: paramGrid,
        n_splits: nSplits,
        optimize_metric: optimizeMetric,
        initial_capital: 100_000,
      });
      setOptResult(resp);
    } catch (err) {
      setOptError((err as Error).message);
    } finally {
      setOptLoading(false);
    }
  };

  const m = btResult?.metrics;
  const tabClass = (t: TabId) =>
    `px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
      activeTab === t
        ? 'bg-surface-800 text-slate-100 border-b-2 border-brand-500'
        : 'text-slate-400 hover:text-slate-200'
    }`;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Backtesting</h1>
        <p className="text-slate-400 text-sm mt-1">Historical strategy simulation and walk-forward parameter optimization</p>
      </div>

      <div className="flex gap-1 border-b border-slate-700">
        <button className={tabClass('backtest')} onClick={() => setActiveTab('backtest')}>Backtest</button>
        <button className={tabClass('optimize')} onClick={() => setActiveTab('optimize')}>Optimize</button>
      </div>

      {activeTab === 'backtest' && (
        <div className="space-y-6">
          {btError && <ErrorAlert message={btError} />}

          <div className="card">
            <h2 className="text-slate-200 font-semibold mb-4">Configuration</h2>
            <div className="flex flex-wrap gap-4 items-end">
              <div>
                <label className="metric-label block mb-1">Ticker</label>
                <select
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  disabled={assets.length === 0}
                >
                  {assets.length === 0 && <option value="">Loading…</option>}
                  {assets.map((a) => (
                    <option key={a.id} value={a.symbol}>
                      {a.symbol}{a.name ? ` — ${a.name}` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="metric-label block mb-1">Strategy</label>
                <select
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={strategy}
                  onChange={(e) => handleStrategyChange(e.target.value)}
                >
                  {STRATEGIES.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="metric-label block mb-1">Start Date</label>
                <input
                  type="date"
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div>
                <label className="metric-label block mb-1">End Date</label>
                <input
                  type="date"
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
              <button onClick={runBacktest} disabled={btLoading || !symbol} className="btn-primary disabled:opacity-50">
                {btLoading ? 'Running…' : 'Run Backtest'}
              </button>
            </div>
            <div className="mt-3 p-2 bg-surface-900 rounded-lg border border-slate-700 text-xs text-slate-500 font-mono">
              Params: {JSON.stringify(strategyParams)}
            </div>
          </div>

          {btLoading && <Spinner label="Running backtest…" />}

          {btResult && !btLoading && (
            <>
              <div className="flex items-center gap-3">
                <StatusBadge status={btResult.status} />
                <span className="text-slate-400 text-sm">
                  Backtest #{btResult.backtest_id} &bull; {btResult.duration_ms}ms &bull; {btResult.strategy_name}
                </span>
              </div>

              {btResult.error_message && <ErrorAlert message={btResult.error_message} />}

              {m && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <MetricCard label="Total Return" value={fmtPct(m.total_return)} positive={(m.total_return ?? 0) > 0} negative={(m.total_return ?? 0) < 0} />
                  <MetricCard label="Sharpe Ratio" value={fmt(m.sharpe_ratio, 3)} positive={(m.sharpe_ratio ?? 0) > 1} negative={(m.sharpe_ratio ?? 0) < 0} />
                  <MetricCard label="Sortino Ratio" value={fmt(m.sortino_ratio, 3)} positive={(m.sortino_ratio ?? 0) > 1} />
                  <MetricCard label="Max Drawdown" value={fmtPct(m.max_drawdown)} negative />
                  <MetricCard label="Win Rate" value={fmtPct(m.win_rate)} positive={(m.win_rate ?? 0) > 0.5} />
                  <MetricCard label="Profit Factor" value={fmt(m.profit_factor, 2)} positive={(m.profit_factor ?? 0) > 1} />
                  <MetricCard label="Annual Return" value={fmtPct(m.annualized_return)} positive={(m.annualized_return ?? 0) > 0} />
                  <MetricCard label="# Trades" value={m.num_trades ?? '—'} />
                </div>
              )}

              {btResult.equity_curve && btResult.equity_curve.length > 0 && (
                <div className="card">
                  <h2 className="text-slate-200 font-semibold mb-4">Equity Curve</h2>
                  <ResponsiveContainer width="100%" height={320}>
                    <AreaChart data={btResult.equity_curve} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                      <defs>
                        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="time" stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => v.substring(0, 10)} />
                      <YAxis stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                      <Tooltip
                        contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
                        labelStyle={{ color: '#94a3b8' }}
                        formatter={(v: number) => [`$${v.toFixed(2)}`, 'Portfolio Value']}
                      />
                      <Area type="monotone" dataKey="value" stroke="#22c55e" strokeWidth={2} fill="url(#equityGrad)" dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === 'optimize' && (
        <div className="space-y-6">
          {optError && <ErrorAlert message={optError} />}

          <div className="card">
            <h2 className="text-slate-200 font-semibold mb-4">Walk-Forward Optimization</h2>
            <p className="text-slate-400 text-xs mb-4">
              Sweeps parameter combinations across rolling train/test folds to find the best out-of-sample parameters without overfitting.
            </p>

            <div className="flex flex-wrap gap-4 items-end mb-6">
              <div>
                <label className="metric-label block mb-1">Ticker</label>
                <select
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={optSymbol}
                  onChange={(e) => setOptSymbol(e.target.value)}
                  disabled={assets.length === 0}
                >
                  {assets.length === 0 && <option value="">Loading…</option>}
                  {assets.map((a) => (
                    <option key={a.id} value={a.symbol}>
                      {a.symbol}{a.name ? ` — ${a.name}` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="metric-label block mb-1">Strategy</label>
                <select
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={optStrategy}
                  onChange={(e) => handleOptStrategyChange(e.target.value)}
                >
                  {STRATEGIES.map((s) => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="metric-label block mb-1">Optimize Metric</label>
                <select
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={optimizeMetric}
                  onChange={(e) => setOptimizeMetric(e.target.value)}
                >
                  {OPTIMIZE_METRICS.map((m) => (
                    <option key={m.value} value={m.value}>{m.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="metric-label block mb-1">WFO Splits</label>
                <input
                  type="number"
                  min={2}
                  max={20}
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 w-20"
                  value={nSplits}
                  onChange={(e) => setNSplits(parseInt(e.target.value) || 5)}
                />
              </div>
              <div>
                <label className="metric-label block mb-1">Start Date</label>
                <input
                  type="date"
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={optStartDate}
                  onChange={(e) => setOptStartDate(e.target.value)}
                />
              </div>
              <div>
                <label className="metric-label block mb-1">End Date</label>
                <input
                  type="date"
                  className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
                  value={optEndDate}
                  onChange={(e) => setOptEndDate(e.target.value)}
                />
              </div>
            </div>

            <div className="mb-4">
              <h3 className="text-slate-300 text-sm font-medium mb-2">Parameter Grid</h3>
              <p className="text-slate-500 text-xs mb-3">Enter comma-separated values to sweep for each parameter.</p>
              <ParamGridEditor grid={paramGrid} onChange={setParamGrid} />
            </div>

            <button onClick={runOptimization} disabled={optLoading || !optSymbol} className="btn-primary disabled:opacity-50">
              {optLoading ? 'Optimizing…' : 'Run Optimization'}
            </button>
          </div>

          {optLoading && <Spinner label="Running walk-forward optimization…" />}

          {optResult && !optLoading && (
            <>
              <div className="flex items-center gap-3">
                <StatusBadge status={optResult.status} />
                <span className="text-slate-400 text-sm">
                  Optimization #{optResult.optimization_id} &bull; {optResult.duration_ms}ms &bull; {optResult.n_splits} folds &bull; {optResult.optimize_metric}
                </span>
              </div>

              {optResult.error_message && <ErrorAlert message={optResult.error_message} />}

              {optResult.best_params && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="card border border-brand-500/30">
                    <h3 className="text-brand-400 font-semibold mb-3">Best Parameters</h3>
                    <div className="space-y-2">
                      {Object.entries(optResult.best_params).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-slate-400 text-sm font-mono">{k}</span>
                          <span className="text-slate-100 text-sm font-mono font-semibold">{String(v)}</span>
                        </div>
                      ))}
                      <div className="pt-2 border-t border-slate-700 flex justify-between">
                        <span className="text-slate-400 text-sm">Avg OOS {optResult.optimize_metric}</span>
                        <span className="text-brand-400 text-sm font-semibold">
                          {optResult.best_metric !== undefined && isFinite(optResult.best_metric)
                            ? optResult.best_metric.toFixed(4)
                            : '—'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {optResult.all_results && optResult.all_results.length > 0 && (
                <div className="card">
                  <h3 className="text-slate-200 font-semibold mb-4">All Parameter Combinations (sorted by OOS metric)</h3>
                  <OptimizationResultsTable
                    results={optResult.all_results}
                    metric={optResult.optimize_metric ?? 'metric'}
                  />
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
