import { useEffect, useState } from 'react';
import { backtestApi } from '../api/endpoints';
import type {
  AssetItem,
  CombinationMode,
  ComboMatrixMetric,
  ComboMatrixResponse,
} from '../api/types';
import { STRATEGIES, DEFAULT_PARAMS_MAP, OPTIMIZE_METRICS } from '../constants/strategies';
import ErrorAlert from './ErrorAlert';
import Spinner from './Spinner';
import StrategyHeatmap from './StrategyHeatmap';
import StrategyMultiSelect from './StrategyMultiSelect';
import { formatAssetOptionLabel } from '../utils/assetDisplay';
import { defaultDatesForTimeframe } from '../utils/backtestDates';
import type { BacktestTimeframe } from '../utils/backtestDates';

type MatrixTimeframe = BacktestTimeframe;

const INTRADAY_TIMEFRAMES: Set<MatrixTimeframe> = new Set(['5m', '15m', '30m', '1h', '4h']);

const TIMEFRAME_OPTIONS: { value: MatrixTimeframe; label: string }[] = [
  { value: '5m', label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '30m', label: '30 Min' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: 'Daily' },
  { value: '1w', label: 'Weekly' },
];

const COMBINATION_MODES: { value: CombinationMode; label: string; description: string }[] = [
  {
    value: 'and',
    label: 'AND (Unanimous)',
    description: 'Enter when every leg is Buy; exit when every leg is Sell.',
  },
  {
    value: 'or',
    label: 'OR (Any)',
    description:
      'Enter when any leg is Buy; exit when any leg is Sell. Sell wins if legs disagree.',
  },
  {
    value: 'majority',
    label: 'Majority Vote',
    description: 'More Buy than Sell votes wins (Neutral abstains).',
  },
  {
    value: 'weighted',
    label: 'Weighted',
    description: 'Weighted Buy vs Sell votes with equal leg weights.',
  },
];

const inputCls =
  'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

const ALL_STRATEGY_VALUES = STRATEGIES.map((s) => s.value);

function buildStrategyParams(
  selected: string[],
): Record<string, Record<string, number>> {
  return Object.fromEntries(
    selected.map((s) => [s, { ...(DEFAULT_PARAMS_MAP[s] ?? {}) }]),
  );
}

interface ComboMatrixTabProps {
  assets: AssetItem[];
}

