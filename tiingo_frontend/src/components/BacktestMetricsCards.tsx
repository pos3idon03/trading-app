import type { BacktestMetrics } from '../api/backtestTypes';
import { metricCardClass, summarizeReturnMetrics } from '../utils/backtestData';

interface BacktestMetricsCardsProps {
  metrics?: BacktestMetrics | null;
}

export default function BacktestMetricsCards({ metrics }: BacktestMetricsCardsProps) {
  const rows = summarizeReturnMetrics(metrics);

  if (!rows.length) {
    return null;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {rows.map((row) => (
        <div key={row.key} className={`rounded-xl border p-4 ${metricCardClass(row.tone)}`}>
          <p className="text-lg font-bold text-center">{row.value}</p>
          <p className="text-xs mt-1 opacity-80 text-center">{row.label}</p>
        </div>
      ))}
    </div>
  );
}
