import OhlcvDashboardView from './OhlcvDashboardView';

export default function CryptoDashboardPage() {
  return (
    <OhlcvDashboardView
      title="Crypto Dashboard"
      description="Select a cryptocurrency to view its OHLCV timeline chart."
      basePath="/dashboard/crypto"
      assetTypeFilter={['crypto']}
      searchPlaceholder="Search crypto (e.g. Bitcoin, ETHUSD)"
    />
  );
}
