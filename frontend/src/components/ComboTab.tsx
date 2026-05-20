import { useEffect, useMemo, useState } from 'react';
import { backtestApi, strategyBuilderApi } from '../api/endpoints';
import type { AssetItem, BacktestResponse, CombinationMode, ComboStrategySignal } from '../api/types';
import { STRATEGIES, DEFAULT_PARAMS_MAP } from '../constants/strategies';
import BacktestResultCard from './BacktestResultCard';
import { ComboSignalTimeline } from './ComboSignalTimeline';
import ErrorAlert from './ErrorAlert';
import Spinner from './Spinner';
import StrategyParamsEditor from './StrategyParamsEditor';
import { formatAssetOptionLabel } from '../utils/assetDisplay';
import { defaultDatesForTimeframe } from '../utils/backtestDates';
import type { BacktestTimeframe } from '../utils/backtestDates';
import { finestTimeframe } from '../utils/timelineAlignment';
import { isIntradayTimeframe } from './ComboSignalTimeline';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ComboTimeframe = BacktestTimeframe;

const TIMEFRAME_OPTIONS: { value: ComboTimeframe; label: string }[] = [
  { value: '5m',  label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '30m', label: '30 Min' },
  { value: '1h',  label: '1 Hour' },
  { value: '4h',  label: '4 Hours' },
  { value: '1d',  label: 'Daily' },
  { value: '1w',  label: 'Weekly' },
];

interface ComboEntry {
  id: string;
  strategy_name: string;
  weight: number;
  timeframe: ComboTimeframe;
}

const COMBINATION_MODES: { value: CombinationMode; label: string; description: string }[] = [
  {
    value: 'and',
    label: 'AND (Unanimous)',
    description:
      'Enter when every leg is Buy; exit when every leg is Sell. Mixed or Neutral legs hold the current position.',
  },
  {
    value: 'or',
    label: 'OR (Any)',
    description:
      'Enter when any leg is Buy; exit when any leg is Sell. If one leg is Sell and another Buy on the same bar, exit (Sell wins).',
  },
  {
    value: 'majority',
    label: 'Majority Vote',
    description:
      'More Buy than Sell votes wins (Neutral abstains). Ties keep the current combined position.',
  },
  {
    value: 'weighted',
    label: 'Weighted',
    description:
      'Weighted Buy vs Sell votes (Neutral abstains). In the hold band between thresholds, position is unchanged.',
  },
];

// ---------------------------------------------------------------------------
// Small sub-components
// ---------------------------------------------------------------------------

