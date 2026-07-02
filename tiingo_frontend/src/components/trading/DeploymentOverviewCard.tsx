import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { DeploymentOverview } from '../../api/executionTypes';
import { PROBABILITY_UP_LABEL } from '../../utils/probabilityExplainability';
import {
  deploymentStatusClass,
  formatDeploymentStatus,
} from '../../utils/tradingDeployments';
import {
  overviewMetricRows,
  profitMetricClass,
} from '../../utils/tradingOverview';
import ProbabilityExplainabilityPanel from './ProbabilityExplainabilityPanel';

interface DeploymentOverviewCardProps {
  deployment: DeploymentOverview;
  busy?: boolean;
  onRefresh?: (deployment: DeploymentOverview) => void;
  onEvaluate?: (deployment: DeploymentOverview) => void;
}

export default function DeploymentOverviewCard({
  deployment,
  busy = false,
  onRefresh,
  onEvaluate,
}: DeploymentOverviewCardProps) {
  const navigate = useNavigate();
  const [showExplainability, setShowExplainability] = useState(false);
  const metrics = overviewMetricRows(deployment);
  const isStale = deployment.update_status === 'stale';

  return (
    <div className="flex w-full flex-col rounded-xl border border-slate-800 bg-surface-900 p-4 text-left transition-colors hover:border-slate-700">
      <button
        type="button"
        onClick={() => navigate(`/trading/activity?deploymentId=${deployment.id}`)}
        className="flex w-full flex-col text-left transition-colors hover:bg-surface-800/40 rounded-lg -m-1 p-1"
      >
        <div className="mb-4 flex min-h-[4.75rem] items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-lg font-bold text-slate-100">{deployment.symbol}</p>
            <p className="mt-0.5 line-clamp-2 text-xs text-slate-500">
              {deployment.model_name ?? '—'}
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            <span className="text-xs rounded-full border border-slate-700 px-2 py-0.5 text-slate-300">
              {deployment.timeframe}
            </span>
            {isStale && (
              <span
                className="text-xs rounded-full border border-amber-700/60 bg-amber-950/40 px-2 py-0.5 text-amber-400"
                title={
                  deployment.missed_slot_count > 0
                    ? `${deployment.missed_slot_count} missed evaluation slot(s)`
                    : 'OHLCV or evaluation is behind schedule'
                }
              >
                Stale
              </span>
            )}
            <span className={`text-xs font-medium ${deploymentStatusClass(deployment.status)}`}>
              {formatDeploymentStatus(deployment.status)}
            </span>
            {deployment.status === 'error' &&
              (deployment.last_error ?? deployment.last_blocked_reason) && (
              <span
                className="max-w-[12rem] text-right text-xs text-red-400/90 line-clamp-2"
                title={deployment.last_error ?? deployment.last_blocked_reason ?? undefined}
              >
                {deployment.last_error ?? deployment.last_blocked_reason}
              </span>
            )}
          </div>
        </div>

        <dl className="space-y-2">
          {metrics.map((metric) => {
            const isProfit = metric.label === 'Strategy profit';
            const isProfitPct = metric.label === 'Strategy profit %';
            const isProbability = metric.label === PROBABILITY_UP_LABEL;
            const toneClass =
              isProfit || isProfitPct
                ? profitMetricClass(
                    isProfit ? deployment.strategy_profit : deployment.strategy_profit_pct,
                  )
                : '';

            return (
              <div key={metric.label} className="space-y-2">
                <div
                  className={`flex min-h-[2rem] items-center justify-between gap-3 rounded-lg px-2 py-1.5 ${
                    toneClass ? `border ${toneClass}` : ''
                  }`}
                >
                  <dt className="text-xs text-slate-500">{metric.label}</dt>
                  <dd className="text-right">
                    <span className="block text-sm font-medium text-slate-100">{metric.value}</span>
                    {metric.sublabel && (
                      <span className="block text-xs text-slate-500">{metric.sublabel}</span>
                    )}
                    {isProbability && metric.expandable && (
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          setShowExplainability((open) => !open);
                        }}
                        className="mt-1 text-xs text-brand-300 hover:text-brand-200"
                      >
                        {showExplainability ? 'Hide drivers' : 'Why?'}
                      </button>
                    )}
                  </dd>
                </div>
                {isProbability && showExplainability && (
                  <div
                    className="rounded-lg border border-slate-800 bg-surface-950/60 px-3 py-2"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <ProbabilityExplainabilityPanel
                      explainability={deployment.last_explainability}
                      compact
                    />
                  </div>
                )}
              </div>
            );
          })}
        </dl>

        <div className="mt-3 min-h-[1.25rem]">
          {deployment.open_order_count > 0 && (
            <p className="text-xs text-amber-400">
              {deployment.open_order_count} open order
              {deployment.open_order_count === 1 ? '' : 's'}
            </p>
          )}
        </div>
      </button>

      <div className="mt-3 flex gap-2 border-t border-slate-800 pt-3">
        <button
          type="button"
          disabled={busy}
          onClick={() => onRefresh?.(deployment)}
          className="flex-1 rounded-lg border border-slate-700 px-2 py-1.5 text-xs text-slate-300 hover:bg-surface-800 disabled:opacity-50"
        >
          Refresh
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => onEvaluate?.(deployment)}
          className="flex-1 rounded-lg border border-brand-700/60 bg-brand-950/30 px-2 py-1.5 text-xs text-brand-300 hover:bg-brand-950/50 disabled:opacity-50"
        >
          Evaluate
        </button>
      </div>
    </div>
  );
}
