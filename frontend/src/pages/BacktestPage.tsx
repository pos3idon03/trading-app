import { useEffect, useState } from 'react';
import { backtestApi, dataApi, strategyBuilderApi } from '../api/endpoints';
import type { AssetItem, BacktestMetrics, BacktestResponse, OptimizationResponse } from '../api/types';
import { STRATEGIES, DEFAULT_PARAMS_MAP, DEFAULT_GRID_MAP, OPTIMIZE_METRICS } from '../constants/strategies';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import StatusBadge from '../components/StatusBadge';
import StrategyMultiSelect from '../components/StrategyMultiSelect';
import StrategyParamsEditor from '../components/StrategyParamsEditor';
import BacktestResultCard from '../components/BacktestResultCard';
import ParamGridEditor from '../components/ParamGridEditor';
import OptimizationResultsTable from '../components/OptimizationResultsTable';
import ComboTab from '../components/ComboTab';
import ComboMatrixTab from '../components/ComboMatrixTab';
import StrategyGuideTab from '../components/StrategyGuideTab';
import { formatAssetOptionLabel } from '../utils/assetDisplay';
import { fmt, fmtPct } from '../utils/formatting';
import { defaultDatesForTimeframe } from '../utils/backtestDates';
import type { BacktestTimeframe } from '../utils/backtestDates';

type TabId = 'backtest' | 'optimize' | 'combo' | 'matrix' | 'guide';

function useAssets() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  useEffect(() => {
    dataApi.getAssets().then((resp) => {
      setAssets(resp.assets.filter((a) => a.is_active));
    });
  }, []);
  return assets;
}

