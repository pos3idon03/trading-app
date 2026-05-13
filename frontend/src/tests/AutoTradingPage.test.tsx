import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AutoTradingPage from '../pages/AutoTradingPage';
import type { AutoTradingAssetRow } from '../api/types';

const mockRow: AutoTradingAssetRow = {
  strategy_id: 1,
  asset_id: 10,
  symbol: 'AAPL',
  asset_name: 'Apple Inc.',
  mc_prob_positive: 0.72,
  mc_buy_prob_positive: 0.65,
  mc_sell_prob_positive: 0.4,
  ai_conviction: 0.85,
  ai_sentiment: 0.4,
  ai_macro: 0.3,
  ai_buy_conviction: 0.7,
  ai_sell_conviction: 0.3,
  ai_buy_sentiment: 0.2,
  ai_sell_sentiment: -0.1,
  ai_buy_macro: 0.1,
  ai_sell_macro: -0.2,
  combination_mode: 'all',
  algo_timeframe: '1d',
  auto_trading_started: false,
  max_amount_per_position: null,
  max_pct_of_capital: null,
};

const mockRowStarted: AutoTradingAssetRow = {
  ...mockRow,
  auto_trading_started: true,
};

vi.mock('../api/endpoints', () => ({
  autoTradingApi: {
    list: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
  },
}));

describe('AutoTradingPage', () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { autoTradingApi } = await import('../api/endpoints');
    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockRow]);
  });

  it('renders page heading', async () => {
    render(<AutoTradingPage />);
    expect(screen.getByText('Auto-Trading')).toBeInTheDocument();
  });

  it('renders asset row with symbol after loading', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('AAPL')).toBeInTheDocument();
      expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
    });
  });

  it('shows empty state when no assets', async () => {
    const { autoTradingApi } = await import('../api/endpoints');
    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([]);

    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText(/No assets have auto-trading enabled/i)).toBeInTheDocument();
    });
  });

  it('shows error when list fails', async () => {
    const { autoTradingApi } = await import('../api/endpoints');
    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));

    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText(/Failed to load auto-trading assets/i)).toBeInTheDocument();
    });
  });

  it('shows Stopped status badge for non-started asset', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('Stopped')).toBeInTheDocument();
    });
  });

  it('shows Start button for non-started asset', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('Start')).toBeInTheDocument();
    });
  });

  it('shows Running status badge and Stop button for started asset', async () => {
    const { autoTradingApi } = await import('../api/endpoints');
    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockRowStarted]);

    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('Running')).toBeInTheDocument();
      expect(screen.getByText('Stop')).toBeInTheDocument();
    });
  });

  it('opens position sizing modal when Start is clicked', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => screen.getByText('Start'));
    fireEvent.click(screen.getByText('Start'));
    expect(screen.getByText(/Start Auto-Trading/)).toBeInTheDocument();
  });

  it('calls autoTradingApi.stop when Stop is clicked', async () => {
    const { autoTradingApi } = await import('../api/endpoints');
    (autoTradingApi.list as ReturnType<typeof vi.fn>).mockResolvedValue([mockRowStarted]);
    (autoTradingApi.stop as ReturnType<typeof vi.fn>).mockResolvedValue(mockRow);

    render(<AutoTradingPage />);
    await waitFor(() => screen.getByText('Stop'));
    fireEvent.click(screen.getByText('Stop'));
    await waitFor(() => {
      expect(autoTradingApi.stop).toHaveBeenCalledWith(1);
    });
  });

  it('renders threshold columns in table header', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('MC Prob+')).toBeInTheDocument();
      expect(screen.getByText('AI Conviction')).toBeInTheDocument();
      expect(screen.getByText('AI Sentiment')).toBeInTheDocument();
      expect(screen.getByText('AI Macro')).toBeInTheDocument();
      expect(screen.getByText('Timeframe')).toBeInTheDocument();
    });
  });

  it('renders combo mode badge', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('All')).toBeInTheDocument();
    });
  });

  it('renders MC values in row', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('72.0%')).toBeInTheDocument();
    });
  });

  it('renders buy/sell threshold hints in MC cell', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getByText('buy ≥ 65.0%')).toBeInTheDocument();
      expect(screen.getByText('sell ≤ 40.0%')).toBeInTheDocument();
    });
  });

  it('renders algo timeframe badge', async () => {
    render(<AutoTradingPage />);
    await waitFor(() => {
      expect(screen.getAllByText('1d').length).toBeGreaterThan(0);
    });
  });
});
