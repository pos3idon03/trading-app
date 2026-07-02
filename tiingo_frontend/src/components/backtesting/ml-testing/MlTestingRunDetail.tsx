import type { MlBacktestResultsResponse } from '../../../api/mlBacktestTypes';
import BacktestMetricsCards from '../../BacktestMetricsCards';
import BacktestEquityChart from '../../charts/BacktestEquityChart';
import MlEvaluationScopeBanner from '../MlEvaluationScopeBanner';
import MlTestingMlSummary from './MlTestingMlSummary';

interface MlTestingRunDetailProps {
  results: MlBacktestResultsResponse | null;
  loading?: boolean;
}

export default function MlTestingRunDetail({ results, loading }: MlTestingRunDetailProps) {
  if (loading) {
    return <p className="text-sm text-slate-500 py-6">Loading run details…</p>;
  }

  if (!results) {
    return (
      <p className="text-sm text-slate-500 py-6">
        Select a completed run to view metrics and equity curve.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <MlEvaluationScopeBanner summary={results.ml_summary} />
      <MlTestingMlSummary summary={results.ml_summary} />
      <BacktestMetricsCards metrics={results.metrics} />
      {results.equity_curve.length > 0 && (
        <BacktestEquityChart
          strategy={results.equity_curve}
          benchmark={results.benchmark_equity_curve ?? []}
          initialCash={results.metrics?.initial_cash ?? undefined}
        />
      )}
    </div>
  );
}
