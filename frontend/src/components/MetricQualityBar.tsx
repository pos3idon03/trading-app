import { getMetricFill, getMetricTier } from '../utils/metricQuality';

export type MetricQualityKind = 'sharpe' | 'profit_factor';

interface MetricQualityBarProps {
  label: string;
  value: number | null | undefined;
  formattedValue: string;
  kind: MetricQualityKind;
}

export default function MetricQualityBar({
  label,
  value,
  formattedValue,
  kind,
}: MetricQualityBarProps) {
  const tier = getMetricTier(kind, value);
  const fill = getMetricFill(kind, value);
  const hasValue = fill !== null;
  const fillPct = hasValue ? Math.round(fill * 100) : 0;
  const displayValue = hasValue ? formattedValue : '—';
  const ariaLabel = hasValue
    ? `${label}: ${formattedValue}, ${tier?.label ?? ''}`
    : `${label}: no data`;

  return (
    <div
      className="card flex flex-col gap-1.5"
      role="meter"
      aria-label={ariaLabel}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={hasValue ? fillPct : undefined}
      title={tier?.label}
    >
      <div className="flex items-baseline justify-between gap-2">
        <span className="metric-label">{label}</span>
        <span className={`metric-value text-sm ${hasValue ? 'text-slate-200' : 'neutral'}`}>
          {displayValue}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-slate-700/80 overflow-hidden" aria-hidden>
        {hasValue && (
          <div
            className={`h-full rounded-full transition-all duration-300 ${tier?.barClass ?? 'bg-slate-500'}`}
            style={{ width: `${fillPct}%` }}
          />
        )}
      </div>
    </div>
  );
}
