import type { MlTestingRun } from '../../../utils/mlTestingSession';
import { formatSignalCounts } from './MlTestingMlSummary';

interface MlTestingRunsTableProps {
  runs: MlTestingRun[];
  selectedClientId: string | null;
  onSelect: (clientId: string) => void;
  onLoadConfig: (clientId: string) => void;
  onDelete: (clientId: string) => void;
  onToggleStar: (clientId: string) => void;
}

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function MlTestingRunsTable({
  runs,
  selectedClientId,
  onSelect,
  onLoadConfig,
  onDelete,
  onToggleStar,
}: MlTestingRunsTableProps) {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-slate-500 py-4">
        No trial runs yet. Adjust parameters and click Run backtest.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto border border-slate-800 rounded-lg">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-950 text-slate-400">
          <tr>
            <th className="px-3 py-2 text-left">When</th>
            <th className="px-3 py-2 text-left">Model</th>
            <th className="px-3 py-2 text-left">Features</th>
            <th className="px-3 py-2 text-right">Return</th>
            <th className="px-3 py-2 text-left">Signals</th>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((row) => (
            <tr
              key={row.clientId}
              className={`border-t border-slate-800 ${
                selectedClientId === row.clientId ? 'bg-brand-500/10' : ''
              }`}
            >
              <td className="px-3 py-2 text-slate-300">{formatWhen(row.createdAt)}</td>
              <td className="px-3 py-2 text-slate-200">
                {row.starred ? '★ ' : ''}
                {row.config.modelType.replace('ml_', '')}
              </td>
              <td className="px-3 py-2 text-slate-400">{row.config.mlParams.feature_mode}</td>
              <td className="px-3 py-2 text-right text-slate-300">
                {row.metrics?.total_return_pct != null
                  ? `${row.metrics.total_return_pct.toFixed(2)}%`
                  : '—'}
              </td>
              <td className="px-3 py-2 text-slate-400 text-xs">
                {row.status === 'completed'
                  ? formatSignalCounts(row.mlSummary?.signal_counts)
                  : '—'}
              </td>
              <td className="px-3 py-2 text-slate-400">
                {row.status === 'failed' ? row.error ?? 'failed' : row.status}
              </td>
              <td className="px-3 py-2 text-right space-x-2">
                <button
                  type="button"
                  onClick={() => onSelect(row.clientId)}
                  className="text-xs text-brand-400 hover:text-brand-300"
                >
                  View
                </button>
                <button
                  type="button"
                  onClick={() => onLoadConfig(row.clientId)}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  Load config
                </button>
                <button
                  type="button"
                  onClick={() => onToggleStar(row.clientId)}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  {row.starred ? 'Unstar' : 'Star'}
                </button>
                <button
                  type="button"
                  onClick={() => onDelete(row.clientId)}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
