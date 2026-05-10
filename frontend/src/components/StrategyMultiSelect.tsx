import { STRATEGIES, STRATEGY_GROUPS } from '../constants/strategies';

interface StrategyMultiSelectProps {
  selected: string[];
  onChange: (selected: string[]) => void;
}

function GroupSection({
  group,
  selected,
  onToggle,
}: {
  group: string;
  selected: string[];
  onToggle: (value: string) => void;
}) {
  const groupStrategies = STRATEGIES.filter((s) => s.group === group);
  return (
    <div className="mb-2">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-1 mb-1">{group}</p>
      {groupStrategies.map((s) => (
        <label
          key={s.value}
          className="flex items-center gap-2 px-1 py-0.5 rounded hover:bg-surface-700 cursor-pointer"
        >
          <input
            type="checkbox"
            className="accent-brand-500 w-3.5 h-3.5 shrink-0"
            checked={selected.includes(s.value)}
            onChange={() => onToggle(s.value)}
          />
          <span className="text-xs text-slate-200">{s.label}</span>
        </label>
      ))}
    </div>
  );
}

export default function StrategyMultiSelect({ selected, onChange }: StrategyMultiSelectProps) {
  const toggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((s) => s !== value));
    } else {
      onChange([...selected, value]);
    }
  };

  const selectAll = () => onChange(STRATEGIES.map((s) => s.value));
  const clearAll = () => onChange([]);

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="metric-label">
          Strategies{' '}
          <span className="text-brand-400 font-semibold">({selected.length} selected)</span>
        </label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={selectAll}
            className="text-xs text-slate-400 hover:text-slate-100 transition-colors"
          >
            All
          </button>
          <span className="text-slate-600">|</span>
          <button
            type="button"
            onClick={clearAll}
            className="text-xs text-slate-400 hover:text-slate-100 transition-colors"
          >
            None
          </button>
        </div>
      </div>
      <div className="max-h-52 overflow-y-auto border border-slate-600 rounded-lg p-2 bg-surface-900">
        {STRATEGY_GROUPS.map((group) => (
          <GroupSection key={group} group={group} selected={selected} onToggle={toggle} />
        ))}
      </div>
    </div>
  );
}
