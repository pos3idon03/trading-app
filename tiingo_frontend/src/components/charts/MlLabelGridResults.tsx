import type { MlLabelSearchResult, MlWalkForwardReadiness } from '../../api/mlBacktestTypes';
import { formatMetricPercent, formatOosAccuracy } from '../../utils/mlBacktestConfig';
import { formatZeroOosGuidance } from '../../utils/mlWalkForwardDiagnostics';

interface MlLabelGridResultsProps {
  results: MlLabelSearchResult[];
  onApply?: (result: MlLabelSearchResult) => void;
  readiness?: MlWalkForwardReadiness;
}

export default function MlLabelGridResults({
  results,
  onApply,
  readiness,
}: MlLabelGridResultsProps) {
  if (!results.length) {
    return (
      <p className="text-sm text-slate-500">
        Run label grid search to compare all models and horizons.
      </p>
    );
  }

  const zeroOosWindows = results.every((row) => (row.oos_window_count ?? 0) === 0);
  const sampleDistribution = results[0]?.class_distribution;
  const guidance = zeroOosWindows
    ? formatZeroOosGuidance(readiness, sampleDistribution)
    : [];

  return (
    <div className="space-y-2">
      {zeroOosWindows && (
        <ul className="space-y-1 text-xs text-amber-200/80 list-disc list-inside">
          {guidance.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
      <div className="overflow-x-auto border border-slate-800 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-900 text-slate-400">
            <tr>
              <th className="px-3 py-2 text-left">Model</th>
              <th className="px-3 py-2 text-left">Label mode</th>
              <th className="px-3 py-2 text-left">Label</th>
              <th className="px-3 py-2 text-right">Horizon</th>
              <th className="px-3 py-2 text-right">Threshold</th>
              <th className="px-3 py-2 text-right">F1 macro</th>
              <th className="px-3 py-2 text-right">OOS acc</th>
              <th className="px-3 py-2 text-right">OOS windows</th>
              <th className="px-3 py-2 text-left">Distribution</th>
              {onApply && <th className="px-3 py-2" />}
            </tr>
          </thead>
          <tbody>
            {results.map((row) => (
              <tr key={row.label_key} className="border-t border-slate-800">
                <td className="px-3 py-2 text-slate-200">
                  {row.model_label ?? row.model_type ?? '—'}
                </td>
                <td className="px-3 py-2 text-slate-400">{row.label_mode}</td>
                <td className="px-3 py-2 text-slate-300">{row.label_key}</td>
                <td className="px-3 py-2 text-right text-slate-300">{row.label_horizon}</td>
                <td className="px-3 py-2 text-right text-slate-300">
                  {row.label_threshold != null
                    ? formatMetricPercent(row.label_threshold)
                    : row.label_mode === 'binary'
                      ? 'N/A'
                      : '—'}
                </td>
                <td className="px-3 py-2 text-right text-emerald-300">
                  {formatMetricPercent(row.f1_macro)}
                </td>
                <td className="px-3 py-2 text-right text-slate-300">
                  {formatOosAccuracy(row.accuracy)}
                </td>
                <td className="px-3 py-2 text-right text-slate-400">
                  {row.oos_window_count ?? 0}
                </td>
                <td className="px-3 py-2 text-xs text-slate-400">
                  {Object.entries(row.class_distribution)
                    .map(([key, count]) => `${key}:${count}`)
                    .join(' · ')}
                </td>
                {onApply && (
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => onApply(row)}
                      className="text-xs text-brand-400 hover:text-brand-300"
                    >
                      Apply
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
