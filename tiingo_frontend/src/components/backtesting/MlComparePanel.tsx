import type { MlCompareResult } from '../../api/mlBacktestTypes';
import { formatMetricPercent, formatOosAccuracy } from '../../utils/mlBacktestConfig';

interface MlComparePanelProps {
  results: MlCompareResult[];
}

export default function MlComparePanel({ results }: MlComparePanelProps) {
  if (results.length === 0) {
    return null;
  }

  return (
    <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-3">
      <h2 className="text-lg font-semibold text-slate-200">Feature mode comparison</h2>
      <div className="overflow-x-auto border border-slate-800 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-950 text-slate-400">
            <tr>
              <th className="px-3 py-2 text-left">Feature mode</th>
              <th className="px-3 py-2 text-right">Mean OOS acc.</th>
              <th className="px-3 py-2 text-right">F1</th>
              <th className="px-3 py-2 text-right">Total return</th>
              <th className="px-3 py-2 text-right">Sharpe</th>
              <th className="px-3 py-2 text-right">Signals (B/S/H)</th>
              <th className="px-3 py-2 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {results.map((item) => {
              const summary = item.run?.ml_summary;
              const metrics = item.run?.metrics;
              const counts = summary?.signal_counts ?? {};
              return (
                <tr key={item.featureMode} className="border-t border-slate-800">
                  <td className="px-3 py-2 text-slate-200">{item.label}</td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {formatOosAccuracy(summary?.mean_oos_accuracy)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {formatMetricPercent(summary?.f1 ?? null)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {metrics?.total_return_pct != null
                      ? `${metrics.total_return_pct.toFixed(2)}%`
                      : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {metrics?.sharpe_ratio?.toFixed(2) ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {counts.buy ?? 0}/{counts.sell ?? 0}/{counts.hold ?? 0}
                  </td>
                  <td className="px-3 py-2 text-slate-400">
                    {item.error ?? item.run?.status ?? '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