function ModeSelector({
  value,
  onChange,
}: {
  value: CombinationMode;
  onChange: (m: CombinationMode) => void;
}) {
  const selectCls =
    'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

  const active = COMBINATION_MODES.find((m) => m.value === value);

  return (
    <div className="space-y-1">
      <label htmlFor="combo-combination-mode" className="metric-label block mb-1">
        Combination Mode
      </label>
      <select
        id="combo-combination-mode"
        aria-label="Combination Mode"
        className={selectCls}
        value={value}
        onChange={(e) => onChange(e.target.value as CombinationMode)}
      >
        {COMBINATION_MODES.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>
      {active && (
        <p className="text-slate-500 text-xs mt-1">{active.description}</p>
      )}
    </div>
  );
}

function ThresholdInput({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  const inputCls =
    'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 w-24';
  return (
    <div>
      <label htmlFor="combo-threshold" className="metric-label block mb-1">
        Threshold
        <span className="text-slate-500 font-normal ml-1">(0–1)</span>
      </label>
      <input
        id="combo-threshold"
        type="number"
        min={0}
        max={1}
        step={0.05}
        className={inputCls}
        value={value}
        onChange={(e) => {
          const v = parseFloat(e.target.value);
          if (!isNaN(v)) onChange(Math.min(1, Math.max(0, v)));
        }}
      />
    </div>
  );
}

function StrategyRow({
  entry,
  isWeighted,
  onWeightChange,
  onTimeframeChange,
  onRemove,
}: {
  entry: ComboEntry;
  isWeighted: boolean;
  onWeightChange: (id: string, w: number) => void;
  onTimeframeChange: (id: string, tf: ComboTimeframe) => void;
  onRemove: (id: string) => void;
}) {
  const label =
    STRATEGIES.find((s) => s.value === entry.strategy_name)?.label ?? entry.strategy_name;

  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-700 last:border-0 flex-wrap">
      <span className="text-sm text-slate-200 flex-1 min-w-[120px] truncate">{label}</span>

      <div className="flex items-center gap-2 shrink-0">
        <label className="text-xs text-slate-400 whitespace-nowrap">Signal TF</label>
        <select
          className="bg-surface-900 border border-slate-600 rounded px-2 py-1 text-xs text-slate-100 focus:outline-none focus:border-brand-500"
          value={entry.timeframe}
          onChange={(e) => onTimeframeChange(entry.id, e.target.value as ComboTimeframe)}
          aria-label={`Signal timeframe for ${label}`}
        >
          {TIMEFRAME_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {isWeighted && (
        <div className="flex items-center gap-2 shrink-0">
          <label className="text-xs text-slate-400 whitespace-nowrap">Weight</label>
          <input
            type="number"
            min={0}
            max={1}
            step={0.1}
            aria-label={`Weight for ${label}`}
            className="bg-surface-900 border border-slate-600 rounded px-2 py-1 text-xs text-slate-100 focus:outline-none focus:border-brand-500 w-16"
            value={entry.weight}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!isNaN(v)) onWeightChange(entry.id, Math.min(1, Math.max(0, v)));
            }}
          />
        </div>
      )}

      <button
        type="button"
        aria-label={`Remove ${label}`}
        onClick={() => onRemove(entry.id)}
        className="text-slate-500 hover:text-red-400 transition-colors text-xs shrink-0"
      >
        ✕
      </button>
    </div>
  );
}

