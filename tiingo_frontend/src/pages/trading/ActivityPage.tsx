import { useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import ProbabilityExplainabilityPanel from '../../components/trading/ProbabilityExplainabilityPanel';
import { useExecutionActivityStream } from '../../hooks/useExecutionActivityStream';
import { PROBABILITY_UP_LABEL } from '../../utils/probabilityExplainability';
import {
  formatDateTime,
  formatOutcome,
  formatProbability,
  formatSignal,
  outcomeClass,
} from '../../utils/tradingDeployments';

export default function ActivityPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const deploymentId = searchParams.get('deploymentId');
  const symbolFilter = searchParams.get('symbol') ?? '';

  const { events, connectionState } = useExecutionActivityStream({
    deploymentId,
    symbol: symbolFilter || null,
  });
  const [expandedExplainability, setExpandedExplainability] = useState<Record<string, boolean>>({});

  const filteredEvents = useMemo(() => {
    if (!symbolFilter) return events;
    return events.filter((event) => event.symbol === symbolFilter.toUpperCase());
  }, [events, symbolFilter]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Activity</h1>
          <p className="text-slate-400 text-sm mt-1">
            Live decision stream for active deployments — signal, probability, position, and order outcome.
          </p>
        </div>
        <div className="text-xs text-slate-400">
          WebSocket:{' '}
          <span
            className={
              connectionState === 'connected' ? 'text-emerald-400' : 'text-amber-400'
            }
          >
            {connectionState}
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Filter symbol e.g. AAPL"
          defaultValue={symbolFilter}
          onKeyDown={(event) => {
            if (event.key !== 'Enter') return;
            const value = (event.target as HTMLInputElement).value.trim();
            const params = new URLSearchParams(searchParams);
            if (value) params.set('symbol', value.toUpperCase());
            else params.delete('symbol');
            navigate(`/trading/activity?${params.toString()}`);
          }}
          className="rounded-lg border border-slate-700 bg-surface-800 px-3 py-2 text-sm text-slate-100"
        />
        {deploymentId && (
          <button
            type="button"
            onClick={() => navigate('/trading/activity')}
            className="px-3 py-2 rounded-lg border border-slate-700 text-slate-300 text-sm"
          >
            Clear deployment filter
          </button>
        )}
      </div>

      <div className="space-y-3">
        {filteredEvents.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-surface-900 p-6 text-sm text-slate-400">
            No evaluation activity yet. Activate a deployment and run Evaluate now, or wait for the
            scheduled evaluation cycle (intraday models refresh every 5 minutes during market hours).
          </div>
        ) : (
          filteredEvents.map((event) => (
            <article
              key={event.id}
              className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-2"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="font-semibold text-slate-100">{event.symbol}</span>
                  <span className="text-slate-500">·</span>
                  <span className="text-slate-300">{event.model_name ?? 'Unknown model'}</span>
                </div>
                <span className={`text-xs font-medium uppercase ${outcomeClass(event.outcome)}`}>
                  {formatOutcome(event.outcome)}
                </span>
              </div>
              <dl className="grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <dt className="text-slate-500">Signal</dt>
                  <dd className="text-slate-100">{formatSignal(event.signal)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">{PROBABILITY_UP_LABEL}</dt>
                  <dd className="text-slate-100">{formatProbability(event.probability)}</dd>
                  {event.explainability && (
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedExplainability((current) => ({
                          ...current,
                          [event.id]: !current[event.id],
                        }))
                      }
                      className="mt-1 text-xs text-brand-300 hover:text-brand-200"
                    >
                      {expandedExplainability[event.id] ? 'Hide drivers' : 'Why?'}
                    </button>
                  )}
                </div>
                <div>
                  <dt className="text-slate-500">Thresholds</dt>
                  <dd className="text-slate-100">
                    buy {event.buy_threshold ?? '—'} / sell {event.sell_threshold ?? '—'}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Position</dt>
                  <dd className="text-slate-100">{event.position_side ?? '—'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Bar time</dt>
                  <dd className="text-slate-100">{formatDateTime(event.bar_time)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Order intent</dt>
                  <dd className="text-slate-100">
                    {event.order_intent_side
                      ? `${event.order_intent_side.toUpperCase()} ${event.order_qty?.toFixed(4) ?? ''}`
                      : '—'}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-slate-500">Block reason</dt>
                  <dd className="text-slate-100">{event.blocked_reason ?? '—'}</dd>
                </div>
              </dl>
              {expandedExplainability[event.id] && (
                <div className="rounded-lg border border-slate-800 bg-surface-950/60 px-3 py-2">
                  <ProbabilityExplainabilityPanel explainability={event.explainability} compact />
                </div>
              )}
              {event.warnings.length > 0 && (
                <p className="text-xs text-amber-400/90">
                  Warnings: {event.warnings.join('; ')}
                </p>
              )}
            </article>
          ))
        )}
      </div>
    </div>
  );
}
