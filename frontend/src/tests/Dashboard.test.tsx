import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import Dashboard from '../pages/Dashboard';
import type { AssetWithPrice, IngestionStatusResponse } from '../api/types';

vi.mock('../api/endpoints', () => ({
  dataApi: {
    getStatus: vi.fn(),
    getAssetsWithPrices: vi.fn(),
    triggerIngestion: vi.fn(),
    deleteAsset: vi.fn(),
  },
}));

import { dataApi } from '../api/endpoints';

const mockStatus: IngestionStatusResponse = {
  status: 'running',
  active_jobs: 0,
  scheduled_jobs: [],
};

function makeAsset(overrides: Partial<AssetWithPrice> = {}): AssetWithPrice {
  return {
    id: 1,
    symbol: 'AAPL',
    name: 'Apple Inc.',
    asset_type: 'stock',
    exchange: 'NASDAQ',
    currency: 'USD',
    is_active: true,
    latest_close: 175.50,
    latest_update: '2024-01-15T00:00:00Z',
    ...overrides,
  };
}

function makeAssets(count: number): AssetWithPrice[] {
  return Array.from({ length: count }, (_, i) => makeAsset({
    id: i + 1,
    symbol: `SYM${String(i + 1).padStart(2, '0')}`,
    name: `Company ${i + 1}`,
    latest_close: 100 + i,
  }));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(dataApi.getStatus).mockResolvedValue(mockStatus);
  vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets: [], count: 0 });
});

describe('Dashboard – Ingested Assets Table', () => {
  it('renders table with asset data', async () => {
    const assets = [
      makeAsset({ symbol: 'AAPL', name: 'Apple Inc.', latest_close: 175.50 }),
      makeAsset({ id: 2, symbol: 'MSFT', name: 'Microsoft Corporation', latest_close: 320.00 }),
    ];
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: assets.length });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.getByText('MSFT')).toBeInTheDocument();
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
      expect(screen.getByText('Microsoft Corporation')).toBeInTheDocument();
      expect(screen.getByText('$175.50')).toBeInTheDocument();
      expect(screen.getByText('$320.00')).toBeInTheDocument();
    });
  });

  it('shows empty state when no assets', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('No assets ingested yet.')).toBeInTheDocument();
    });
  });

  it('shows null price as dash', async () => {
    const assets = [makeAsset({ latest_close: null, latest_update: null })];
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: 1 });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
    });

    const dashes = screen.getAllByText('—');
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it('paginates assets with 20 per page', async () => {
    const assets = makeAssets(25);
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: assets.length });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('SYM01')).toBeInTheDocument();
      expect(screen.queryByText('SYM21')).not.toBeInTheDocument();
    });

    expect(screen.getByText(/Page 1 of 2/)).toBeInTheDocument();

    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => {
      expect(screen.getByText('SYM21')).toBeInTheDocument();
      expect(screen.queryByText('SYM01')).not.toBeInTheDocument();
    });

    expect(screen.getByText(/Page 2 of 2/)).toBeInTheDocument();
  });

  it('previous button navigates back', async () => {
    const assets = makeAssets(25);
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: assets.length });

    render(<Dashboard />);

    await waitFor(() => expect(screen.getByText('Next')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => expect(screen.getByText('SYM21')).toBeInTheDocument());

    fireEvent.click(screen.getByText('Previous'));

    await waitFor(() => {
      expect(screen.getByText('SYM01')).toBeInTheDocument();
    });
  });

  it('shows delete confirmation dialog on Delete click', async () => {
    const assets = [makeAsset()];
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: 1 });

    render(<Dashboard />);

    await waitFor(() => expect(screen.getByText('AAPL')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }));

    expect(screen.getByText(/Delete AAPL\?/)).toBeInTheDocument();
    expect(screen.getByText(/permanently delete/)).toBeInTheDocument();
  });

  it('cancels delete confirmation without calling API', async () => {
    const assets = [makeAsset()];
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: 1 });

    render(<Dashboard />);

    await waitFor(() => expect(screen.getByText('AAPL')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByText(/Delete AAPL\?/)).not.toBeInTheDocument();
    expect(vi.mocked(dataApi.deleteAsset)).not.toHaveBeenCalled();
  });

  it('calls deleteAsset and refreshes on confirmed delete', async () => {
    const assets = [makeAsset()];
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: 1 });
    vi.mocked(dataApi.deleteAsset).mockResolvedValue({
      symbol: 'AAPL',
      deleted: true,
      message: 'Deleted',
    });

    render(<Dashboard />);

    await waitFor(() => expect(screen.getByText('AAPL')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }));

    const confirmBtn = screen.getByRole('button', { name: 'Delete' });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(vi.mocked(dataApi.deleteAsset)).toHaveBeenCalledWith('AAPL');
    });

    expect(vi.mocked(dataApi.getAssetsWithPrices)).toHaveBeenCalledTimes(2);
  });

  it('calls triggerIngestion with correct symbol on Re-ingest', async () => {
    const assets = [makeAsset({ symbol: 'TSLA', name: 'Tesla' })];
    vi.mocked(dataApi.getAssetsWithPrices).mockResolvedValue({ assets, count: 1 });
    vi.mocked(dataApi.triggerIngestion).mockResolvedValue({
      job_id: 'job-123',
      status: 'completed',
      symbols: ['TSLA'],
      timeframes: ['1d', '1h'],
      message: 'Done',
    });

    render(<Dashboard />);

    await waitFor(() => expect(screen.getByText('TSLA')).toBeInTheDocument());

    fireEvent.click(screen.getByRole('button', { name: 'Re-ingest' }));

    await waitFor(() => {
      expect(vi.mocked(dataApi.triggerIngestion)).toHaveBeenCalledWith(
        expect.objectContaining({ symbols: ['TSLA'] }),
      );
    });
  });
});