function AddStrategySelect({
  onAdd,
  existing,
}: {
  onAdd: (strategyValue: string) => void;
  existing: string[];
}) {
  const [selected, setSelected] = useState('');
  const selectCls =
    'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

  const available = STRATEGIES.filter((s) => !existing.includes(s.value));

  const handleAdd = () => {
    if (!selected || existing.includes(selected)) return;
    onAdd(selected);
    setSelected('');
  };

  return (
    <div className="flex items-center gap-2 mt-3">
      <select
        aria-label="Add strategy"
        className={selectCls}
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        disabled={available.length === 0}
      >
        <option value="">Add strategy…</option>
        {available.map((s) => (
          <option key={s.value} value={s.value}>
            {s.label}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={handleAdd}
        disabled={!selected}
        className="btn-primary text-xs px-3 py-2 disabled:opacity-40"
      >
        Add
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main ComboTab component
// ---------------------------------------------------------------------------

interface ComboTabProps {
  assets: AssetItem[];
}

function buildParamsMap(
  entries: ComboEntry[],
  prev: Record<string, Record<string, number>>,
): Record<string, Record<string, number>> {
  const next: Record<string, Record<string, number>> = {};
  for (const e of entries) {
    next[e.strategy_name] = prev[e.strategy_name] ?? { ...(DEFAULT_PARAMS_MAP[e.strategy_name] ?? {}) };
  }
  return next;
}

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

const inputCls =
  'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

export default function ComboTab({ assets }: ComboTabProps) {
  const [symbol, setSymbol] = useState('');
  const comboDailyDefaults = defaultDatesForTimeframe('1d');
  const [startDate, setStartDate] = useState(comboDailyDefaults.start);
  const [endDate, setEndDate] = useState(comboDailyDefaults.end);
  const [entries, setEntries] = useState<ComboEntry[]>([
    { id: makeId(), strategy_name: 'ma_crossover', weight: 1.0, timeframe: '1d' },
    { id: makeId(), strategy_name: 'rsi', weight: 1.0, timeframe: '1d' },
  ]);
  const [paramsMap, setParamsMap] = useState<Record<string, Record<string, number>>>(
    buildParamsMap(
      [
        { id: '', strategy_name: 'ma_crossover', weight: 1.0 },
        { id: '', strategy_name: 'rsi', weight: 1.0 },
      ],
      {},
    ),
  );
  const [mode, setMode] = useState<CombinationMode>('majority');
  const [threshold, setThreshold] = useState(0.5);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [comboSignals, setComboSignals] = useState<ComboStrategySignal[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const executionTimeframe = useMemo(
    () => finestTimeframe(entries.map((e) => e.timeframe)),
    [entries],
  );

  useEffect(() => {
    if (assets.length > 0 && !symbol) setSymbol(assets[0].symbol);
  }, [assets, symbol]);

  useEffect(() => {
    const dates = defaultDatesForTimeframe(executionTimeframe as ComboTimeframe);
    setStartDate(dates.start);
    setEndDate(dates.end);
  }, [executionTimeframe]);

  const handleLegTimeframeChange = (id: string, tf: ComboTimeframe) => {
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, timeframe: tf } : e)));
  };

  const handleAddStrategy = (strategyValue: string) => {
    const newEntry: ComboEntry = {
      id: makeId(),
      strategy_name: strategyValue,
      weight: 1.0,
      timeframe: '1d',
    };
    const next = [...entries, newEntry];
    setEntries(next);
    setParamsMap((prev) => buildParamsMap(next, prev));
  };

  const handleRemoveStrategy = (id: string) => {
    if (entries.length <= 2) return;
    const next = entries.filter((e) => e.id !== id);
    setEntries(next);
    setParamsMap((prev) => buildParamsMap(next, prev));
  };

  const handleWeightChange = (id: string, w: number) => {
    setEntries((prev) => prev.map((e) => (e.id === id ? { ...e, weight: w } : e)));
  };

  const runCombo = async () => {
    if (!symbol || entries.length < 2) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setComboSignals(null);

    const comboRequest = {
      symbol,
      strategies: entries.map((e) => ({
        strategy_name: e.strategy_name,
        strategy_params: paramsMap[e.strategy_name] ?? DEFAULT_PARAMS_MAP[e.strategy_name] ?? {},
        weight: e.weight,
        timeframe: e.timeframe,
      })),
      combination_mode: mode,
      threshold,
      timeframe: executionTimeframe,
      start_date: new Date(startDate).toISOString(),
      end_date: new Date(endDate).toISOString(),
      initial_capital: 100_000,
    };

    try {
      const [resp, signalsResp] = await Promise.all([
        backtestApi.runCombo(comboRequest),
        backtestApi.getComboSignals(comboRequest),
      ]);
      setResult(resp);
      setComboSignals(signalsResp.strategies);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const selectedStrategyValues = entries.map((e) => e.strategy_name);

  return (
    <div className="space-y-6">
      {error && <ErrorAlert message={error} />}

      <div className="card">
        <h2 className="text-slate-200 font-semibold mb-1">Combination Configuration</h2>
        <p className="text-slate-400 text-xs mb-4">
          Select 2 or more strategies and a combination mode to generate a single blended signal.
        </p>

        {/* Ticker / dates / timeframe */}
        <div className="flex flex-wrap gap-4 items-start mb-6">
          <div>
            <label htmlFor="combo-ticker" className="metric-label block mb-1">Ticker</label>
            <select
              id="combo-ticker"
              aria-label="Ticker"
              className={inputCls}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
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
        </div>
        <p className="text-slate-500 text-xs mb-4">
          Combined backtest aligns on{' '}
          <span className="text-slate-300 font-mono">{executionTimeframe}</span>
          {' '}(finest signal timeframe).
          {isIntradayTimeframe(executionTimeframe) && ' Intraday bars are aggregated from 5m data.'}
        </p>

        {/* Combination mode + threshold */}
        <div className="flex flex-wrap gap-6 items-start mb-6">
          <ModeSelector value={mode} onChange={setMode} />
          {mode === 'weighted' && (
            <ThresholdInput value={threshold} onChange={setThreshold} />
          )}
        </div>

        {/* Strategy list */}
        <div className="mb-4">
          <label className="metric-label block mb-2">
            Strategies
            <span className="text-slate-500 font-normal ml-1">(min 2)</span>
          </label>

          <div className="border border-slate-700 rounded-lg px-3 py-1">
            {entries.map((entry) => (
              <StrategyRow
                key={entry.id}
                entry={entry}
                isWeighted={mode === 'weighted'}
                onWeightChange={handleWeightChange}
                onTimeframeChange={handleLegTimeframeChange}
                onRemove={handleRemoveStrategy}
              />
            ))}
          </div>

          <AddStrategySelect onAdd={handleAddStrategy} existing={selectedStrategyValues} />
        </div>

        {/* Per-strategy params */}
        <div className="mb-6">
          <StrategyParamsEditor
            selectedStrategies={selectedStrategyValues}
            paramsMap={paramsMap}
            onChange={setParamsMap}
          />
        </div>

        <button
          onClick={runCombo}
          disabled={loading || !symbol || entries.length < 2}
          className="btn-primary disabled:opacity-50"
        >
          {loading
            ? 'Running combo backtest…'
            : `Run Combo Backtest (${entries.length} strategies, ${COMBINATION_MODES.find((m) => m.value === mode)?.label})`}
        </button>
      </div>

      {loading && <Spinner label="Running combination backtest…" />}

      {result && !loading && (
        <div className="space-y-6">
          <div>
            <h3 className="text-slate-300 text-sm font-medium mb-3">Combo Result</h3>
            <BacktestResultCard
              result={result}
              syncId="combo-sync"
              attachTimeframe={executionTimeframe}
              onAddToStrategy={async (strategyName, params, assetId, tf) => {
                const entry = entries.find((e) => e.strategy_name === strategyName);
                const legTf = entry?.timeframe ?? tf;
                const attachParams =
                  strategyName.startsWith('combo:')
                    ? {
                        ...params,
                        strategies: (params.strategies as Array<Record<string, unknown>> | undefined)?.map(
                          (leg) => {
                            const legEntry = entries.find(
                              (e) => e.strategy_name === leg.strategy_name,
                            );
                            return { ...leg, timeframe: legEntry?.timeframe ?? leg.timeframe ?? legTf };
                          },
                        ) ?? params.strategies,
                      }
                    : params;
                await strategyBuilderApi.attachAlgo({
                  asset_id: assetId,
                  strategy_name: strategyName,
                  params: attachParams,
                  timeframe: strategyName.startsWith('combo:') ? executionTimeframe : legTf,
                });
              }}
            />
          </div>

          {comboSignals && comboSignals.length > 0 && (
            <div className="space-y-6">
              <ComboSignalTimeline
                strategies={comboSignals}
                syncId="combo-sync"
                alignmentTimeframe={executionTimeframe}
                intraday={isIntradayTimeframe(executionTimeframe)}
              />

              <div>
                <h3 className="text-slate-300 text-sm font-semibold mb-3">Individual Strategy Results</h3>
                <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                  {comboSignals.map((s) => {
                    const legEntry = entries.find((e) => e.strategy_name === s.strategy_name);
                    return (
                    <BacktestResultCard
                      key={s.strategy_name}
                      syncId="combo-sync"
                      attachTimeframe={legEntry?.timeframe ?? '1d'}
                      onAddToStrategy={async (strategyName, params, assetId, legTf) => {
                        await strategyBuilderApi.attachAlgo({
                          asset_id: assetId,
                          strategy_name: strategyName,
                          params,
                          timeframe: legTf,
                        });
                      }}
                      result={{
                        asset_id: result.asset_id,
                        strategy_name: s.strategy_name,
                        status: 'done',
                        equity_curve: s.equity_curve,
                        buy_hold_curve: s.buy_hold_curve,
                        trade_log: s.trade_log,
                        indicator_series: s.indicator_series,
                      }}
                    />
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
