import OhlcvDashboardView from './OhlcvDashboardView';

export default function CryptoDashboardPage() {
  return (
    <OhlcvDashboardView
      title="Crypto Dashboard"
      description="Select an ingested cryptocurrency from your watchlist to view its OHLCV timeline chart."
      basePath="/dashboard/crypto"
      assetTypeFilter={['crypto']}
      searchPlaceholder="Search ingested crypto in watchlist"
    />
  );
}
