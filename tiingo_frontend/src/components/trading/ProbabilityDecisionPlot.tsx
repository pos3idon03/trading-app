import type { ProbabilityExplainability } from '../../api/executionTypes';
import {
  buildDecisionPlotSteps,
  formatContribution,
  hasExplainability,
} from '../../utils/probabilityExplainability';

interface ProbabilityDecisionPlotProps {
  explainability: ProbabilityExplainability;
  compact?: boolean;
}

export default function ProbabilityDecisionPlot({
  explainability,
  compact = false,
}: ProbabilityDecisionPlotProps) {
  if (!hasExplainability(explainability)) {
    return null;
  }

  const steps = buildDecisionPlotSteps(explainability);
  if (steps.length < 2) {
    return null;
  }

  const values = steps.map((step) => step.cumulative);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const span = maxValue - minValue || 1;

  return (
    <div className={`space-y-2 ${compact ? 'text-xs' : 'text-sm'}`}>
      <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
        Decision path
      </p>
      <div className="space-y-1.5">
        {steps.map((step, index) => {
          const widthPct = Math.max(4, ((step.cumulative - minValue) / span) * 100);
          const isBase = step.feature === 'base';
          const label = isBase ? 'Base' : step.feature;
          return (
            <div key={`${step.feature}-${index}`} className="space-y-0.5">
              <div className="flex items-center justify-between gap-2 text-slate-400">
                <span className="font-mono text-[11px]">{label}</span>
                <span className="text-slate-500">{formatContribution(step.cumulative)}</span>
              </div>
              <div className="h-1.5 rounded bg-slate-800">
                <div
                  className={`h-1.5 rounded ${isBase ? 'bg-slate-500' : 'bg-sky-500/80'}`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      {explainability.predicted_value != null && (
        <p className="text-[11px] text-slate-500">
          Model margin (up class): {formatContribution(explainability.predicted_value)}
        </p>
      )}
    </div>
  );
}
