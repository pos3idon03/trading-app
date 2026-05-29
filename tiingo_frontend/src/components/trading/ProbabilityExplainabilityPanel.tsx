import type { ProbabilityExplainability } from '../../api/executionTypes';
import {
  formatContribution,
  formatFeatureValue,
  hasExplainability,
  maxContributionMagnitude,
} from '../../utils/probabilityExplainability';

interface ProbabilityExplainabilityPanelProps {
  explainability: ProbabilityExplainability | null | undefined;
  compact?: boolean;
}

export default function ProbabilityExplainabilityPanel({
  explainability,
  compact = false,
}: ProbabilityExplainabilityPanelProps) {
  if (!explainability) {
    return null;
  }

  if (!hasExplainability(explainability)) {
    const warning = explainability.warnings?.[0] ?? 'Explainability unavailable for this model.';
    return (
      <p className={`text-slate-500 ${compact ? 'text-xs' : 'text-sm'}`}>{warning}</p>
    );
  }

  const scale = maxContributionMagnitude(explainability.top_contributors);

  return (
    <div className={`space-y-3 ${compact ? 'text-xs' : 'text-sm'}`}>
      <div className="space-y-2">
        {explainability.top_contributors.map((row) => {
          const positive = row.contribution >= 0;
          const widthPct =
            scale > 0 ? Math.max(4, (Math.abs(row.contribution) / scale) * 100) : 0;
          return (
            <div key={row.feature} className="space-y-1">
              <div className="flex items-center justify-between gap-2 text-slate-300">
                <span className="font-mono text-[11px]">{row.feature}</span>
                <span className="text-slate-500">
                  {formatFeatureValue(row.feature, row.value)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 flex-1 rounded bg-slate-800">
                  <div
                    className={`h-2 rounded ${positive ? 'bg-emerald-500/80' : 'bg-red-500/80'}`}
                    style={{ width: `${widthPct}%` }}
                  />
                </div>
                <span
                  className={`w-16 text-right font-medium ${
                    positive ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {formatContribution(row.contribution)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] leading-relaxed text-slate-500">
        Contributions show what pushed Probability (up) on this bar; signal still depends on
        buy/sell thresholds.
      </p>
    </div>
  );
}
