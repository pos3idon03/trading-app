interface MetricCardProps {
  label: string;
  value: string | number | null | undefined;
  suffix?: string;
  positive?: boolean;
  negative?: boolean;
}

export default function MetricCard({ label, value, suffix = '', positive, negative }: MetricCardProps) {
  const colorClass = positive ? 'positive' : negative ? 'negative' : 'neutral';

  return (
    <div className="card flex flex-col gap-1">
      <span className="metric-label">{label}</span>
      <span className={`metric-value ${colorClass}`}>
        {value !== null && value !== undefined ? `${value}${suffix}` : '—'}
      </span>
    </div>
  );
}
