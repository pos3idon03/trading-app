import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom';
import MarketStatusBar from './components/MarketStatusBar';
import Dashboard from './pages/Dashboard';
import OHLCVChart from './pages/OHLCVChart';
import FinancialsPage from './pages/FinancialsPage';
import MonteCarloPage from './pages/MonteCarloPage';
import BacktestPage from './pages/BacktestPage';
import AgentAnalysisPage from './pages/AgentAnalysisPage';
import LiveTradingPage from './pages/LiveTradingPage';
import StrategyBuilderPage from './pages/StrategyBuilderPage';
import ExecutionPage from './pages/ExecutionPage';
import AutoTradingPage from './pages/AutoTradingPage';

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? 'bg-surface-800 text-brand-500'
            : 'text-slate-400 hover:text-slate-100 hover:bg-surface-800'
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <div className="sticky top-0 z-10">
          <MarketStatusBar />
          <header className="border-b border-slate-800 bg-surface-900">
            <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
              <Link to="/" className="text-brand-500 font-bold text-lg tracking-tight">
                Trading<span className="text-slate-400">App</span>
              </Link>
              <nav className="flex items-center gap-1">
                <NavItem to="/" label="Dashboard" />
                <NavItem to="/ohlcv" label="Price Data" />
                <NavItem to="/financials" label="Financials" />
                <NavItem to="/simulation" label="Simulation" />
                <NavItem to="/backtest" label="Backtest" />
                <NavItem to="/agents" label="AI Agents" />
                <NavItem to="/live" label="Live Trading" />
                <NavItem to="/strategy-builder" label="Strategy Builder" />
                <NavItem to="/auto-trading" label="Auto-Trading" />
                <NavItem to="/execution" label="Execution" />
              </nav>
            </div>
          </header>
        </div>

        <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/ohlcv" element={<OHLCVChart />} />
            <Route path="/financials" element={<FinancialsPage />} />
            <Route path="/simulation" element={<MonteCarloPage />} />
            <Route path="/backtest" element={<BacktestPage />} />
            <Route path="/agents" element={<AgentAnalysisPage />} />
            <Route path="/live" element={<LiveTradingPage />} />
            <Route path="/strategy-builder" element={<StrategyBuilderPage />} />
            <Route path="/auto-trading" element={<AutoTradingPage />} />
            <Route path="/execution" element={<ExecutionPage />} />
          </Routes>
        </main>

        <footer className="border-t border-slate-800 text-slate-600 text-xs text-center py-3">
          Trading App &mdash; Phases 1–6
        </footer>
      </div>
    </BrowserRouter>
  );
}
