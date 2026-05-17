import { useEffect, useState } from 'react';
import { executionApi } from '../api/endpoints';
import type {
  PortfolioResponse,
  RiskConfigResponse,
} from '../api/types';
import ErrorAlert from '../components/ErrorAlert';
import ExecutionAssetCard from '../components/ExecutionAssetCard';
import MetricCard from '../components/MetricCard';
import Spinner from '../components/Spinner';
import { useExecutionMonitor } from '../hooks/useExecutionMonitor';

// ---------------------------------------------------------------------------
// Kill switch
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Portfolio overview
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Empty state for monitoring
// ---------------------------------------------------------------------------

function EmptyMonitor() {
  return (
    <div className="card text-center py-12">
      <p className="text-slate-400 text-sm">No auto-trading assets are currently running.</p>
      <p className="text-slate-600 text-xs mt-1">
        Start an asset from the Auto-Trading page to see live monitoring here.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ExecutionPage() {
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [riskConfig, setRiskConfig] = useState<RiskConfigResponse | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [riskLoading, setRiskLoading] = useState(true);

  const { monitors, assetsLoading, assetsError, refresh, setOrdersPage } = useExecutionMonitor();

  const fetchRiskData = async () => {
    try {
      const [pf, rc] = await Promise.all([
        executionApi.getPortfolio(),
        executionApi.getRiskConfig(),
      ]);
      setPortfolio(pf);
      setRiskConfig(rc);
    } catch (err) {
      setStatusError((err as Error).message);
    } finally {
      setRiskLoading(false);
    }
  };

  useEffect(() => { fetchRiskData(); }, []);

  const toggleKillSwitch = async () => {
    try {
      if (riskConfig?.kill_switch_active) {
        await executionApi.enable();
      } else {
        await executionApi.disable();
      }
      await fetchRiskData();
    } catch (err) {
      setStatusError((err as Error).message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Execution</h1>
          <p className="text-slate-400 text-sm mt-1">
            Live monitoring of auto-trading criteria, signals, and transactions.
          </p>
        </div>
        <button
          onClick={() => { fetchRiskData(); refresh(); }}
          className="px-3 py-2 rounded-lg text-sm bg-surface-800 text-slate-300 hover:bg-surface-700"
        >
          Refresh
        </button>
      </div>

      {(statusError || assetsError) && (
        <ErrorAlert message={statusError ?? assetsError ?? ''} />
      )}

      {/* Kill switch */}
      {!riskLoading && riskConfig && (
        <div className="card flex items-center justify-between">
          <div>
            <h2 className="text-slate-200 font-semibold">Master Kill Switch</h2>
            <p className="text-slate-500 text-xs mt-1">
              Immediately halts ALL trading activity. Overrides all signals and strategies.
            </p>
          </div>
          <KillSwitch active={riskConfig.kill_switch_active} onToggle={toggleKillSwitch} />
        </div>
      )}

      {/* Portfolio */}
      {portfolio && <PortfolioOverview portfolio={portfolio} />}

      {/* Auto-trading monitor section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-slate-200 font-semibold text-lg">Live Auto-Trading Monitor</h2>
          {monitors.length > 0 && (
            <span className="text-xs text-slate-500">
              {monitors.length} asset{monitors.length !== 1 ? 's' : ''} running · polling per timeframe
            </span>
          )}
        </div>

        {assetsLoading ? (
          <div className="flex justify-center py-12">
            <Spinner />
          </div>
        ) : monitors.length === 0 ? (
          <EmptyMonitor />
        ) : (
          <div className="space-y-6">
            {monitors.map((m) => (
              <ExecutionAssetCard
                key={m.strategyId}
                monitor={m}
                onOrdersPageChange={(page) => setOrdersPage(m.strategyId, page)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
