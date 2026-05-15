import { useState } from 'react';
import type { BacktestResponse } from '../api/types';
import { STRATEGIES, DEFAULT_PARAMS_MAP } from '../constants/strategies';
import { fmt, fmtPct } from '../utils/formatting';
import MetricCard from './MetricCard';
import MetricQualityBar from './MetricQualityBar';
import StatusBadge from './StatusBadge';
import ErrorAlert from './ErrorAlert';
import BacktestEquityCurve from './BacktestEquityCurve';
import IndicatorChart from './IndicatorChart';

interface BacktestResultCardProps {
  result: BacktestResponse;
  onAddToStrategy?: (strategyName: string, params: Record<string, unknown>, assetId: number) => Promise<void>;
  syncId?: string;
}

function StrategyLabel({ strategyName }: { strategyName: string }) {
  const label = STRATEGIES.find((s) => s.value === strategyName)?.label ?? strategyName;
  return <span className="text-slate-100 font-semibold text-sm">{label}</span>;
}

function MetricsGrid({ metrics }: { metrics: NonNullable<BacktestResponse['metrics']> }) {
  const m = metrics;
  return (
    <div className="grid grid-cols-2 gap-2">
      <MetricCard label="Total Return"  value={fmtPct(m.total_return)}    positive={(m.total_return ?? 0) > 0}  negative={(m.total_return ?? 0) < 0} />
      <MetricQualityBar label="Sharpe Ratio" value={m.sharpe_ratio} formattedValue={fmt(m.sharpe_ratio, 3)} kind="sharpe" />
      <MetricCard label="Max Drawdown"  value={fmtPct(m.max_drawdown)}    negative />
      <MetricCard label="Win Rate"      value={fmtPct(m.win_rate)}        positive={(m.win_rate ?? 0) > 0.5} />
      <MetricQualityBar label="Profit Factor" value={m.profit_factor} formattedValue={fmt(m.profit_factor, 2)} kind="profit_factor" />
      <MetricCard label="# Trades"      value={m.num_trades ?? '—'} />
    </div>
  );
}

function AddToStrategyButton({
  strategyName,
  params,
  assetId,
  onAdd,
}: {
  strategyName: string;
  params: Record<string, unknown>;
  assetId: number;
  onAdd: (strategyName: string, params: Record<string, unknown>, assetId: number) => Promise<void>;
}) {
  const [state, setState] = useState<'idle' | 'loading' | 'done' | 'error'>('idle');

  const handleClick = async () => {
    setState('loading');
    try {
      await onAdd(strategyName, params, assetId);
      setState('done');
    } catch {
      setState('error');
      setTimeout(() => setState('idle'), 2000);
    }
  };

  const label = state === 'loading' ? '…'
    : state === 'done' ? 'Added ✓'
    : state === 'error' ? 'Failed'
    : '+ Strategy';

  const cls = state === 'done'
    ? 'text-green-400 border-green-700'
    : state === 'error'
    ? 'text-red-400 border-red-700'
    : 'text-slate-400 border-slate-600 hover:text-brand-400 hover:border-brand-600';

  return (
    <button
      onClick={handleClick}
      disabled={state === 'loading' || state === 'done'}
      className={`text-xs border rounded px-2 py-0.5 transition-colors ${cls}`}
    >
      {label}
    </button>
  );
}

export default function BacktestResultCard({ result, onAddToStrategy, syncId }: BacktestResultCardProps) {
  const gradientId = `equityGrad-${result.strategy_name}`;
  const hasEquity = (result.equity_curve ?? []).length > 0;
  const hasIndicators = (result.indicator_series ?? []).length > 0;
  const isDone = result.status === 'done';
  const defaultParams = DEFAULT_PARAMS_MAP[result.strategy_name] ?? {};

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <StatusBadge status={result.status} />
        <StrategyLabel strategyName={result.strategy_name} />
        <span className="text-slate-500 text-xs ml-auto flex items-center gap-2">
          {isDone && onAddToStrategy && (
            <AddToStrategyButton
              strategyName={result.strategy_name}
              params={result.strategy_params ?? {}}
              assetId={result.asset_id}
              onAdd={onAddToStrategy}
            />
          )}
          {result.duration_ms != null && `${result.duration_ms}ms`}
        </span>
      </div>

      {result.error_message && <ErrorAlert message={result.error_message} />}

      {result.metrics && <MetricsGrid metrics={result.metrics} />}

      {hasEquity && (
        <BacktestEquityCurve
          data={result.equity_curve!}
          gradientId={gradientId}
          tradeLog={result.trade_log}
          buyHoldData={result.buy_hold_curve}
          compact
          syncId={syncId}
        />
      )}

      {hasIndicators && (
        <div className="pt-1 border-t border-slate-700/50">
          <IndicatorChart
            data={result.indicator_series!}
            strategyName={result.strategy_name}
            strategyParams={defaultParams}
            syncId={syncId}
          />
        </div>
      )}
    </div>
  );
}
