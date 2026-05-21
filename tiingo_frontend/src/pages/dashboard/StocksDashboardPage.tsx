import OhlcvDashboardView from './OhlcvDashboardView';

export default function StocksDashboardPage() {
  return (
    <OhlcvDashboardView
      title="Stocks Dashboard"
      description="Select a stock or ETF to view its OHLCV timeline chart."
      basePath="/dashboard/stocks"
      assetTypeFilter={['stock', 'etf']}
      searchPlaceholder="Search stocks and ETFs (e.g. Apple, MSFT)"
    />
  );
}
