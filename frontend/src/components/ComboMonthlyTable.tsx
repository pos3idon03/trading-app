import React from 'react';
import { ComboMonthlyRow } from '../api/types';

interface Props {
  breakdown: ComboMonthlyRow[];
  strategies: string[];
}

const STRATEGY_LABELS: Record<string, string> = {
  ma_crossover: 'MA Cross',
  sma_cross: 'SMA Cross',
  ema_cross: 'EMA Cross',
  sma_break: 'SMA Break',
  macd: 'MACD',
  rsi: 'RSI',
  lrsi: 'LRSI',
  aroon: 'Aroon',
  stoch_rsi: 'StochRSI',
  momentum_rotation: 'Momentum',
  new_high_low: 'New High/Low',
  atr_trailing_stop: 'ATR Stop',
  vwap_cross: 'VWAP',
  grid_trading: 'Grid',
  wedge_compression: 'Wedge',
  mean_reversion: 'Mean Rev',
  mean_reversion_trend: 'MR Trend',
  mean_reversion_range: 'MR Range',
  reverting_market: 'Reverting',
  breakout: 'Breakout',
  range_breakout: 'Range BO',
  trend_pullback: 'Trend PB',
  vrp_harvest: 'VRP',
  orb: 'ORB',
  gap_fade: 'Gap Fade',
  seasonal: 'Seasonal',
};

function strategyLabel(name: string): string {
  return STRATEGY_LABELS[name] ?? name;
}

function formatMonth(month: string): string {
  const [year, monthNum] = month.split('-');
  const date = new Date(Number(year), Number(monthNum) - 1, 1);
  return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

interface PositionBadgeProps {
  position: 'Buy' | 'Sell';
}

function PositionBadge({ position }: PositionBadgeProps) {
  const cls =
    position === 'Buy'
      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
      : 'bg-red-500/20 text-red-400 border border-red-500/30';

  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-semibold ${cls}`}>
      {position}
    </span>
  );
}

interface StrategyCellProps {
  strategyName: string;
  row: ComboMonthlyRow;
}

function StrategyCell({ strategyName, row }: StrategyCellProps) {
  const state = row.strategies.find((s) => s.strategy_name === strategyName);
  if (!state) {
    return <td className="px-3 py-2 text-slate-500 text-sm">—</td>;
  }

  const indicatorEntries = Object.entries(state.indicators).filter(([, v]) => v !== null);

  return (
    <td className="px-3 py-2 align-top min-w-[120px]">
      <div className="flex flex-col gap-1">
        <PositionBadge position={state.position} />
        {indicatorEntries.length > 0 && (
          <div className="flex flex-col gap-0.5 mt-1">
            {indicatorEntries.map(([key, val]) => (
              <span key={key} className="text-xs text-slate-400 whitespace-nowrap">
                {key}: {val?.toFixed(2)}
              </span>
            ))}
          </div>
        )}
      </div>
    </td>
  );
}

export function ComboMonthlyTable({ breakdown, strategies }: Props) {
  if (!breakdown || breakdown.length === 0) {
    return null;
  }

  return (
    <div className="mt-6">
      <h3 className="text-sm font-semibold text-slate-300 mb-3">Monthly Strategy Breakdown</h3>
      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="min-w-full text-sm text-slate-300">
          <thead>
            <tr className="bg-slate-800 border-b border-slate-700">
              <th className="px-3 py-2 text-left font-medium text-slate-400 whitespace-nowrap">
                Month
              </th>
              {strategies.map((name) => (
                <th
                  key={name}
                  className="px-3 py-2 text-left font-medium text-slate-400 whitespace-nowrap"
                >
                  {strategyLabel(name)}
                </th>
              ))}
              <th className="px-3 py-2 text-left font-medium text-slate-200 whitespace-nowrap">
                Combined
              </th>
            </tr>
          </thead>
          <tbody>
            {breakdown.map((row, idx) => (
              <tr
                key={row.month}
                className={`border-b border-slate-700/50 ${
                  idx % 2 === 0 ? 'bg-slate-900' : 'bg-slate-800/50'
                }`}
              >
                <td className="px-3 py-2 font-medium text-slate-300 whitespace-nowrap">
                  {formatMonth(row.month)}
                </td>
                {strategies.map((name) => (
                  <StrategyCell key={name} strategyName={name} row={row} />
                ))}
                <td className="px-3 py-2 align-top">
                  <PositionBadge position={row.combined_position} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
