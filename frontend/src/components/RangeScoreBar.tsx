interface RangeScoreBarProps {
  label: string;
  value: number | null;
  min: number;
  max: number;
}

export default function RangeScoreBar({ label, value, min, max }: RangeScoreBarProps) {
  const midpoint = (min + max) / 2;
  const span = max - min;
  const threshold = span * 0.15;

  const pct =
    value !== null
      ? Math.min(100, Math.max(0, ((value - min) / span) * 100))
      : null;

  const color =
    value === null
      ? 'bg-slate-500'
      : value > midpoint + threshold
      ? 'bg-green-500'
      : value < midpoint - threshold
      ? 'bg-red-500'
      : 'bg-yellow-500';

  const dotBorderColor =
    value === null
      ? 'border-slate-500'
      : value > midpoint + threshold
      ? 'border-green-500'
      : value < midpoint - threshold
      ? 'border-red-500'
      : 'border-yellow-500';

  const minLabel = min === 0 ? '0' : min.toFixed(1);
  const maxLabel = `+${max.toFixed(1)}`.replace('+-', '-');

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-300 font-mono">
          {value !== null ? value.toFixed(2) : '—'}
        </span>
      </div>

      <div className="relative h-2 bg-slate-700 rounded-full">
        {pct !== null && (
          <>
            <div
              className={`${color} h-full rounded-full transition-all duration-500`}
              style={{ width: `${pct}%` }}
            />
            <div
              className={`absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-slate-900 border-2 ${dotBorderColor} transition-all duration-500`}
              style={{ left: `calc(${pct}% - 6px)` }}
            />
          </>
        )}
      </div>

      <div className="flex justify-between text-xs text-slate-500">
        <span>{minLabel}</span>
        <span>{maxLabel}</span>
      </div>
    </div>
  );
}
