import type { OptimizationSummary } from '../api/types';

interface OptimizationResultsTableProps {
  results: OptimizationSummary[];
  metric: string;
}

function MetricBar({ value, max, isInf }: { value: number; max: number; isInf: boolean }) {
  const pct = isInf ? 0 : Math.max(0, value / max);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 rounded-full bg-slate-700 flex-1 overflow-hidden">
        <div
          className={`h-full rounded-full ${isInf ? 'bg-slate-600' : 'bg-brand-500'}`}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
      <span className={`font-mono w-16 text-right ${isInf ? 'text-slate-500' : 'text-slate-300'}`}>
        {isInf ? '—' : value.toFixed(4)}
      </span>
    </div>
  );
}

export default function OptimizationResultsTable({ results, metric }: OptimizationResultsTableProps) {
  const sorted = [...results].sort((a, b) => b.avg_oos_metric - a.avg_oos_metric);
  const max = sorted[0]?.avg_oos_metric ?? 1;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs text-left">
        <thead>
          <tr className="border-b border-slate-700">
            {sorted[0] &&
              Object.keys(sorted[0].params).map((k) => (
                <th key={k} className="px-3 py-2 text-slate-400 font-medium">{k}</th>
              ))}
            <th className="px-3 py-2 text-slate-400 font-medium">Avg OOS {metric}</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const isInf = !isFinite(row.avg_oos_metric);
            return (
              <tr key={i} className={`border-b border-slate-800 ${i === 0 ? 'bg-brand-500/10' : ''}`}>
                {Object.values(row.params).map((v, j) => (
                  <td key={j} className="px-3 py-2 font-mono text-slate-200">{String(v)}</td>
                ))}
                <td className="px-3 py-2">
                  <MetricBar value={row.avg_oos_metric} max={max} isInf={isInf} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
