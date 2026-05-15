import type { ChartOverlayTradeEntry } from '../api/types';
import MetricCard from './MetricCard';

interface Props {
  trades: ChartOverlayTradeEntry[];
}

interface TradeSummary {
  total: number;
  profitable: number;
  totalPnl: number | null;
  totalReturnPct: number | null;
  avgProfitPct: number | null;
  avgLossPct: number | null;
}

function computeSummary(trades: ChartOverlayTradeEntry[]): TradeSummary {
  const closed = trades.filter((t) => t.return_pct != null);
  const profitable = closed.filter((t) => (t.return_pct ?? 0) > 0);
  const losing = closed.filter((t) => (t.return_pct ?? 0) <= 0);

  const avg = (arr: ChartOverlayTradeEntry[]) =>
    arr.length ? arr.reduce((s, t) => s + (t.return_pct ?? 0), 0) / arr.length : null;

  const pnlTrades = trades.filter((t) => t.pnl != null);
  const totalPnl = pnlTrades.length
    ? pnlTrades.reduce((s, t) => s + (t.pnl ?? 0), 0)
    : null;

  const pctTrades = trades.filter((t) => t.return_pct != null);
  const totalReturnPct = pctTrades.length
    ? pctTrades.reduce((s, t) => s + (t.return_pct ?? 0), 0)
    : null;

  return {
    total: trades.length,
    profitable: profitable.length,
    totalPnl,
    totalReturnPct,
    avgProfitPct: avg(profitable),
    avgLossPct: avg(losing),
  };
}

function splitDateTime(raw: string | null): { date: string; time: string } {
  if (!raw) return { date: '—', time: '—' };
  const normalized = raw.replace(' ', 'T');
  const d = new Date(normalized);
  if (isNaN(d.getTime())) return { date: raw.slice(0, 10), time: '' };
  const date = d.toISOString().slice(0, 10);
  const time = d.toISOString().slice(11, 16);
  return { date, time };
}

function fmtPct(v: number | null, forceSign = false): string {
  if (v == null) return '—';
  const pct = v * 100;
  const sign = forceSign && pct > 0 ? '+' : '';
  return `${sign}${pct.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
}

function fmtPnl(v: number | null): string {
  if (v == null) return '—';
  const sign = v > 0 ? '+' : '';
  return `${sign}${v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function OverlayTradeTable({ trades }: Props) {
  if (!trades.length) return null;

  const summary = computeSummary(trades);
  const totalPnlPositive = summary.totalPnl != null && summary.totalPnl > 0;
  const totalPnlNegative = summary.totalPnl != null && summary.totalPnl < 0;
  const totalReturnPositive = summary.totalReturnPct != null && summary.totalReturnPct > 0;
  const totalReturnNegative = summary.totalReturnPct != null && summary.totalReturnPct < 0;

  return (
    <div className="mt-6 space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard label="Total Transactions" value={summary.total} />
        <MetricCard
          label="Profitable Transactions"
          value={summary.profitable}
          positive={summary.profitable > 0}
        />
        <MetricCard
          label="Total Profit / Loss"
          value={fmtPnl(summary.totalPnl)}
          positive={totalPnlPositive}
          negative={totalPnlNegative}
        />
        <MetricCard
          label="Total Profit/Loss %"
          value={summary.totalReturnPct != null ? fmtPct(summary.totalReturnPct, true) : '—'}
          positive={totalReturnPositive}
          negative={totalReturnNegative}
        />
        <MetricCard
          label="Average Profit %"
          value={summary.avgProfitPct != null ? fmtPct(summary.avgProfitPct, true) : '—'}
          positive={summary.avgProfitPct != null && summary.avgProfitPct > 0}
        />
        <MetricCard
          label="Average Loss %"
          value={summary.avgLossPct != null ? fmtPct(summary.avgLossPct) : '—'}
          negative={summary.avgLossPct != null && summary.avgLossPct < 0}
        />
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-700">
        <table className="w-full text-sm text-slate-300">
          <thead>
            <tr className="bg-surface-800 text-slate-400 text-xs uppercase tracking-wide">
              <th className="px-4 py-3 text-left">#</th>
              <th className="px-4 py-3 text-right">Buy Price</th>
              <th className="px-4 py-3 text-left">Buy Date</th>
              <th className="px-4 py-3 text-left">Buy Time</th>
              <th className="px-4 py-3 text-right">Sell Price</th>
              <th className="px-4 py-3 text-left">Sell Date</th>
              <th className="px-4 py-3 text-right">Profit / Loss</th>
              <th className="px-4 py-3 text-right">Profit/Loss %</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade, idx) => {
              const buy = splitDateTime(trade.entry_time);
              const sell = splitDateTime(trade.exit_time);
              const pct = trade.return_pct;
              const pnl = trade.pnl;
              const colorCls = pct == null ? 'text-slate-400' : pct > 0 ? 'text-green-400' : 'text-red-400';
              const rowCls = idx % 2 === 0 ? 'bg-surface-900' : 'bg-surface-800/60';

              return (
                <tr key={idx} className={`${rowCls} border-t border-slate-700/50`}>
                  <td className="px-4 py-2.5 text-slate-500">{idx + 1}</td>
                  <td className="px-4 py-2.5 text-right font-mono">{trade.entry_price.toFixed(2)}</td>
                  <td className="px-4 py-2.5">{buy.date}</td>
                  <td className="px-4 py-2.5 text-slate-400">{buy.time}</td>
                  <td className="px-4 py-2.5 text-right font-mono">
                    {trade.exit_price != null
                      ? trade.exit_price.toFixed(2)
                      : <span className="text-slate-500 italic">Open</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    {trade.exit_time
                      ? sell.date
                      : <span className="text-slate-500 italic">Open</span>}
                  </td>
                  <td className={`px-4 py-2.5 text-right font-mono font-medium ${colorCls}`}>
                    {fmtPnl(pnl)}
                  </td>
                  <td className={`px-4 py-2.5 text-right font-mono font-medium ${colorCls}`}>
                    {fmtPct(pct, true)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
