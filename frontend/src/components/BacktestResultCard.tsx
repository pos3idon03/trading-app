import type { BacktestResponse } from '../api/types';
import { STRATEGIES } from '../constants/strategies';
import { fmt, fmtPct } from '../utils/formatting';
import MetricCard from './MetricCard';
import StatusBadge from './StatusBadge';
import ErrorAlert from './ErrorAlert';
import BacktestEquityCurve from './BacktestEquityCurve';

interface BacktestResultCardProps {
  result: BacktestResponse;
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
      <MetricCard label="Sharpe Ratio"  value={fmt(m.sharpe_ratio, 3)}    positive={(m.sharpe_ratio ?? 0) > 1}  negative={(m.sharpe_ratio ?? 0) < 0} />
      <MetricCard label="Max Drawdown"  value={fmtPct(m.max_drawdown)}    negative />
      <MetricCard label="Win Rate"      value={fmtPct(m.win_rate)}        positive={(m.win_rate ?? 0) > 0.5} />
      <MetricCard label="Profit Factor" value={fmt(m.profit_factor, 2)}   positive={(m.profit_factor ?? 0) > 1} />
      <MetricCard label="# Trades"      value={m.num_trades ?? '—'} />
    </div>
  );
}

export default function BacktestResultCard({ result }: BacktestResultCardProps) {
  const gradientId = `equityGrad-${result.backtest_id}`;
  const hasEquity = (result.equity_curve ?? []).length > 0;

  return (
    <div className="card space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <StatusBadge status={result.status} />
        <StrategyLabel strategyName={result.strategy_name} />
        <span className="text-slate-500 text-xs ml-auto">
          #{result.backtest_id} &bull; {result.duration_ms}ms
        </span>
      </div>

      {result.error_message && <ErrorAlert message={result.error_message} />}

      {result.metrics && <MetricsGrid metrics={result.metrics} />}

      {hasEquity && (
        <BacktestEquityCurve
          data={result.equity_curve!}
          gradientId={gradientId}
          compact
        />
      )}
    </div>
  );
}
