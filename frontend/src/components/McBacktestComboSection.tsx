import type { CombinationMode, McBacktestTimeframe } from '../api/types';
import { DEFAULT_PARAMS_MAP, STRATEGIES } from '../constants/strategies';
import { MC_COMBINATION_MODES } from '../constants/monteCarlo';
import StrategyParamsEditor from './StrategyParamsEditor';
import type { BacktestTimeframe } from '../utils/backtestDates';

const TIMEFRAME_OPTIONS: { value: McBacktestTimeframe; label: string }[] = [
  { value: '5m', label: '5 Min' },
  { value: '15m', label: '15 Min' },
  { value: '30m', label: '30 Min' },
  { value: '1h', label: '1 Hour' },
  { value: '4h', label: '4 Hours' },
  { value: '1d', label: 'Daily' },
  { value: '1w', label: 'Weekly' },
];

export interface McComboEntry {
  id: string;
  strategy_name: string;
  weight: number;
  timeframe: McBacktestTimeframe;
}

export interface McComboConfig {
  enabled: boolean;
  mode: CombinationMode;
  threshold: number;
  mcLegWeight: number;
  entries: McComboEntry[];
  paramsMap: Record<string, Record<string, number>>;
}

export const DEFAULT_MC_COMBO_CONFIG: McComboConfig = {
  enabled: false,
  mode: 'and',
  threshold: 0.5,
  mcLegWeight: 1.0,
  entries: [],
  paramsMap: {},
};

const SELECT_CLS =
  'bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500';

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function buildParamsMap(
  entries: McComboEntry[],
  prev: Record<string, Record<string, number>>,
): Record<string, Record<string, number>> {
  const next: Record<string, Record<string, number>> = {};
  for (const e of entries) {
    next[e.strategy_name] = prev[e.strategy_name] ?? { ...(DEFAULT_PARAMS_MAP[e.strategy_name] ?? {}) };
  }
  return next;
}