function TickerSelect({
  assets,
  value,
  onChange,
}: {
  assets: AssetItem[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="metric-label block mb-1">Ticker</label>
      <select
        className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={assets.length === 0}
      >
        {assets.length === 0 && <option value="">Loading…</option>}
        {assets.map((a) => (
          <option key={a.id} value={a.symbol}>
            {formatAssetOptionLabel(a)}
          </option>
        ))}
      </select>
    </div>
  );
}

function DateRangeInputs({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
}: {
  startDate: string;
  endDate: string;
  onStartChange: (v: string) => void;
  onEndChange: (v: string) => void;
}) {
  const cls = 'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';
  return (
    <>
      <div>
        <label className="metric-label block mb-1">Start Date</label>
        <input type="date" className={cls} value={startDate} onChange={(e) => onStartChange(e.target.value)} />
      </div>
      <div>
        <label className="metric-label block mb-1">End Date</label>
        <input type="date" className={cls} value={endDate} onChange={(e) => onEndChange(e.target.value)} />
      </div>
    </>
  );
}

type Timeframe = BacktestTimeframe;

const INTRADAY_TIMEFRAMES: Set<Timeframe> = new Set(['5m', '15m', '30m', '1h', '4h']);

const TIMEFRAME_OPTIONS: { value: Timeframe; label: string }[] = [
  { value: '5m', label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '30m', label: '30 Min' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: 'Daily' },
  { value: '1w', label: 'Weekly' },
];

function PriceFrequencySelect({
  value,
  onChange,
}: {
  value: Timeframe;
  onChange: (v: Timeframe) => void;
}) {
  const isIntraday = INTRADAY_TIMEFRAMES.has(value);
  return (
    <div>
      <label htmlFor="price-frequency" className="metric-label block mb-1">Price Frequency</label>
      <select
        id="price-frequency"
        className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
        value={value}
        onChange={(e) => onChange(e.target.value as Timeframe)}
      >
        {TIMEFRAME_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {isIntraday && (
        <p className="text-slate-500 text-xs mt-1">
          Aggregated from 5m bars. Date range auto-adjusted.
        </p>
      )}
    </div>
  );
}

function TabBar({ active, onChange }: { active: TabId; onChange: (t: TabId) => void }) {
  const cls = (t: TabId) =>
    `px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
      active === t
        ? 'bg-surface-800 text-slate-100 border-b-2 border-brand-500'
        : 'text-slate-400 hover:text-slate-200'
    }`;
  return (
    <div className="flex gap-1 border-b border-slate-700">
      <button className={cls('backtest')} onClick={() => onChange('backtest')}>Backtest</button>
      <button className={cls('optimize')} onClick={() => onChange('optimize')}>Optimize</button>
      <button className={cls('combo')} onClick={() => onChange('combo')}>Combo</button>
      <button className={cls('matrix')} onClick={() => onChange('matrix')}>Matrix</button>
      <button className={cls('guide')} onClick={() => onChange('guide')}>Strategy guide</button>
    </div>
  );
}

function PendingStrategyCard({ strategyValue }: { strategyValue: string }) {
  const label = STRATEGIES.find((s) => s.value === strategyValue)?.label ?? strategyValue;
  return (
    <div className="card flex flex-col items-center justify-center gap-3 min-h-[160px]">
      <Spinner label="" />
      <p className="text-slate-400 text-sm">{label}</p>
    </div>
  );
}

async function handleAddToStrategy(
  strategyName: string,
  params: Record<string, unknown>,
  assetId: number,
  timeframe: string,
): Promise<void> {
  await strategyBuilderApi.attachAlgo({
    asset_id: assetId,
    strategy_name: strategyName,
    params,
    timeframe,
  });
}

function BacktestResultsGrid({
  results,
  pending,
  attachTimeframe,
}: {
  results: BacktestResponse[];
  pending: string[];
  attachTimeframe: string;
}) {
  if (results.length === 0 && pending.length === 0) return null;

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
      {results.map((r) => (
        <BacktestResultCard
          key={r.strategy_name}
          result={r}
          attachTimeframe={attachTimeframe}
          onAddToStrategy={handleAddToStrategy}
        />
      ))}
      {pending.map((s) => (
        <PendingStrategyCard key={s} strategyValue={s} />
      ))}
    </div>
  );
}

async function runStrategiesParallel(
  symbol: string,
  strategies: string[],
  startDate: string,
  endDate: string,
  timeframe: Timeframe,
  paramsMap: Record<string, Record<string, number>>,
  onResult: (r: BacktestResponse) => void,
  onError: (strategy: string, msg: string) => void
) {
  const promises = strategies.map((strategyName) =>
    backtestApi
      .run({
        symbol,
        strategy_name: strategyName,
        timeframe,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        strategy_params: paramsMap[strategyName] ?? DEFAULT_PARAMS_MAP[strategyName] ?? {},
        initial_capital: 100_000,
      })
      .then((r) => { onResult(r); })
      .catch((e: Error) => { onError(strategyName, e.message); })
  );
  await Promise.allSettled(promises);
}

function buildInitialParamsMap(strategies: string[]): Record<string, Record<string, number>> {
  return Object.fromEntries(
    strategies.map((s) => [s, { ...(DEFAULT_PARAMS_MAP[s] ?? {}) }])
  );
}

function syncParamsMap(
  prev: Record<string, Record<string, number>>,
  next: string[]
): Record<string, Record<string, number>> {
  const synced: Record<string, Record<string, number>> = {};
  for (const s of next) {
    synced[s] = prev[s] ?? { ...(DEFAULT_PARAMS_MAP[s] ?? {}) };
  }
  return synced;
}

function BacktestTab({ assets }: { assets: AssetItem[] }) {
  const [symbol, setSymbol] = useState('');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['ma_crossover']);
  const [paramsMap, setParamsMap] = useState<Record<string, Record<string, number>>>(
    buildInitialParamsMap(['ma_crossover'])
  );
  const dailyDefaults = defaultDatesForTimeframe('1d');
  const [startDate, setStartDate] = useState(dailyDefaults.start);
  const [endDate, setEndDate] = useState(dailyDefaults.end);
  const [timeframe, setTimeframe] = useState<Timeframe>('1d');
  const [btResults, setBtResults] = useState<BacktestResponse[]>([]);
  const [pendingStrategies, setPendingStrategies] = useState<string[]>([]);
  const [btErrors, setBtErrors] = useState<string[]>([]);

  useEffect(() => {
    if (assets.length > 0 && !symbol) setSymbol(assets[0].symbol);
  }, [assets, symbol]);

  const handleTimeframeChange = (tf: Timeframe) => {
    setTimeframe(tf);
    const dates = defaultDatesForTimeframe(tf);
    setStartDate(dates.start);
    setEndDate(dates.end);
  };

  const handleStrategiesChange = (strategies: string[]) => {
    setSelectedStrategies(strategies);
    setParamsMap((prev) => syncParamsMap(prev, strategies));
  };

  const handleResult = (r: BacktestResponse) => {
    setBtResults((prev) => [...prev, r]);
    setPendingStrategies((prev) => prev.filter((s) => s !== r.strategy_name));
  };

  const handleError = (strategy: string, msg: string) => {
    setBtErrors((prev) => [...prev, `${strategy}: ${msg}`]);
    setPendingStrategies((prev) => prev.filter((s) => s !== strategy));
  };

  const runBacktest = async () => {
    if (!symbol || selectedStrategies.length === 0) return;
    setBtResults([]);
    setBtErrors([]);
    setPendingStrategies([...selectedStrategies]);
    await runStrategiesParallel(
      symbol, selectedStrategies, startDate, endDate, timeframe, paramsMap, handleResult, handleError,
    );
  };

  const isRunning = pendingStrategies.length > 0;

  return (
    <div className="space-y-6">
      {btErrors.map((e, i) => <ErrorAlert key={i} message={e} />)}

      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Configuration</h2>
        <div className="flex flex-wrap gap-4 items-start mb-4">
          <TickerSelect assets={assets} value={symbol} onChange={setSymbol} />
          <DateRangeInputs
            startDate={startDate}
            endDate={endDate}
            onStartChange={setStartDate}
            onEndChange={setEndDate}
          />
          <PriceFrequencySelect value={timeframe} onChange={handleTimeframeChange} />
        </div>
        <div className="mb-4">
          <StrategyMultiSelect selected={selectedStrategies} onChange={handleStrategiesChange} />
        </div>
        <div className="mb-4">
          <StrategyParamsEditor
            selectedStrategies={selectedStrategies}
            paramsMap={paramsMap}
            onChange={setParamsMap}
          />
        </div>
        <button
          onClick={runBacktest}
          disabled={isRunning || !symbol || selectedStrategies.length === 0}
          className="btn-primary disabled:opacity-50"
        >
          {isRunning
            ? `Running… (${pendingStrategies.length} remaining)`
            : `Run Backtest${selectedStrategies.length > 1 ? ` (${selectedStrategies.length} strategies)` : ''}`}
        </button>
      </div>

      <BacktestResultsGrid
        results={btResults}
        pending={pendingStrategies}
        attachTimeframe={timeframe}
      />
    </div>
  );
}

