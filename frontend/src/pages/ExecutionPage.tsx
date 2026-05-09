import { useEffect, useState } from 'react';
import { executionApi } from '../api/endpoints';
import type {
  ExecutionStatusResponse,
  OrderItem,
  PortfolioResponse,
  RiskConfigResponse,
  RiskEventItem,
} from '../api/types';
import ErrorAlert from '../components/ErrorAlert';
import MetricCard from '../components/MetricCard';
import StatusBadge from '../components/StatusBadge';

function KillSwitch({ active, onToggle }: { active: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className={`relative px-6 py-3 rounded-xl text-sm font-bold uppercase tracking-wider border-2 transition-all ${
        active
          ? 'bg-red-500/30 text-red-300 border-red-500 shadow-lg shadow-red-500/20 hover:bg-red-500/40'
          : 'bg-green-500/20 text-green-300 border-green-500/50 hover:bg-green-500/30'
      }`}
    >
      <span className="flex items-center gap-2">
        <span className={`h-3 w-3 rounded-full ${active ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`} />
        {active ? 'Kill Switch ACTIVE — Trading Halted' : 'Trading Enabled — Click to Halt'}
      </span>
    </button>
  );
}

function PortfolioOverview({ portfolio }: { portfolio: PortfolioResponse }) {
  const pnlColor = (portfolio.daily_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400';
  return (
    <div className="card">
      <h2 className="text-slate-200 font-semibold mb-4">Portfolio Overview</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <MetricCard label="Equity" value={`$${portfolio.equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} />
        <MetricCard label="Cash" value={`$${portfolio.cash.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} />
        <MetricCard label="Buying Power" value={`$${portfolio.buying_power.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} />
        <div className="p-3 bg-surface-900 rounded-lg border border-slate-700">
          <span className="metric-label">Daily P&L</span>
          <p className={`text-lg font-mono font-semibold ${pnlColor}`}>
            {(portfolio.daily_pnl ?? 0) >= 0 ? '+' : ''}${(portfolio.daily_pnl ?? 0).toFixed(2)}
            <span className="text-xs ml-1">
              ({(portfolio.daily_pnl_pct ?? 0) >= 0 ? '+' : ''}{(portfolio.daily_pnl_pct ?? 0).toFixed(2)}%)
            </span>
          </p>
        </div>
      </div>

      {portfolio.positions.length > 0 && (
        <div className="mt-4">
          <h3 className="text-slate-300 text-sm font-semibold mb-2">Active Positions ({portfolio.total_positions})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-slate-500 border-b border-slate-700">
                  <th className="text-left py-2 pr-4">Symbol</th>
                  <th className="text-right py-2 pr-4">Qty</th>
                  <th className="text-right py-2 pr-4">Avg Entry</th>
                  <th className="text-right py-2 pr-4">Current</th>
                  <th className="text-right py-2 pr-4">Market Value</th>
                  <th className="text-right py-2">P&L</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((p) => (
                  <tr key={p.symbol} className="border-b border-slate-800 text-slate-300">
                    <td className="py-2 pr-4 font-semibold">{p.symbol}</td>
                    <td className="text-right py-2 pr-4 font-mono">{p.qty}</td>
                    <td className="text-right py-2 pr-4 font-mono">${p.avg_entry_price.toFixed(2)}</td>
                    <td className="text-right py-2 pr-4 font-mono">${p.current_price.toFixed(2)}</td>
                    <td className="text-right py-2 pr-4 font-mono">${p.market_value.toFixed(2)}</td>
                    <td className={`text-right py-2 font-mono font-semibold ${p.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl.toFixed(2)}
                      <span className="text-slate-500 ml-1">({(p.unrealized_pnl_pct * 100).toFixed(1)}%)</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function RiskConfigPanel({ config, onUpdate }: {
  config: RiskConfigResponse;
  onUpdate: (field: string, value: number) => void;
}) {
  return (
    <div className="card">
      <h2 className="text-slate-200 font-semibold mb-4">Risk Configuration</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {[
          { key: 'max_position_pct', label: 'Max Position %', value: config.max_position_pct },
          { key: 'max_exposure_pct', label: 'Max Exposure %', value: config.max_exposure_pct },
          { key: 'daily_loss_limit_pct', label: 'Daily Loss Limit %', value: config.daily_loss_limit_pct },
          { key: 'max_orders_per_minute', label: 'Max Orders/min', value: config.max_orders_per_minute },
        ].map((item) => (
          <div key={item.key}>
            <label className="metric-label block mb-1">{item.label}</label>
            <input
              type="number"
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 w-full font-mono"
              value={item.value}
              step={item.key === 'max_orders_per_minute' ? 1 : 0.5}
              onChange={(e) => onUpdate(item.key, parseFloat(e.target.value))}
            />
          </div>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
        <span>Mode: <span className="text-slate-300 font-semibold uppercase">{config.trading_mode}</span></span>
        <span>Kill switch: <span className={config.kill_switch_active ? 'text-red-400' : 'text-green-400'}>{config.kill_switch_active ? 'ACTIVE' : 'OFF'}</span></span>
      </div>
    </div>
  );
}

function OrderHistory({ orders }: { orders: OrderItem[] }) {
  if (orders.length === 0) {
    return (
      <div className="card text-center py-8">
        <p className="text-slate-500 text-sm">No orders yet.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h2 className="text-slate-200 font-semibold mb-4">Order History</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-slate-500 border-b border-slate-700">
              <th className="text-left py-2 pr-3">ID</th>
              <th className="text-left py-2 pr-3">Symbol</th>
              <th className="text-left py-2 pr-3">Side</th>
              <th className="text-right py-2 pr-3">Qty</th>
              <th className="text-left py-2 pr-3">Type</th>
              <th className="text-left py-2 pr-3">Status</th>
              <th className="text-right py-2 pr-3">Fill Price</th>
              <th className="text-left py-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.id} className="border-b border-slate-800 text-slate-300">
                <td className="py-2 pr-3 font-mono">{o.id}</td>
                <td className="py-2 pr-3 font-semibold">{o.symbol}</td>
                <td className={`py-2 pr-3 font-semibold uppercase ${o.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                  {o.side}
                </td>
                <td className="text-right py-2 pr-3 font-mono">{o.qty}</td>
                <td className="py-2 pr-3">{o.order_type}</td>
                <td className="py-2 pr-3"><StatusBadge status={o.status} /></td>
                <td className="text-right py-2 pr-3 font-mono">
                  {o.filled_price ? `$${o.filled_price.toFixed(2)}` : '—'}
                </td>
                <td className="py-2 text-slate-500">{new Date(o.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RiskEventLog({ events }: { events: RiskEventItem[] }) {
  if (events.length === 0) return null;

  const severityColor: Record<string, string> = {
    critical: 'text-red-400 bg-red-500/10 border-red-500/20',
    warning: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
    info: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  };

  return (
    <div className="card">
      <h2 className="text-slate-200 font-semibold mb-4">Risk Events</h2>
      <div className="space-y-2">
        {events.map((e) => (
          <div key={e.id} className={`p-3 rounded-lg border text-xs ${severityColor[e.severity] ?? severityColor.info}`}>
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold uppercase tracking-wide">{e.event_type}</span>
              <span className="text-slate-500">{new Date(e.created_at).toLocaleString()}</span>
            </div>
            <p>{e.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ExecutionPage() {
  const [status, setStatus] = useState<ExecutionStatusResponse | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [riskConfig, setRiskConfig] = useState<RiskConfigResponse | null>(null);
  const [orders, setOrders] = useState<OrderItem[]>([]);
  const [riskEvents, setRiskEvents] = useState<RiskEventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAll = async () => {
    try {
      const [st, pf, rc, oh, re] = await Promise.all([
        executionApi.getStatus(),
        executionApi.getPortfolio(),
        executionApi.getRiskConfig(),
        executionApi.getOrders(),
        executionApi.getRiskEvents(),
      ]);
      setStatus(st);
      setPortfolio(pf);
      setRiskConfig(rc);
      setOrders(oh.orders);
      setRiskEvents(re.events);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const toggleKillSwitch = async () => {
    try {
      if (riskConfig?.kill_switch_active) {
        await executionApi.enable();
      } else {
        await executionApi.disable();
      }
      await fetchAll();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const updateRiskField = async (field: string, value: number) => {
    try {
      const updated = await executionApi.updateRiskConfig({ [field]: value });
      setRiskConfig(updated);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-slate-400 text-sm">Loading execution dashboard…</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Execution & Risk Management</h1>
          <p className="text-slate-400 text-sm mt-1">
            Paper trading execution, portfolio tracking, and hardcoded risk controls.
          </p>
        </div>
        <button onClick={fetchAll} className="px-3 py-2 rounded-lg text-sm bg-surface-800 text-slate-300 hover:bg-surface-700">
          Refresh
        </button>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Kill switch */}
      <div className="card flex items-center justify-between">
        <div>
          <h2 className="text-slate-200 font-semibold">Master Kill Switch</h2>
          <p className="text-slate-500 text-xs mt-1">
            Immediately halts ALL trading activity. Overrides all signals and strategies.
          </p>
        </div>
        <KillSwitch
          active={riskConfig?.kill_switch_active ?? false}
          onToggle={toggleKillSwitch}
        />
      </div>

      {/* Status summary */}
      {status && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <MetricCard
            label="Trading Mode"
            value={status.trading_mode.toUpperCase()}
          />
          <MetricCard
            label="Stream"
            value={status.stream_connected ? 'Connected' : 'Disconnected'}
          />
          <MetricCard
            label="Symbols"
            value={status.subscribed_symbols.join(', ') || 'None'}
          />
          <MetricCard
            label="Kill Switch"
            value={status.kill_switch_active ? 'ACTIVE' : 'OFF'}
          />
        </div>
      )}

      {portfolio && <PortfolioOverview portfolio={portfolio} />}
      {riskConfig && <RiskConfigPanel config={riskConfig} onUpdate={updateRiskField} />}
      <OrderHistory orders={orders} />
      <RiskEventLog events={riskEvents} />
    </div>
  );
}
