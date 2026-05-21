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
          <Route path="dashboard/stocks" element={<StocksDashboardPage />} />
          <Route path="dashboard/stocks/:symbol" element={<StocksDashboardPage />} />
          <Route path="dashboard/crypto" element={<CryptoDashboardPage />} />
          <Route path="dashboard/crypto/:symbol" element={<CryptoDashboardPage />} />
          <Route path="dashboard/macro" element={<MacroDashboardPage />} />
          <Route path="dashboard/macro/:seriesId" element={<MacroDashboardPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
