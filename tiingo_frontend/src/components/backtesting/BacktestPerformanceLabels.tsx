import type { BacktestMetrics } from '../../api/backtestTypes';
import {
  performanceLabelClass,
  summarizePerformanceLabels,
} from '../../utils/backtestData';

interface BacktestPerformanceLabelsProps {
  metrics?: BacktestMetrics | null;
}

export default function BacktestPerformanceLabels({ metrics }: BacktestPerformanceLabelsProps) {
  const rows = summarizePerformanceLabels(metrics);

  if (!rows.length) {
    return null;
  }

  const showTradeHint = metrics?.trade_count === 0;

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium text-slate-300">Risk-adjusted performance</h3>
      <div className="flex flex-wrap gap-2">
        {rows.map((row) => (
          <div
            key={row.key}
            className={`rounded-lg border px-3 py-2 min-w-[7.5rem] text-center ${performanceLabelClass(row.tone)}`}
          >
            <p className="text-sm font-semibold">{row.value}</p>
            <p className="text-[11px] mt-0.5 opacity-80">{row.label}</p>
          </div>
        ))}
      </div>
      {showTradeHint && (
        <p className="text-xs text-slate-500">
          Profit factor and win rate require at least one closed trade.
        </p>
      )}
    </div>
  );
}
