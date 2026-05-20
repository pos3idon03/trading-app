import { useEffect, useState } from 'react';
import type { AssetItem, McBacktestPreset, McBacktestTimeframe, McModelType } from '../api/types';
import ParamGridEditor from './ParamGridEditor';
import ErrorAlert from './ErrorAlert';
import McBacktestOptimizeResults from './McBacktestOptimizeResults';
import { formatAssetOptionLabel } from '../utils/assetDisplay';
import {
  defaultCalibrationDaysForTimeframe,
  defaultDatesForTimeframe,
  INTRADAY_CALIBRATION_DAY_OPTIONS,
  INTRADAY_MAX_LOOKBACK_DAYS,
  isIntradayTimeframe,
} from '../utils/backtestDates';
import { buildBacktestPreset, countValidBacktestCombos, isBacktestGridOverLimit } from '../utils/mcBacktestPreset';
import {
  DEFAULT_MC_BACKTEST_GRID,
  MC_BACKTEST_OPTIMIZE_METRICS,
  MC_MAX_PARAM_COMBOS,
  MC_MODEL_OPTIONS,
} from '../constants/monteCarlo';
import { useMcBacktestOptimizeJob } from '../hooks/useMcBacktestOptimizeJob';

const SELECT_CLS =
  'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

const TIMEFRAME_OPTIONS: { value: McBacktestTimeframe; label: string }[] = [
  { value: '5m', label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '30m', label: '30 Min' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: 'Daily' },
  { value: '1w', label: 'Weekly' },
];

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

interface MonteCarloBacktestOptimizeTabProps {
  assets: AssetItem[];
  onApplyPreset: (preset: McBacktestPreset) => void;
}