function ModeSelector({
  value,
  onChange,
}: {
  value: CombinationMode;
  onChange: (m: CombinationMode) => void;
}) {
  const active = MC_COMBINATION_MODES.find((m) => m.value === value);
  return (
    <div className="space-y-1">
      <label htmlFor="mc-combo-mode" className="metric-label block mb-1">
        Combination Mode
      </label>
      <select
        id="mc-combo-mode"
        aria-label="Combination Mode"
        className={SELECT_CLS}
        value={value}
        onChange={(e) => onChange(e.target.value as CombinationMode)}
      >
        {MC_COMBINATION_MODES.map((m) => (
          <option key={m.value} value={m.value}>
            {m.label}
          </option>
        ))}
      </select>
      {active && <p className="text-slate-500 text-xs mt-1">{active.description}</p>}
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
  entry: McComboEntry;
  isWeighted: boolean;
  onWeightChange: (id: string, w: number) => void;
  onTimeframeChange: (id: string, tf: McBacktestTimeframe) => void;
  onRemove: (id: string) => void;
}) {
  const label = STRATEGIES.find((s) => s.value === entry.strategy_name)?.label ?? entry.strategy_name;
  return (
    <div className="flex items-center gap-3 py-2 border-b border-slate-700 last:border-0 flex-wrap">
      <span className="text-sm text-slate-200 flex-1 min-w-[120px] truncate">{label}</span>
      <div className="flex items-center gap-2 shrink-0">
        <label className="text-xs text-slate-400 whitespace-nowrap">Signal TF</label>
        <select
          className="bg-surface-900 border border-slate-600 rounded px-2 py-1 text-xs text-slate-100 focus:outline-none focus:border-brand-500"
          value={entry.timeframe}
          onChange={(e) => onTimeframeChange(entry.id, e.target.value as McBacktestTimeframe)}
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

interface McBacktestComboSectionProps {
  config: McComboConfig;
  onChange: (config: McComboConfig) => void;
  execTimeframe: McBacktestTimeframe;
}

export function validateMcComboConfig(config: McComboConfig): string | null {
  if (!config.enabled) return null;
  if (config.entries.length < 1) {
    return 'Add at least one algo strategy when Algo combo is enabled';
  }
  return null;
}

export default function McBacktestComboSection({
  config,
  onChange,
  execTimeframe,
}: McBacktestComboSectionProps) {
  const isWeighted = config.mode === 'weighted';
  const existing = config.entries.map((e) => e.strategy_name);

  const update = (patch: Partial<McComboConfig>) => onChange({ ...config, ...patch });

  const addStrategy = (strategyName: string) => {
    const entry: McComboEntry = {
      id: makeId(),
      strategy_name: strategyName,
      weight: 1.0,
      timeframe: execTimeframe,
    };
    const entries = [...config.entries, entry];
    update({
      entries,
      paramsMap: buildParamsMap(entries, config.paramsMap),
    });
  };

  const removeEntry = (id: string) => {
    const entries = config.entries.filter((e) => e.id !== id);
    update({ entries, paramsMap: buildParamsMap(entries, config.paramsMap) });
  };

  return (
    <div className="border border-slate-700 rounded-lg p-4 mb-4">
      <div className="flex items-center gap-3 mb-3">
        <input
          id="mc-combo-enabled"
          type="checkbox"
          checked={config.enabled}
          onChange={(e) => update({ enabled: e.target.checked })}
          className="rounded border-slate-600"
        />
        <label htmlFor="mc-combo-enabled" className="text-slate-200 font-medium text-sm">
          Algo combo
        </label>
      </div>
      <p className="text-slate-500 text-xs mb-3">
        MC prob is always leg 1; combined signal drives entries. Entry filters apply to the final combo signal.
      </p>

      {config.enabled && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4 items-end">
            <ModeSelector value={config.mode} onChange={(mode) => update({ mode })} />
            {isWeighted && (
              <>
                <div>
                  <label htmlFor="mc-combo-threshold" className="metric-label block mb-1">
                    Threshold
                    <span className="text-slate-500 font-normal ml-1">(0–1)</span>
                  </label>
                  <input
                    id="mc-combo-threshold"
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    className={`${SELECT_CLS} w-24`}
                    value={config.threshold}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      if (!isNaN(v)) update({ threshold: Math.min(1, Math.max(0, v)) });
                    }}
                  />
                </div>
                <div>
                  <label htmlFor="mc-leg-weight" className="metric-label block mb-1">
                    MC leg weight
                  </label>
                  <input
                    id="mc-leg-weight"
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    className={`${SELECT_CLS} w-24`}
                    value={config.mcLegWeight}
                    onChange={(e) => {
                      const v = parseFloat(e.target.value);
                      if (!isNaN(v)) update({ mcLegWeight: Math.min(1, Math.max(0, v)) });
                    }}
                  />
                </div>
              </>
            )}
          </div>

          <div>
            <p className="metric-label mb-2">Algo strategies (leg 2+)</p>
            {config.entries.length === 0 && (
              <p className="text-amber-400 text-xs mb-2">Add at least one strategy.</p>
            )}
            {config.entries.map((entry) => (
              <div key={entry.id} className="mb-3">
                <StrategyRow
                  entry={entry}
                  isWeighted={isWeighted}
                  onWeightChange={(id, weight) =>
                    update({
                      entries: config.entries.map((e) => (e.id === id ? { ...e, weight } : e)),
                    })
                  }
                  onTimeframeChange={(id, timeframe) =>
                    update({
                      entries: config.entries.map((e) => (e.id === id ? { ...e, timeframe } : e)),
                    })
                  }
                  onRemove={removeEntry}
                />
              </div>
            ))}
            {config.entries.length > 0 && (
              <StrategyParamsEditor
                selectedStrategies={config.entries.map((e) => e.strategy_name)}
                paramsMap={config.paramsMap}
                onChange={(paramsMap) => update({ paramsMap })}
              />
            )}
            <div className="flex items-center gap-2 mt-2">
              <select
                aria-label="Add algo strategy"
                className={SELECT_CLS}
                defaultValue=""
                onChange={(e) => {
                  const v = e.target.value;
                  if (v) addStrategy(v);
                  e.target.value = '';
                }}
              >
                <option value="">Add strategy…</option>
                {STRATEGIES.filter((s) => !existing.includes(s.value)).map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function comboConfigToRequestPayload(config: McComboConfig) {
  if (!config.enabled) return {};
  return {
    combo_enabled: true,
    combination_mode: config.mode,
    threshold: config.threshold,
    mc_leg_weight: config.mcLegWeight,
    algo_strategies: config.entries.map((e) => ({
      strategy_name: e.strategy_name,
      strategy_params: config.paramsMap[e.strategy_name] ?? {},
      weight: e.weight,
      timeframe: e.timeframe as BacktestTimeframe,
    })),
  };
}
