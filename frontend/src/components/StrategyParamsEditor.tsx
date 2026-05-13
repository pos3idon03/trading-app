import { useState } from 'react';
import { STRATEGIES, DEFAULT_PARAMS_MAP } from '../constants/strategies';

interface StrategyParamsEditorProps {
  selectedStrategies: string[];
  paramsMap: Record<string, Record<string, number>>;
  onChange: (paramsMap: Record<string, Record<string, number>>) => void;
}

function formatParamLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function StrategyParamSection({
  strategyValue,
  params,
  onParamChange,
  onReset,
}: {
  strategyValue: string;
  params: Record<string, number>;
  onParamChange: (key: string, value: number) => void;
  onReset: () => void;
}) {
  const [open, setOpen] = useState(true);
  const label = STRATEGIES.find((s) => s.value === strategyValue)?.label ?? strategyValue;
  const inputCls =
    'bg-surface-900 border border-slate-600 rounded px-2 py-1 text-xs text-slate-100 focus:outline-none focus:border-brand-500 w-24';

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-surface-800 hover:bg-surface-700 transition-colors text-left"
      >
        <span className="text-sm text-slate-200 font-medium">{label}</span>
        <div className="flex items-center gap-2">
          <span
            className="text-xs text-slate-500 hover:text-brand-400 transition-colors"
            onClick={(e) => { e.stopPropagation(); onReset(); }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); onReset(); } }}
          >
            Reset
          </span>
          <span className="text-slate-400 text-xs">{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div className="px-3 py-3 bg-surface-900 flex flex-wrap gap-4">
          {Object.entries(params).map(([key, value]) => {
            const inputId = `param-${strategyValue}-${key}`;
            return (
              <div key={key} className="flex flex-col gap-1">
                <label htmlFor={inputId} className="text-xs text-slate-400">
                  {formatParamLabel(key)}
                </label>
                <input
                  id={inputId}
                  type="number"
                  className={inputCls}
                  value={value}
                  step="any"
                  onChange={(e) => {
                    const parsed = parseFloat(e.target.value);
                    if (!isNaN(parsed)) onParamChange(key, parsed);
                  }}
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function StrategyParamsEditor({
  selectedStrategies,
  paramsMap,
  onChange,
}: StrategyParamsEditorProps) {
  if (selectedStrategies.length === 0) return null;

  const handleParamChange = (strategy: string, key: string, value: number) => {
    onChange({
      ...paramsMap,
      [strategy]: { ...paramsMap[strategy], [key]: value },
    });
  };

  const handleReset = (strategy: string) => {
    const defaults = DEFAULT_PARAMS_MAP[strategy] ?? {};
    onChange({ ...paramsMap, [strategy]: { ...defaults } });
  };

  return (
    <div>
      <label className="metric-label block mb-2">Strategy Parameters</label>
      <div className="space-y-2">
        {selectedStrategies.map((sv) => (
          <StrategyParamSection
            key={sv}
            strategyValue={sv}
            params={paramsMap[sv] ?? DEFAULT_PARAMS_MAP[sv] ?? {}}
            onParamChange={(key, value) => handleParamChange(sv, key, value)}
            onReset={() => handleReset(sv)}
          />
        ))}
      </div>
    </div>
  );
}