export default function MonteCarloBacktestOptimizeTab({
  assets,
  onApplyPreset,
}: MonteCarloBacktestOptimizeTabProps) {
  const dailyDefaults = defaultDatesForTimeframe('1d');
  const [symbol, setSymbol] = useState('');
  const [modelType, setModelType] = useState<McModelType>('merton');
  const [startDate, setStartDate] = useState(dailyDefaults.start);
  const [endDate, setEndDate] = useState(dailyDefaults.end);
  const [timeframe, setTimeframe] = useState<McBacktestTimeframe>('1d');
  const [calibrationDays, setCalibrationDays] = useState(30);
  const [paramGrid, setParamGrid] = useState<Record<string, number[]>>(DEFAULT_MC_BACKTEST_GRID);
  const [nSplits, setNSplits] = useState(5);
  const [optimizeMetric, setOptimizeMetric] = useState('sortino_ratio');
  const [minTrades, setMinTrades] = useState(5);
  const [maxDrawdownCap, setMaxDrawdownCap] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const {
    loading,
    progressPct,
    progressMessage,
    result,
    error,
    start,
  } = useMcBacktestOptimizeJob();

  useEffect(() => {
    if (assets.length > 0 && !symbol) setSymbol(assets[0].symbol);
  }, [assets, symbol]);

  const handleTimeframeChange = (tf: McBacktestTimeframe) => {
    setTimeframe(tf);
    const dates = defaultDatesForTimeframe(tf);
    setStartDate(dates.start);
    setEndDate(dates.end);
    if (isIntradayTimeframe(tf)) {
      setCalibrationDays(defaultCalibrationDaysForTimeframe(tf));
    }
  };

  const comboCount = countValidBacktestCombos(paramGrid);
  const gridOverLimit = isBacktestGridOverLimit(paramGrid);

  const runOptimization = async () => {
    if (!symbol || gridOverLimit) return;
    setValidationError(null);
    const capRaw = maxDrawdownCap.trim();
    const capParsed = capRaw === '' ? undefined : parseFloat(capRaw);
    if (capParsed !== undefined && (Number.isNaN(capParsed) || capParsed > 0)) {
      setValidationError('Max avg OOS drawdown must be a negative number (e.g. -0.25)');
      return;
    }
    await start({
      symbol,
      timeframe,
      start_date: new Date(startDate).toISOString(),
      end_date: new Date(endDate).toISOString(),
      model_type: modelType,
      param_grid: paramGrid,
      n_splits: nSplits,
      optimize_metric: optimizeMetric,
      initial_capital: 1000,
      min_trades: minTrades,
      ...(isIntradayTimeframe(timeframe) ? { calibration_days: calibrationDays } : {}),
      ...(capParsed !== undefined ? { max_drawdown_cap: capParsed } : {}),
    });
  };

  const handleApply = () => {
    if (!result) return;
    const preset = buildBacktestPreset(result, {
      symbol,
      modelType,
      timeframe,
      startDate,
      endDate,
      calibrationDays,
    });
    if (preset) onApplyPreset(preset);
  };

  const displayError = validationError ?? error;

  return (
    <div className="space-y-6">
      {displayError && <ErrorAlert message={displayError} />}
      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-4">Walk-Forward Backtest Optimization</h2>
        <p className="text-slate-400 text-xs mb-4">
          Sweeps entry/exit thresholds plus MC config across rolling folds using the same
          1-step prob-positive backtest engine. Best params can be applied directly to the
          Backtest tab.
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
              {MC_BACKTEST_OPTIMIZE_METRICS.map((m) => (
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
            <label className="metric-label block mb-1">Min OOS trades</label>
            <input
              type="number"
              min={0}
              max={100}
              className={`${SELECT_CLS} w-20`}
              value={minTrades}
              onChange={(e) => setMinTrades(parseInt(e.target.value, 10) || 0)}
            />
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
            <select
              className={SELECT_CLS}
              value={timeframe}
              onChange={(e) => handleTimeframeChange(e.target.value as McBacktestTimeframe)}
            >
              {TIMEFRAME_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
          {isIntradayTimeframe(timeframe) && (
            <div>
              <label className="metric-label block mb-1">Calibration Window</label>
              <select
                className={SELECT_CLS}
                value={calibrationDays}
                onChange={(e) => setCalibrationDays(Number(e.target.value))}
              >
                {INTRADAY_CALIBRATION_DAY_OPTIONS.map((v) => (
                  <option key={v} value={v}>{v} days</option>
                ))}
              </select>
            </div>
          )}
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
        {isIntradayTimeframe(timeframe) && (
          <p className="text-slate-500 text-xs mb-4">
            Intraday bars are resampled from stored 5m data (up to {INTRADAY_MAX_LOOKBACK_DAYS} days).
            Add calibration_days to the param grid to sweep calibration windows.
          </p>
        )}
        <div className="mb-4">
          <h3 className="text-slate-300 text-sm font-medium mb-2">Parameter Grid</h3>
          <p className="text-slate-500 text-xs mb-3">
            Entry/exit thresholds as percentages (e.g. 52 = 52%). Must satisfy Exit &lt; Entry.
            Optional: entry_confirmation_bars, prob_smoothing_bars, min_hold_bars, cooldown_bars.
          </p>
          <ParamGridEditor grid={paramGrid} onChange={setParamGrid} />
          <p
            className={`text-xs mt-2 ${gridOverLimit ? 'text-red-400' : 'text-slate-500'}`}
          >
            {comboCount} valid combination{comboCount === 1 ? '' : 's'} (max {MC_MAX_PARAM_COMBOS}).
            {gridOverLimit
              ? ' Reduce grid values to continue.'
              : ' Large grids run as a background job with live progress.'}
          </p>
        </div>
        <button
          type="button"
          onClick={runOptimization}
          disabled={loading || !symbol || gridOverLimit || comboCount === 0}
          className="btn-primary disabled:opacity-50"
        >
          {loading ? 'Optimizing…' : 'Run Optimization'}
        </button>
        {loading && (
          <div className="mt-4 space-y-2">
            <div className="h-2 bg-surface-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 transition-all duration-300"
                style={{ width: `${Math.min(100, Math.max(0, progressPct))}%` }}
              />
            </div>
            <p className="text-slate-400 text-xs">
              {progressMessage ?? 'Starting optimization…'}
              {progressPct > 0 ? ` (${Math.round(progressPct)}%)` : ''}
            </p>
          </div>
        )}
      </div>
      {result && !loading && (
        <McBacktestOptimizeResults result={result} onApply={handleApply} />
      )}
    </div>
  );
}
