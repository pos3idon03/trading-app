import type { StrategyFeatureOption } from '../../utils/mlStrategyFeatures';

interface MlAlgoStrategyFeaturesPickerProps {
  options: StrategyFeatureOption[];
  selectedIds: string[];
  onToggle: (strategyId: string) => void;
  loading?: boolean;
  disabled?: boolean;
}

export default function MlAlgoStrategyFeaturesPicker({
  options,
  selectedIds,
  onToggle,
  loading = false,
  disabled = false,
}: MlAlgoStrategyFeaturesPickerProps) {
  const selected = new Set(selectedIds);

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-slate-300">Algo strategy features</h3>
      <p className="text-xs text-slate-500">
        Optional ensemble-eligible algo signals merge on top of OHLCV price features in every
        feature mode (prices_only, macro, fundamentals).
      </p>
      {loading ? (
        <p className="text-xs text-slate-500">Loading strategies…</p>
      ) : options.length === 0 ? (
        <p className="text-xs text-slate-500">Strategy catalog unavailable.</p>
      ) : (
        <div className="flex flex-wrap gap-3">
          {options.map((strategy) => (
            <label
              key={strategy.id}
              className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selected.has(strategy.id)}
                disabled={disabled}
                onChange={() => onToggle(strategy.id)}
              />
              {strategy.label}
            </label>
          ))}
        </div>
      )}
      {selectedIds.length > 0 && (
        <p className="text-xs text-slate-500">
          Columns use the pattern strat_(strategy_id)_signal and strat_(strategy_id)_cont_*.
        </p>
      )}
    </div>
  );
}
