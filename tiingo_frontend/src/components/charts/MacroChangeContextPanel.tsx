import type { PeriodChangeContext } from '../../utils/macroStandaloneData';

interface MacroChangeContextPanelProps {
  context: PeriodChangeContext | null;
  macroId: string;
  assetId: string;
  stepLabel: string;
}

function PercentileGauge({
  title,
  value,
  percentile,
  history,
}: {
  title: string;
  value: number;
  percentile: number;
  history: number[];
}) {
  const min = history.length ? Math.min(...history) : value;
  const max = history.length ? Math.max(...history) : value;
  const span = max - min || 1;
  const marker = ((value - min) / span) * 100;

  return (
    <div className="rounded-lg border border-slate-800 bg-surface-800/50 p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-sm font-medium text-slate-200">{title}</h4>
        <span className="text-xs text-slate-500">{percentile}th percentile</span>
      </div>
      <p className="text-lg font-mono text-slate-100">
        {value >= 0 ? '+' : ''}
        {value.toFixed(2)}%
      </p>
      <div className="relative h-3 rounded-full bg-slate-700 overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-brand-500/30"
          style={{ width: `${Math.min(100, Math.max(0, marker))}%` }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-brand-500 border border-white"
          style={{ left: `calc(${Math.min(100, Math.max(0, marker))}% - 5px)` }}
        />
      </div>
      <p className="text-xs text-slate-500">
        Range {min.toFixed(2)}% → {max.toFixed(2)}% across full history
      </p>
    </div>
  );
}

export default function MacroChangeContextPanel({
  context,
  macroId,
  assetId,
  stepLabel,
}: MacroChangeContextPanelProps) {
  if (!context) {
    return (
      <section className="w-full border border-slate-800 rounded-lg bg-surface-900 p-4">
        <h3 className="text-sm font-semibold text-slate-200 mb-2">Historical context</h3>
        <p className="text-xs text-slate-500">
          Select a macro series and asset with enough overlapping history to see percentile context.
        </p>
      </section>
    );
  }

  return (
    <section className="w-full border border-slate-800 rounded-lg bg-surface-900 p-4 space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-200">Historical context</h3>
        <p className="text-xs text-slate-500 mt-1">
          How extreme each {stepLabel} change is versus the full aligned history at this macro
          frequency.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <PercentileGauge
          title={`${macroId} change`}
          value={context.point.macroChange}
          percentile={context.macroPercentile}
          history={context.macroHistory}
        />
        <PercentileGauge
          title={`${assetId} change`}
          value={context.point.assetChange}
          percentile={context.assetPercentile}
          history={context.assetHistory}
        />
      </div>
    </section>
  );
}
