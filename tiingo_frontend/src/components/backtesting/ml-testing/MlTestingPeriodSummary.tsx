import type { WalkForwardBudget } from '../../../utils/mlUniverseBudget';
import { resolveWarmupBars, type WalkForwardParams } from '../../../utils/mlBacktestConfig';

interface MlTestingPeriodSummaryProps {
  params: WalkForwardParams;
  budget: WalkForwardBudget | null;
}

export default function MlTestingPeriodSummary({
  params,
  budget,
}: MlTestingPeriodSummaryProps) {
  const warmup = resolveWarmupBars(params);
  const simulationStart = budget?.simulationStartBarIndex ?? params.train_bars;

  return (
    <div className="rounded-lg border border-slate-800 bg-surface-950/50 px-4 py-3 text-sm text-slate-400 space-y-1">
      <p>
        <span className="text-slate-300">Warmup</span> {warmup} bars (feature lookback) →{' '}
        <span className="text-slate-300">Train</span> {params.train_bars} →{' '}
        <span className="text-slate-300">Test</span> {params.test_bars} per fold →{' '}
        <span className="text-slate-300">Step</span> {params.step_bars} (simulation advance)
      </p>
      {budget != null && (
        <p>
          Minimum bars: {budget.minimumRequired} · Structural folds: {budget.structuralFolds} ·
          Simulation trading starts near bar {simulationStart}
          {budget.remainingBars >= 0
            ? ` · Headroom: ${budget.remainingBars} bars`
            : ` · Shortfall: ${-budget.remainingBars} bars`}
        </p>
      )}
    </div>
  );
}
