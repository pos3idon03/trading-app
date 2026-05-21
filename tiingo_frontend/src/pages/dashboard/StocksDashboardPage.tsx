import OhlcvDashboardView from './OhlcvDashboardView';

export default function StocksDashboardPage() {
  return (
    <OhlcvDashboardView
      title="Stocks Dashboard"
      description="Select an ingested stock or ETF from your watchlist to view its OHLCV chart and fundamentals trends below."
      basePath="/dashboard/stocks"
      assetTypeFilter={['stock', 'etf']}
      searchPlaceholder="Search ingested stocks and ETFs in watchlist"
      showFundamentals
    />
  );
}
