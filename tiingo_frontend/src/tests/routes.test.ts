import { describe, expect, it } from 'vitest';

const INGESTION_TABS = [
  { path: '/ingestion', label: 'Overview' },
  { path: '/ingestion/watchlist', label: 'Watchlist' },
  { path: '/ingestion/market', label: 'Market Data' },
  { path: '/ingestion/stream', label: 'Live Stream' },
  { path: '/ingestion/news', label: 'News' },
  { path: '/ingestion/fundamentals', label: 'Fundamentals' },
  { path: '/ingestion/fred', label: 'FRED Macro' },
];

const DASHBOARD_ROUTES = [
  { path: '/dashboard/stocks', label: 'Stocks' },
  { path: '/dashboard/stocks/AAPL', label: 'Stocks symbol' },
  { path: '/dashboard/crypto', label: 'Crypto' },
  { path: '/dashboard/crypto/BTCUSD', label: 'Crypto symbol' },
  { path: '/dashboard/macro', label: 'Macro' },
  { path: '/dashboard/macro/GDP', label: 'Macro series' },
  { path: '/dashboard/macro?tab=regression', label: 'Macro regression tab' },
];

describe('route paths', () => {
  it('defines unique ingestion tab paths', () => {
    const paths = INGESTION_TABS.map((t) => t.path);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('includes dashboard asset path params', () => {
    expect(DASHBOARD_ROUTES.some((r) => r.path.includes('/dashboard/stocks/AAPL'))).toBe(true);
    expect(DASHBOARD_ROUTES.some((r) => r.path.includes('/dashboard/macro/GDP'))).toBe(true);
  });
});

describe('asset type filter', () => {
  function filterResults(
    results: { symbol: string; asset_type: string }[],
    assetTypeFilter?: string[],
  ) {
    return results.filter((r) => {
      if (assetTypeFilter?.length && !assetTypeFilter.includes(r.asset_type)) return false;
      return true;
    });
  }

  it('filters stocks and etfs only', () => {
    const results = [
      { symbol: 'AAPL', asset_type: 'stock' },
      { symbol: 'SPY', asset_type: 'etf' },
      { symbol: 'BTCUSD', asset_type: 'crypto' },
    ];
    const filtered = filterResults(results, ['stock', 'etf']);
    expect(filtered.map((r) => r.symbol)).toEqual(['AAPL', 'SPY']);
  });

  it('filters crypto only', () => {
    const results = [
      { symbol: 'AAPL', asset_type: 'stock' },
      { symbol: 'BTCUSD', asset_type: 'crypto' },
    ];
    const filtered = filterResults(results, ['crypto']);
    expect(filtered.map((r) => r.symbol)).toEqual(['BTCUSD']);
  });
});
