import type { McBacktestOptimizeResponse } from '../api/types';
import OptimizationResultsTable from './OptimizationResultsTable';
import MetricCard from './MetricCard';
import StatusBadge from './StatusBadge';
import ErrorAlert from './ErrorAlert';
import { fmt, fmtPct } from '../utils/formatting';
import { formatThresholdParam } from '../utils/mcBacktestPreset';

const TOP_N_COMBOS = 10;

function BestParamsCard({
  result,
  onApply,
}: {
  result: McBacktestOptimizeResponse;
  onApply?: () => void;
}) {
  if (!result.best_params) return null;
  return (
    <div className="card border border-brand-500/30">
      <h3 className="text-brand-400 font-semibold mb-1">Best Backtest Parameters</h3>
      <p className="text-slate-500 text-xs mb-3">
        Optimized for walk-forward out-of-sample {result.optimize_metric}. Apply these to the
        Backtest tab to run a full-period validation.
      </p>
      <div className="space-y-2">
        {Object.entries(result.best_params).map(([k, v]) => (
          <div key={k} className="flex justify-between">
            <span className="text-slate-400 text-sm font-mono">{k}</span>
            <span className="text-slate-100 text-sm font-mono font-semibold">
              {formatThresholdParam(k, v)}
            </span>
          </div>
        ))}
        <div className="pt-2 border-t border-slate-700 flex justify-between">
          <span className="text-slate-400 text-sm">Avg OOS {result.optimize_metric}</span>
          <span className="text-brand-400 text-sm font-semibold">
            {result.best_metric !== undefined && isFinite(result.best_metric)
              ? result.best_metric.toFixed(4)
              : '—'}
          </span>
        </div>
        {result.best_avg_oos_max_drawdown != null &&
          isFinite(result.best_avg_oos_max_drawdown) && (
          <div className="flex justify-between">
            <span className="text-slate-400 text-sm">Avg OOS max drawdown</span>
            <span className="text-slate-100 text-sm font-semibold">
              {fmtPct(result.best_avg_oos_max_drawdown)}
            </span>
          </div>
        )}
      </div>
      {onApply && (
        <button type="button" onClick={onApply} className="btn-primary mt-4 w-full sm:w-auto">
          Apply to Backtest Tab
        </button>
      )}
    </div>
  );
}

function MetricsPanel({
  title,
  subtitle,
  metrics,
}: {
  title: string;
  subtitle: string;
  metrics: McBacktestOptimizeResponse['full_period_metrics'];
}) {
  if (!metrics) return null;
  return (
    <div className="card border border-slate-600">
      <h3 className="text-slate-200 font-semibold mb-1">{title}</h3>
      <p className="text-slate-500 text-xs mb-3">{subtitle}</p>
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          label="Total Return"
          value={fmtPct(metrics.total_return)}
          positive={(metrics.total_return ?? 0) > 0}
          negative={(metrics.total_return ?? 0) < 0}
        />
        <MetricCard label="Sharpe" value={fmt(metrics.sharpe_ratio, 3)} />
        <MetricCard label="Max Drawdown" value={fmtPct(metrics.max_drawdown)} negative />
        <MetricCard label="# Trades" value={metrics.num_trades ?? '—'} />
      </div>
    </div>
  );
}

export default function McBacktestOptimizeResults({
  result,
  onApply,
}: {
  result: McBacktestOptimizeResponse;
  onApply?: () => void;
}) {
  const topResults = (result.all_results ?? []).slice(0, TOP_N_COMBOS);

  return (
    <>
      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={result.status} />
        <span className="text-slate-400 text-sm">
          {result.duration_ms}ms &bull; {result.n_splits} folds &bull; {result.optimize_metric}
        </span>
      </div>
      {result.error_message && <ErrorAlert message={result.error_message} />}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <BestParamsCard result={result} onApply={onApply} />
        <MetricsPanel
          title="Full Period (best params)"
          subtitle="Same date range as optimization, using the best parameter combo."
          metrics={result.full_period_metrics}
        />
        <MetricsPanel
          title="Hold-out Period (last 20%)"
          subtitle="Final 20% of eval bars — not used to pick the best combo."
          metrics={result.holdout_metrics}
        />
      </div>
      {topResults.length > 0 && (
        <div className="card">
          <h3 className="text-slate-200 font-semibold mb-4">
            Top {TOP_N_COMBOS} Parameter Combinations (by OOS {result.optimize_metric})
          </h3>
          <OptimizationResultsTable
            results={topResults}
            metric={result.optimize_metric}
          />
        </div>
      )}
    </>
  );
}
