import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { McSimulationOptimizeResponse } from '../api/types';
import OptimizationResultsTable from './OptimizationResultsTable';
import MetricCard from './MetricCard';
import StatusBadge from './StatusBadge';
import ErrorAlert from './ErrorAlert';
import { fmtPct } from '../utils/formatting';

const PERCENTILE_COLORS: Record<string, string> = {
  '5': '#ef4444',
  '25': '#f97316',
  '50': '#22c55e',
  '75': '#3b82f6',
  '95': '#a855f7',
};

function buildChartData(paths: Record<string, number[]>): Record<string, number>[] {
  const len = paths['50']?.length ?? 0;
  return Array.from({ length: len }, (_, i) => {
    const point: Record<string, number> = { step: i };
    for (const [pct, values] of Object.entries(paths)) {
      point[`p${pct}`] = Number(values[i]?.toFixed(4));
    }
    return point;
  });
}

function BestParamsCard({ result }: { result: McSimulationOptimizeResponse }) {
  if (!result.best_params) return null;
  return (
    <div className="card border border-brand-500/30">
      <h3 className="text-brand-400 font-semibold mb-1">Best Parameters</h3>
      <p className="text-slate-500 text-xs mb-3">
        Avg OOS scores are averaged across folds where this combo won the in-sample leg.
      </p>
      <div className="space-y-2">
        {Object.entries(result.best_params).map(([k, v]) => (
          <div key={k} className="flex justify-between">
            <span className="text-slate-400 text-sm font-mono">{k}</span>
            <span className="text-slate-100 text-sm font-mono font-semibold">{String(v)}</span>
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
        {result.best_avg_oos_max_drawdown != null && isFinite(result.best_avg_oos_max_drawdown) && (
          <div className="flex justify-between">
            <span className="text-slate-400 text-sm">Avg OOS max drawdown</span>
            <span className="text-slate-100 text-sm font-semibold">
              {fmtPct(result.best_avg_oos_max_drawdown)}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function BestRunChart({ paths }: { paths: Record<string, number[]> }) {
  const chartData = buildChartData(paths);
  if (chartData.length === 0) return null;
  return (
    <div className="card">
      <h3 className="text-slate-200 font-semibold mb-4">Best-Run Percentile Paths</h3>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          {['5', '25', '50', '75', '95'].map((pct) => (
            <Line
              key={pct}
              type="monotone"
              dataKey={`p${pct}`}
              stroke={PERCENTILE_COLORS[pct]}
              dot={false}
              strokeWidth={pct === '50' ? 2 : 1}
              isAnimationActive={false}
            />
          ))}
          <XAxis dataKey="step" stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
          <YAxis stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
          <Tooltip
            contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
          />
          <Legend />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export default function McSimulationOptimizeResults({ result }: { result: McSimulationOptimizeResponse }) {
  const stats = result.best_run_stats;
  return (
    <>
      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge status={result.status} />
        <span className="text-slate-400 text-sm">
          {result.duration_ms}ms &bull; {result.n_splits} folds &bull; {result.optimize_metric}
        </span>
      </div>
      {result.error_message && <ErrorAlert message={result.error_message} />}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <BestParamsCard result={result} />
        {stats && (
          <div className="card border border-slate-600">
            <h3 className="text-slate-200 font-semibold mb-1">Best-Run Simulation</h3>
            <p className="text-slate-500 text-xs mb-3">
              Full forward simulation at end of date range using best params.
            </p>
            <div className="grid grid-cols-2 gap-3">
              <MetricCard label="Median Terminal" value={stats.p50.toFixed(4)} />
              <MetricCard
                label="Prob. Positive Return"
                value={`${(stats.prob_positive_return * 100).toFixed(1)}%`}
                positive={stats.prob_positive_return > 0.5}
              />
              <MetricCard
                label="Mean Max Drawdown"
                value={`${(stats.mean_max_drawdown * 100).toFixed(1)}%`}
                negative
              />
              <MetricCard label="Std Dev (terminal)" value={stats.std_terminal.toFixed(4)} />
            </div>
          </div>
        )}
      </div>
      {result.best_run_percentile_paths && (
        <BestRunChart paths={result.best_run_percentile_paths} />
      )}
      {result.all_results && result.all_results.length > 0 && (
        <div className="card">
          <h3 className="text-slate-200 font-semibold mb-4">
            All Parameter Combinations (sorted by OOS metric)
          </h3>
          <OptimizationResultsTable
            results={result.all_results}
            metric={result.optimize_metric}
          />
        </div>
      )}
    </>
  );
}
