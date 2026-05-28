import type { MlWalkForwardReadiness } from '../../api/mlBacktestTypes';
import { readinessStatusTone } from '../../utils/mlWalkForwardDiagnostics';

interface MlWalkForwardReadinessCardProps {
  readiness: MlWalkForwardReadiness | undefined;
  warnings?: string[];
  compact?: boolean;
}

function StatCell({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-slate-500 text-xs">{label}</dt>
      <dd className="text-slate-100 font-medium">{value}</dd>
    </div>
  );
}

export default function MlWalkForwardReadinessCard({
  readiness,
  warnings = [],
  compact = false,
}: MlWalkForwardReadinessCardProps) {
  if (!readiness || readiness.total_bars === 0) {
    return (
      <p className="text-xs text-slate-500">
        Run data preview to check walk-forward readiness (valid features and trainable folds).
      </p>
    );
  }

  const tone = readinessStatusTone(readiness);
  const borderClass =
    tone === 'ready'
      ? 'border-emerald-900/50 bg-emerald-950/20'
      : tone === 'warning'
        ? 'border-amber-900/50 bg-amber-950/20'
        : 'border-slate-800 bg-surface-950/40';

  const issues = [
    ...(readiness.readiness_issues ?? []),
    ...warnings.filter(
      (warning) => !(readiness.readiness_issues ?? []).includes(warning),
    ),
  ];

  return (
    <section className={`rounded-lg border p-4 space-y-3 ${borderClass}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="text-sm font-medium text-slate-200">Walk-forward readiness</h4>
        <span
          className={`text-xs font-medium ${
            tone === 'ready' ? 'text-emerald-300' : 'text-amber-200'
          }`}
        >
          {tone === 'ready' ? 'Ready for labeling' : 'Not ready for walk-forward'}
        </span>
      </div>

      <dl className={`grid gap-3 ${compact ? 'grid-cols-2 md:grid-cols-3' : 'grid-cols-2 md:grid-cols-5'}`}>
        <StatCell label="Valid feature rows" value={readiness.valid_feature_rows} />
        <StatCell label="Trainable rows" value={readiness.trainable_rows} />
        <StatCell
          label="Viable folds"
          value={`${readiness.viable_folds} / ${readiness.structural_folds}`}
        />
        {!compact && (
          <>
            <StatCell label="Labeled rows" value={readiness.labeled_rows} />
            <StatCell label="Total bars" value={readiness.total_bars} />
          </>
        )}
      </dl>

      <p className="text-xs text-slate-400">
        Label counts use raw prices. Walk-forward training requires bars with both valid features
        and labels. Structural folds ({readiness.structural_folds}) count window geometry; viable
        folds ({readiness.viable_folds}) can actually train.
      </p>

      {issues.length > 0 && (
        <ul className="space-y-1 text-xs text-amber-200/90 list-disc list-inside">
          {issues.map((issue) => (
            <li key={issue}>{issue}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
