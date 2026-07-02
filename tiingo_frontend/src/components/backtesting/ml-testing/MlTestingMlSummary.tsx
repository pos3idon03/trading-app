import type { MlSummary } from '../../../api/mlBacktestTypes';
import { formatMetricPercent, formatOosAccuracy } from '../../../utils/mlBacktestConfig';

interface MlTestingMlSummaryProps {
  summary: MlSummary;
}

function formatSignalCounts(counts: Record<string, number> | undefined): string {
  if (!counts) {
    return '—';
  }
  const buy = counts.buy ?? 0;
  const sell = counts.sell ?? 0;
  const hold = counts.hold ?? 0;
  return `buy ${buy} · sell ${sell} · hold ${hold}`;
}

export default function MlTestingMlSummary({ summary }: MlTestingMlSummaryProps) {
  const zeroBuys = (summary.signal_counts?.buy ?? 0) === 0;

  return (
    <section className="space-y-3 rounded-lg border border-slate-800 bg-surface-950/40 p-3">
      <h3 className="text-sm font-medium text-slate-300">ML summary</h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div>
          <p className="text-slate-500">OOS windows</p>
          <p className="text-slate-200">{summary.oos_window_count}</p>
        </div>
        <div>
          <p className="text-slate-500">Mean OOS accuracy</p>
          <p className="text-slate-200">{formatOosAccuracy(summary.mean_oos_accuracy)}</p>
        </div>
        <div>
          <p className="text-slate-500">Precision / Recall / F1</p>
          <p className="text-slate-200">
            {formatMetricPercent(summary.precision)} /{' '}
            {formatMetricPercent(summary.recall)} / {formatMetricPercent(summary.f1)}
          </p>
        </div>
        <div>
          <p className="text-slate-500">Signals (simulation window)</p>
          <p className="text-slate-200">{formatSignalCounts(summary.signal_counts)}</p>
        </div>
      </div>
      {(summary.oos_window_count ?? 0) === 0 && (
        <p className="text-xs text-amber-200/90">
          No walk-forward folds trained (OOS windows = 0). Meta-label + LSTM needs several
          base-strategy entry events per train window — try Time-Series Momentum or SMA
          Crossover as base, lower LSTM sequence length in the ML wizard, extend the date range,
          or use binary/ternary label mode.
        </p>
      )}
      {zeroBuys && (summary.oos_window_count ?? 0) > 0 && (
        <p className="text-xs text-amber-200/90">
          No buy signals in the simulation window — the portfolio stayed flat. For meta-label,
          try a busier base strategy, lower the meta gate threshold, or switch to binary/ternary
          label mode.
        </p>
      )}
    </section>
  );
}

export { formatSignalCounts };
