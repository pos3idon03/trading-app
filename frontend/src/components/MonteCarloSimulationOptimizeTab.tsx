import { useEffect, useState } from 'react';
import { simulationApi } from '../api/endpoints';
import type { AssetItem, McModelType, McSimulationOptimizeResponse } from '../api/types';
import ParamGridEditor from './ParamGridEditor';
import Spinner from './Spinner';
import ErrorAlert from './ErrorAlert';
import McSimulationOptimizeResults from './McSimulationOptimizeResults';
import { formatAssetOptionLabel } from '../utils/assetDisplay';
import { defaultDatesForTimeframe } from '../utils/backtestDates';
import {
  DEFAULT_MC_SIM_GRID,
  MC_HORIZON_OPTIONS,
  MC_MODEL_OPTIONS,
  MC_SIM_OPTIMIZE_METRICS,
} from '../constants/monteCarlo';

const SELECT_CLS =
  'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

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
        className={SELECT_CLS}
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

export default function MonteCarloSimulationOptimizeTab({ assets }: { assets: AssetItem[] }) {
  const dailyDefaults = defaultDatesForTimeframe('1d');
  const [symbol, setSymbol] = useState('');
  const [modelType, setModelType] = useState<McModelType>('merton');
  const [startDate, setStartDate] = useState(dailyDefaults.start);
  const [endDate, setEndDate] = useState(dailyDefaults.end);
  const [timeframe, setTimeframe] = useState('1d');
  const [horizonSteps, setHorizonSteps] = useState(252);
  const [paramGrid, setParamGrid] = useState<Record<string, number[]>>(DEFAULT_MC_SIM_GRID);
  const [nSplits, setNSplits] = useState(5);
  const [optimizeMetric, setOptimizeMetric] = useState('prob_positive_return');
  const [maxDrawdownCap, setMaxDrawdownCap] = useState('');
  const [result, setResult] = useState<McSimulationOptimizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (assets.length > 0 && !symbol) setSymbol(assets[0].symbol);
  }, [assets, symbol]);

  const runOptimization = async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const capRaw = maxDrawdownCap.trim();
      const capParsed = capRaw === '' ? undefined : parseFloat(capRaw);
      if (capParsed !== undefined && (Number.isNaN(capParsed) || capParsed > 0)) {
        setError('Max avg OOS drawdown must be a negative number (e.g. -0.25)');
        setLoading(false);
        return;
      }
      const resp = await simulationApi.optimize({
        symbol,
        timeframe,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        model_type: modelType,
        horizon_steps: horizonSteps,
        param_grid: paramGrid,
        n_splits: nSplits,
        optimize_metric: optimizeMetric,
        ...(capParsed !== undefined ? { max_drawdown_cap: capParsed } : {}),
      });
      setResult(resp);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && <ErrorAlert message={error} />}
      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Walk-Forward Simulation Optimization</h2>
        <p className="text-slate-400 text-xs mb-4">
          Sweeps MC simulation config across rolling train/test folds. In-sample picks the best
          combo by simulation stats; out-of-sample scores predictive accuracy vs actual prices.
        </p>
        <div className="flex flex-wrap gap-4 items-end mb-6">
          <TickerSelect assets={assets} value={symbol} onChange={setSymbol} />
          <div>
            <label className="metric-label block mb-1">Model</label>
            <select
              className={SELECT_CLS}
              value={modelType}
              onChange={(e) => setModelType(e.target.value as McModelType)}
            >
              {MC_MODEL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Optimize Metric</label>
            <select
              className={SELECT_CLS}
              value={optimizeMetric}
              onChange={(e) => setOptimizeMetric(e.target.value)}
            >
              {MC_SIM_OPTIMIZE_METRICS.map((m) => (
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
              className={`${SELECT_CLS} w-20`}
              value={nSplits}
              onChange={(e) => setNSplits(parseInt(e.target.value, 10) || 5)}
            />
          </div>
          <div>
            <label className="metric-label block mb-1">Simulation Period</label>
            <select
              className={SELECT_CLS}
              value={horizonSteps}
              onChange={(e) => setHorizonSteps(Number(e.target.value))}
            >
              {MC_HORIZON_OPTIONS.map((v) => (
                <option key={v} value={v}>{v} days</option>
              ))}
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1">Start Date</label>
            <input
              type="date"
              className={SELECT_CLS}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label className="metric-label block mb-1">End Date</label>
            <input
              type="date"
              className={SELECT_CLS}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
          <div>
            <label className="metric-label block mb-1">Timeframe</label>
            <select className={SELECT_CLS} value={timeframe} onChange={(e) => setTimeframe(e.target.value)}>
              <option value="1d">Daily</option>
              <option value="1w">Weekly</option>
            </select>
          </div>
          <div>
            <label className="metric-label block mb-1" title="Worst allowed average OOS max drawdown">
              Max avg OOS drawdown
            </label>
            <input
              type="text"
              placeholder="-0.25"
              className={`${SELECT_CLS} w-28`}
              value={maxDrawdownCap}
              onChange={(e) => setMaxDrawdownCap(e.target.value)}
            />
          </div>
        </div>
        <div className="mb-4">
          <h3 className="text-slate-300 text-sm font-medium mb-2">Parameter Grid</h3>
          <p className="text-slate-500 text-xs mb-3">
            Enter comma-separated values to sweep for each parameter.
          </p>
          <ParamGridEditor grid={paramGrid} onChange={setParamGrid} />
        </div>
        <button
          type="button"
          onClick={runOptimization}
          disabled={loading || !symbol}
          className="btn-primary disabled:opacity-50"
        >
          {loading ? 'Optimizing…' : 'Run Optimization'}
        </button>
      </div>
      {loading && <Spinner label="Running walk-forward simulation optimization…" />}
      {result && !loading && <McSimulationOptimizeResults result={result} />}
    </div>
  );
}
