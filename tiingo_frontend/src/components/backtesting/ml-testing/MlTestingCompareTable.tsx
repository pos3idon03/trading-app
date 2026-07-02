import { useMemo, useState } from 'react';
import type { MlTestingRun } from '../../../utils/mlTestingSession';
import { formatMetricPercent, formatOosAccuracy } from '../../../utils/mlBacktestConfig';
import { formatIndicatorGroupsSummary } from '../../../utils/mlIndicatorGroups';
import { formatSignalCounts } from './MlTestingMlSummary';

function configLabel(run: MlTestingRun): string {
  const cfg = run.config;
  const stratCount = cfg.mlParams.strategy_feature_ids?.length ?? 0;
  const strat = stratCount > 0 ? `${stratCount} strat` : 'no strat';
  const dynamic = formatIndicatorGroupsSummary(
    Boolean(cfg.mlParams.dynamic_indicator_selection),
    cfg.mlParams.indicator_groups,
  );
  const metaBase =
    cfg.mlParams.label_mode === 'meta_label' && cfg.mlParams.base_strategy_id
      ? `base ${cfg.mlParams.base_strategy_id.replace(/_/g, ' ')}`
      : null;
  const parts = [
    cfg.modelType.replace('ml_', ''),
    cfg.mlParams.feature_mode,
    cfg.mlParams.label_mode,
    strat,
    dynamic,
    metaBase,
  ].filter(Boolean);
  return parts.join(' · ');
}

type SortKey = 'sharpe' | 'return' | 'oos' | 'f1' | 'createdAt';

interface MlTestingCompareTableProps {
  runs: MlTestingRun[];
  selectedClientId: string | null;
  onSelect: (clientId: string) => void;
}

function sortValue(run: MlTestingRun, key: SortKey): number {
  if (key === 'createdAt') {
    return new Date(run.createdAt).getTime();
  }
  const metrics = run.metrics;
  const summary = run.mlSummary;
  if (key === 'sharpe') return metrics?.sharpe_ratio ?? -Infinity;
  if (key === 'return') return metrics?.total_return_pct ?? -Infinity;
  if (key === 'oos') return summary?.mean_oos_accuracy ?? -Infinity;
  if (key === 'f1') return summary?.f1 ?? -Infinity;
  return 0;
}

export default function MlTestingCompareTable({
  runs,
  selectedClientId,
  onSelect,
}: MlTestingCompareTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('sharpe');
  const completed = runs.filter((row) => row.status === 'completed');

  const sorted = useMemo(() => {
    return [...completed].sort((a, b) => sortValue(b, sortKey) - sortValue(a, sortKey));
  }, [completed, sortKey]);

  const bestId = sorted[0]?.clientId ?? null;

  if (completed.length === 0) {
    return (
      <p className="text-sm text-slate-500 py-4">
        Run at least one completed backtest to compare metrics.
      </p>
    );
  }

  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-slate-400">Sort by</span>
        {(
          [
            ['sharpe', 'Sharpe'],
            ['return', 'Return'],
            ['oos', 'OOS accuracy'],
            ['f1', 'F1'],
            ['createdAt', 'Newest'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setSortKey(key)}
            className={`text-xs px-2 py-1 rounded border ${
              sortKey === key
                ? 'border-brand-500 text-brand-400'
                : 'border-slate-700 text-slate-400'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="overflow-x-auto border border-slate-800 rounded-lg">
        <table className="min-w-full text-sm">
          <thead className="bg-surface-950 text-slate-400">
            <tr>
              <th className="px-3 py-2 text-left">Config</th>
              <th className="px-3 py-2 text-right">Sharpe</th>
              <th className="px-3 py-2 text-right">Return</th>
              <th className="px-3 py-2 text-right">OOS acc.</th>
              <th className="px-3 py-2 text-right">F1</th>
              <th className="px-3 py-2 text-left">Signals</th>
              <th className="px-3 py-2 text-left">Status</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row) => {
              const isBest = row.clientId === bestId;
              const isSelected = row.clientId === selectedClientId;
              return (
                <tr
                  key={row.clientId}
                  onClick={() => onSelect(row.clientId)}
                  className={`border-t border-slate-800 cursor-pointer ${
                    isSelected ? 'bg-brand-500/10' : 'hover:bg-surface-800/40'
                  }`}
                >
                  <td className="px-3 py-2 text-slate-200 text-xs">
                    {configLabel(row)}
                    {row.starred && ' ★'}
                    {isBest && (
                      <span className="ml-2 text-xs text-emerald-400">best</span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {row.metrics?.sharpe_ratio?.toFixed(2) ?? '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {row.metrics?.total_return_pct != null
                      ? `${row.metrics.total_return_pct.toFixed(2)}%`
                      : '—'}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {formatOosAccuracy(row.mlSummary?.mean_oos_accuracy)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-300">
                    {formatMetricPercent(row.mlSummary?.f1 ?? null)}
                  </td>
                  <td className="px-3 py-2 text-slate-400 text-xs">
                    {formatSignalCounts(row.mlSummary?.signal_counts)}
                  </td>
                  <td className="px-3 py-2 text-slate-400">{row.status}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
