import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppShell from './components/layout/AppShell';
import IngestionLayout from './pages/IngestionLayout';
import OverviewTab from './pages/ingestion/OverviewTab';
import WatchlistTab from './pages/ingestion/WatchlistTab';
import JobsTab from './pages/ingestion/JobsTab';
import MarketDataTab from './pages/ingestion/MarketDataTab';
import LiveStreamTab from './pages/ingestion/LiveStreamTab';
import NewsTab from './pages/ingestion/NewsTab';
import FundamentalsTab from './pages/ingestion/FundamentalsTab';
import FredMacroTab from './pages/ingestion/FredMacroTab';
import StocksDashboardPage from './pages/dashboard/StocksDashboardPage';
import CryptoDashboardPage from './pages/dashboard/CryptoDashboardPage';
import MacroDashboardPage from './pages/dashboard/MacroDashboardPage';
import OverviewPage from './pages/dashboard/OverviewPage';
import AlgosPage from './pages/backtesting/AlgosPage';
import MLPage from './pages/backtesting/MLPage';
import TradingModelsPage from './pages/backtesting/TradingModelsPage';
import FoundationPage from './pages/backtesting/FoundationPage';
import DeploymentsPage from './pages/trading/DeploymentsPage';
import PortfolioPage from './pages/trading/PortfolioPage';
import OrdersPage from './pages/trading/OrdersPage';
import ControlsPage from './pages/trading/ControlsPage';
import ActivityPage from './pages/trading/ActivityPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<Navigate to="/ingestion" replace />} />
          <Route path="ingestion" element={<IngestionLayout />}>
            <Route index element={<OverviewTab />} />
            <Route path="watchlist" element={<WatchlistTab />} />
            <Route path="jobs" element={<JobsTab />} />
            <Route path="market" element={<MarketDataTab />} />
            <Route path="stream" element={<LiveStreamTab />} />
            <Route path="news" element={<NewsTab />} />
            <Route path="fundamentals" element={<FundamentalsTab />} />
            <Route path="fred" element={<FredMacroTab />} />
          </Route>
          <Route path="dashboard/overview" element={<OverviewPage />} />
          <Route path="dashboard/stocks" element={<StocksDashboardPage />} />
          <Route path="dashboard/stocks/:symbol" element={<StocksDashboardPage />} />
          <Route path="dashboard/crypto" element={<CryptoDashboardPage />} />
          <Route path="dashboard/crypto/:symbol" element={<CryptoDashboardPage />} />
          <Route path="dashboard/macro" element={<MacroDashboardPage />} />
          <Route path="dashboard/macro/:seriesId" element={<MacroDashboardPage />} />
          <Route path="backtesting" element={<Navigate to="/backtesting/algos" replace />} />
          <Route path="backtesting/algos" element={<AlgosPage />} />
          <Route path="backtesting/algos/:symbol" element={<AlgosPage />} />
          <Route path="backtesting/ml" element={<MLPage />} />
          <Route path="backtesting/ml/:symbol" element={<MLPage />} />
          <Route path="backtesting/foundation" element={<FoundationPage />} />
          <Route path="backtesting/foundation/:symbol" element={<FoundationPage />} />
          <Route path="backtesting/trading-models" element={<TradingModelsPage />} />
          <Route path="trading" element={<Navigate to="/trading/deployments" replace />} />
          <Route path="trading/deployments" element={<DeploymentsPage />} />
          <Route path="trading/activity" element={<ActivityPage />} />
          <Route path="trading/portfolio" element={<PortfolioPage />} />
          <Route path="trading/orders" element={<OrdersPage />} />
          <Route path="trading/controls" element={<ControlsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