function OptimizeFullPeriodMetrics({ metrics }: { metrics: BacktestMetrics }) {
  return (
    <div className="grid grid-cols-2 gap-2 text-sm">
      <div className="flex justify-between col-span-2">
        <span className="text-slate-400">Total return</span>
        <span className="text-slate-100 font-semibold">{fmtPct(metrics.total_return)}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-slate-400">Sharpe</span>
        <span className="text-slate-100 font-semibold">{fmt(metrics.sharpe_ratio, 3)}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-slate-400">Sortino</span>
        <span className="text-slate-100 font-semibold">{fmt(metrics.sortino_ratio, 3)}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-slate-400">Max drawdown</span>
        <span className="text-red-400 font-semibold">{fmtPct(metrics.max_drawdown)}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-slate-400"># Trades</span>
        <span className="text-slate-100 font-semibold">{metrics.num_trades ?? '—'}</span>
      </div>
    </div>
  );
}

function OptimizeBestParams({ optResult }: { optResult: OptimizationResponse }) {
  if (!optResult.best_params) return null;
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div className="card border border-brand-500/30">
        <h3 className="text-brand-400 font-semibold mb-1">Best Parameters</h3>
        <p className="text-slate-500 text-xs mb-3">
          Avg OOS metrics are averaged across test folds where this combo won the prior in-sample leg.
        </p>
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
          {optResult.best_avg_oos_max_drawdown != null &&
            isFinite(optResult.best_avg_oos_max_drawdown) && (
            <div className="flex justify-between">
              <span className="text-slate-400 text-sm">Avg OOS max drawdown</span>
              <span className="text-slate-100 text-sm font-semibold">
                {fmtPct(optResult.best_avg_oos_max_drawdown)}
              </span>
            </div>
          )}
        </div>
      </div>
      {optResult.full_period_metrics && (
        <div className="card border border-slate-600">
          <h3 className="text-slate-200 font-semibold mb-1">Full sample (same window)</h3>
          <p className="text-slate-500 text-xs mb-3">
            Same definition as the Backtest tab: one run over the full date range with best params.
          </p>
          <OptimizeFullPeriodMetrics metrics={optResult.full_period_metrics} />
        </div>
      )}
    </div>
  );
}