export default function ComboMatrixTab({ assets }: ComboMatrixTabProps) {
  const dailyDefaults = defaultDatesForTimeframe('1d');
  const [symbol, setSymbol] = useState('');
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([
    'ma_crossover',
    'rsi',
    'macd',
  ]);
  const [metric, setMetric] = useState<ComboMatrixMetric>('sharpe_ratio');
  const [timeframe, setTimeframe] = useState<MatrixTimeframe>('1d');
  const [startDate, setStartDate] = useState(dailyDefaults.start);
  const [endDate, setEndDate] = useState(dailyDefaults.end);
  const [mode, setMode] = useState<CombinationMode>('majority');
  const [threshold, setThreshold] = useState(0.5);
  const [result, setResult] = useState<ComboMatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [confirmAll, setConfirmAll] = useState(false);

  useEffect(() => {
    if (assets.length > 0 && !symbol) setSymbol(assets[0].symbol);
  }, [assets, symbol]);

  useEffect(() => {
    if (!loading) return;
    const t0 = Date.now();
    const id = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - t0) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, [loading]);

  const handleTimeframeChange = (tf: MatrixTimeframe) => {
    setTimeframe(tf);
    const dates = defaultDatesForTimeframe(tf);
    setStartDate(dates.start);
    setEndDate(dates.end);
  };

  const handleSelectAll = () => {
    if (!confirmAll) {
      setConfirmAll(true);
      return;
    }
    setSelectedStrategies([...ALL_STRATEGY_VALUES]);
    setConfirmAll(false);
  };

  const runMatrix = async () => {
    if (!symbol || selectedStrategies.length < 2) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setElapsedSec(0);

    try {
      const resp = await backtestApi.runComboMatrix({
        symbol,
        strategies: selectedStrategies,
        combination_mode: mode,
        threshold,
        metric,
        timeframe,
        start_date: new Date(startDate).toISOString(),
        end_date: new Date(endDate).toISOString(),
        initial_capital: 100_000,
        strategy_params: buildStrategyParams(selectedStrategies),
      });
      setResult(resp);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Matrix run failed');
    } finally {
      setLoading(false);
    }
  };

  const isFullCatalog = selectedStrategies.length >= ALL_STRATEGY_VALUES.length - 2;
  const activeMode = COMBINATION_MODES.find((m) => m.value === mode);

  return (
    <div className="space-y-6">
      <div className="card">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">Strategy combination matrix</h2>
        <p className="text-slate-400 text-sm mb-4">
          Compare every pair of strategies combined simultaneously. Diagonal cells show solo
          strategy performance; off-diagonal cells show the combined backtest metric.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="metric-label block mb-1">Ticker</label>
            <select
              aria-label="Ticker"
              className={inputCls}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={assets.length === 0}
            >
              {assets.map((a) => (
                <option key={a.id} value={a.symbol}>
                  {formatAssetOptionLabel(a)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="metric-label block mb-1">Metric</label>
            <select
              aria-label="Metric"
              className={inputCls}
              value={metric}
              onChange={(e) => setMetric(e.target.value as ComboMatrixMetric)}
            >
              {OPTIMIZE_METRICS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="matrix-price-frequency" className="metric-label block mb-1">
              Price Frequency
            </label>
            <select
              id="matrix-price-frequency"
              className={inputCls}
              value={timeframe}
              onChange={(e) => handleTimeframeChange(e.target.value as MatrixTimeframe)}
            >
              {TIMEFRAME_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            {INTRADAY_TIMEFRAMES.has(timeframe) && (
              <p className="text-slate-500 text-xs mt-1">
                Aggregated from 5m bars. Date range auto-adjusted.
              </p>
            )}
          </div>

          <div>
            <label className="metric-label block mb-1">Combination Mode</label>
            <select
              aria-label="Combination mode"
              className={inputCls}
              value={mode}
              onChange={(e) => setMode(e.target.value as CombinationMode)}
            >
              {COMBINATION_MODES.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
            {activeMode && (
              <p className="text-slate-500 text-xs mt-1">{activeMode.description}</p>
            )}
          </div>

          <div>
            <label className="metric-label block mb-1">Start Date</label>
            <input
              type="date"
              className={inputCls}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div>
            <label className="metric-label block mb-1">End Date</label>
            <input
              type="date"
              className={inputCls}
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          {mode === 'weighted' && (
            <div>
              <label className="metric-label block mb-1">Threshold (0–1)</label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.05}
                className={`${inputCls} w-24`}
                value={threshold}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  if (!isNaN(v)) setThreshold(Math.min(1, Math.max(0, v)));
                }}
              />
            </div>
          )}
        </div>

        <StrategyMultiSelect
          selected={selectedStrategies}
          onChange={(next) => {
            setSelectedStrategies(next);
            setConfirmAll(false);
          }}
        />

        {confirmAll && (
          <p className="text-amber-400 text-xs mt-2">
            Full catalog ({ALL_STRATEGY_VALUES.length} strategies) may take several minutes.
            Click &quot;Run all strategies&quot; again to confirm.
          </p>
        )}

        {isFullCatalog && !confirmAll && (
          <p className="text-amber-400 text-xs mt-2">
            Large selection: matrix run may take several minutes.
          </p>
        )}

        <div className="flex flex-wrap gap-3 mt-4">
          <button
            type="button"
            className="btn-secondary text-sm"
            onClick={handleSelectAll}
          >
            {confirmAll ? 'Confirm run all strategies' : 'Run all strategies'}
          </button>
          <button
            type="button"
            className="btn-primary"
            disabled={loading || !symbol || selectedStrategies.length < 2}
            onClick={runMatrix}
          >
            {loading ? 'Running matrix…' : 'Run matrix'}
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex flex-col items-center gap-2 py-8">
          <Spinner />
          <p className="text-slate-400 text-sm">
            Computing {selectedStrategies.length}×{selectedStrategies.length} cells…
            {elapsedSec > 0 && ` (${elapsedSec}s)`}
          </p>
        </div>
      )}

      {error && <ErrorAlert message={error} />}

      {result && !loading && (
        <StrategyHeatmap
          strategies={result.strategies}
          values={result.values}
          metric={metric}
          combinationMode={result.combination_mode}
        />
      )}
    </div>
  );
}
