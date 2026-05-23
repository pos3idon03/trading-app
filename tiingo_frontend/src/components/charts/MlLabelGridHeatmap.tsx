import type { MlLabelSearchResult } from '../../api/mlBacktestTypes';
import { formatMetricPercent } from '../../utils/mlBacktestConfig';

interface MlLabelGridHeatmapProps {
  results: MlLabelSearchResult[];
}

function heatColor(value: number | null | undefined): string {
  if (value == null) {
    return 'rgb(30 41 59)';
  }
  const clamped = Math.max(0, Math.min(1, value));
  const red = Math.round(239 - clamped * 120);
  const green = Math.round(68 + clamped * 120);
  return `rgb(${red} ${green} 100)`;
}

export default function MlLabelGridHeatmap({ results }: MlLabelGridHeatmapProps) {
  if (!results.length) {
    return null;
  }

  const models = [...new Set(results.map((row) => row.model_label ?? row.model_type ?? '—'))];
  const horizons = [...new Set(results.map((row) => row.label_horizon))].sort((a, b) => a - b);
  const lookup = new Map<string, MlLabelSearchResult>();
  for (const row of results) {
    lookup.set(`${row.model_label ?? row.model_type}:${row.label_horizon}`, row);
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead>
          <tr>
            <th className="px-2 py-2 text-left text-slate-400">Model \\ Horizon</th>
            {horizons.map((horizon) => (
              <th key={horizon} className="px-2 py-2 text-center text-slate-400">
                {horizon}d
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model}>
              <td className="px-2 py-2 text-slate-300 whitespace-nowrap">{model}</td>
              {horizons.map((horizon) => {
                const row = lookup.get(`${model}:${horizon}`);
                const value = row?.f1_macro ?? null;
                return (
                  <td key={horizon} className="px-1 py-1">
                    <div
                      className="rounded px-2 py-2 text-center text-slate-900 font-medium"
                      style={{ backgroundColor: heatColor(value) }}
                      title={row ? `OOS acc ${formatMetricPercent(row.accuracy)}` : undefined}
                    >
                      {formatMetricPercent(value)}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