function OptimizeSingleResult({ optResult }: { optResult: OptimizationResponse }) {
  return (
    <>
      <div className="flex items-center gap-3">
        <StatusBadge status={optResult.status} />
        <span className="text-slate-400 text-sm">
          Optimization #{optResult.optimization_id} &bull; {optResult.duration_ms}ms &bull;{' '}
          {optResult.n_splits} folds &bull; {optResult.optimize_metric}
        </span>
      </div>
      {optResult.error_message && <ErrorAlert message={optResult.error_message} />}
      <OptimizeBestParams optResult={optResult} />
      {optResult.all_results && optResult.all_results.length > 0 && (
        <div className="card">
          <h3 className="text-slate-200 font-semibold mb-4">
            All Parameter Combinations (sorted by OOS metric)
          </h3>
          <OptimizationResultsTable
            results={optResult.all_results}
            metric={optResult.optimize_metric ?? 'metric'}
          />
        </div>
      )}
    </>
  );
}

function OptimizeTab({ assets }: { assets: AssetItem[] }) {
  const [optSymbol, setOptSymbol] = useState('');
  const [optStrategy, setOptStrategy] = useState('ma_crossover');
  const optDailyDefaults = defaultDatesForTimeframe('1d');
  const [optStartDate, setOptStartDate] = useState(optDailyDefaults.start);
  const [optEndDate, setOptEndDate] = useState(optDailyDefaults.end);
  const [optTimeframe, setOptTimeframe] = useState<Timeframe>('1d');
  const [paramGrid, setParamGrid] = useState<Record<string, number[]>>(DEFAULT_GRID_MAP['ma_crossover']);
  const [nSplits, setNSplits] = useState(5);
  const [optimizeMetric, setOptimizeMetric] = useState('sharpe_ratio');
  const [maxDrawdownCap, setMaxDrawdownCap] = useState('');
  const [optResult, setOptResult] = useState<OptimizationResponse | null>(null);
  const [optLoading, setOptLoading] = useState(false);
  const [optError, setOptError] = useState<string | null>(null);

  useEffect(() => {
    if (assets.length > 0 && !optSymbol) setOptSymbol(assets[0].symbol);
  }, [assets, optSymbol]);

  const handleStrategyChange = (s: string) => {
    setOptStrategy(s);
    setParamGrid(DEFAULT_GRID_MAP[s] ?? DEFAULT_GRID_MAP['ma_crossover']);
  };

  const handleOptTimeframeChange = (tf: Timeframe) => {
    setOptTimeframe(tf);
    const dates = defaultDatesForTimeframe(tf);
    setOptStartDate(dates.start);
    setOptEndDate(dates.end);
  };

  const runOptimization = async () => {
    if (!optSymbol) return;
    setOptLoading(true);
    setOptError(null);
    try {
      const capRaw = maxDrawdownCap.trim();
      const capParsed = capRaw === '' ? undefined : parseFloat(capRaw);
      if (capParsed !== undefined && (Number.isNaN(capParsed) || capParsed > 0)) {
        setOptError('Max avg OOS drawdown must be a negative number (e.g. -0.25)');
        setOptLoading(false);
        return;
      }
      const resp = await backtestApi.optimize({
        symbol: optSymbol,
        strategy_name: optStrategy,
        timeframe: optTimeframe,
        start_date: new Date(optStartDate).toISOString(),
        end_date: new Date(optEndDate).toISOString(),
        param_grid: paramGrid,
        n_splits: nSplits,
        optimize_metric: optimizeMetric,
        initial_capital: 100_000,
        ...(capParsed !== undefined ? { max_drawdown_cap: capParsed } : {}),
      });
      setOptResult(resp);
    } catch (err) {
      setOptError((err as Error).message);
    } finally {
      setOptLoading(false);
    }
  };

  const selectCls = 'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

  return (
    <div className="space-y-6">
      {optError && <ErrorAlert message={optError} />}
      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Walk-Forward Optimization</h2>
        <p className="text-slate-400 text-xs mb-4">
          Sweeps parameter combinations across rolling train/test folds to find robust out-of-sample
          parameters. After optimization, full-sample metrics use the same engine as the Backtest tab
          so you can compare walk-forward averages to a single full-window run.
        </p>
        <div className="flex flex-wrap gap-4 items-end mb-6">
          <TickerSelect assets={assets} value={optSymbol} onChange={setOptSymbol} />
          <div>
            <label className="metric-label block mb-1">Strategy</label>
            <select className={selectCls} value={optStrategy} onChange={(e) => handleStrategyChange(e.target.value)}>
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Optimize Metric</label>
            <select className={selectCls} value={optimizeMetric} onChange={(e) => setOptimizeMetric(e.target.value)}>
              {OPTIMIZE_METRICS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">WFO Splits</label>
            <input
              type="number" min={2} max={20}
              className={`${selectCls} w-20`}
              value={nSplits}
              onChange={(e) => setNSplits(parseInt(e.target.value) || 5)}
            />
          </div>
          <div>
            <label className="metric-label block mb-1" title="Worst allowed average OOS max drawdown">
              Max avg OOS drawdown
            </label>
            <input
              type="text"
              placeholder="-0.25"
              className={`${selectCls} w-28`}
              value={maxDrawdownCap}
              onChange={(e) => setMaxDrawdownCap(e.target.value)}
            />
          </div>
          <DateRangeInputs startDate={optStartDate} endDate={optEndDate} onStartChange={setOptStartDate} onEndChange={setOptEndDate} />
          <PriceFrequencySelect value={optTimeframe} onChange={handleOptTimeframeChange} />
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
      {optResult && !optLoading && <OptimizeSingleResult optResult={optResult} />}
    </div>
  );
}

export default function BacktestPage() {
  const assets = useAssets();
  const [activeTab, setActiveTab] = useState<TabId>('backtest');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Backtesting</h1>
        <p className="text-slate-400 text-sm mt-1">
          Historical strategy simulation and walk-forward parameter optimization
        </p>
      </div>
      <TabBar active={activeTab} onChange={setActiveTab} />
      {activeTab === 'backtest' && <BacktestTab assets={assets} />}
      {activeTab === 'optimize' && <OptimizeTab assets={assets} />}
      {activeTab === 'combo' && <ComboTab assets={assets} />}
      {activeTab === 'matrix' && <ComboMatrixTab assets={assets} />}
      {activeTab === 'guide' && <StrategyGuideTab />}
    </div>
  );
}
