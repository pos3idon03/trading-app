import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LiveTradingPage from '../pages/LiveTradingPage';

vi.mock('../api/endpoints', () => ({
  dataApi: {
    getAssets: vi.fn().mockResolvedValue({
      assets: [
        { id: 1, symbol: 'AAPL', name: 'Apple Inc.', asset_type: 'stock', exchange: 'NASDAQ', currency: 'USD', is_active: true },
        { id: 2, symbol: 'MSFT', name: 'Microsoft Corp.', asset_type: 'stock', exchange: 'NASDAQ', currency: 'USD', is_active: true },
      ],
      count: 2,
    }),
  },
  liveApi: {
    getStatus: vi.fn().mockResolvedValue({
      connected: false,
      subscribed_symbols: [],
      last_tick_at: null,
      error: null,
      reconnect_count: 0,
    }),
    startStream: vi.fn().mockResolvedValue({
      connected: true,
      subscribed_symbols: ['AAPL'],
      last_tick_at: null,
      error: null,
      reconnect_count: 0,
    }),
    stopStream: vi.fn().mockResolvedValue({
      connected: false,
      subscribed_symbols: [],
      last_tick_at: null,
      error: null,
      reconnect_count: 0,
    }),
    getIndicators: vi.fn().mockResolvedValue({
      symbol: 'AAPL',
      timeframe: '1h',
      close_price: 175.5,
      rsi: 55.2,
      macd: 0.12,
      macd_signal: 0.08,
      macd_histogram: 0.04,
      bb_upper: 180.0,
      bb_middle: 175.0,
      bb_lower: 170.0,
      vwap: 174.8,
      bb_percent: 0.55,
    }),
    getStrategySignals: vi.fn().mockResolvedValue({
      symbol: 'AAPL',
      timeframe: '1h',
      bar_count: 60,
      strategies: [
        { strategy: 'rsi', label: 'RSI (Relative Strength Index)', group: 'Momentum', signal: 'BUY' },
        { strategy: 'macd', label: 'MACD', group: 'Momentum', signal: 'SELL' },
        { strategy: 'ma_crossover', label: 'MA Crossover', group: 'Original', signal: 'NEUTRAL' },
      ],
    }),
  },
}));

describe('LiveTradingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page heading', () => {
    render(<LiveTradingPage />);
    expect(screen.getByText('Live Trading')).toBeInTheDocument();
  });

  it('renders stream control panel', () => {
    render(<LiveTradingPage />);
    expect(screen.getByText('Stream Control')).toBeInTheDocument();
  });

  it('shows empty state when no streams added', () => {
    render(<LiveTradingPage />);
    expect(screen.getByText(/Add a symbol above/i)).toBeInTheDocument();
  });

  it('shows Add Stream button after assets load', async () => {
    render(<LiveTradingPage />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /\+ Add Stream/i })).toBeInTheDocument();
    });
  });

  it('adds a stream card when Add Stream is clicked', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    expect(screen.getByText('AAPL')).toBeInTheDocument();
  });

  it('fetches indicator data immediately on add without starting stream', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    const { liveApi } = await import('../api/endpoints');
    await waitFor(() => {
      expect(liveApi.getIndicators).toHaveBeenCalledWith('AAPL', '1h');
    });
  });

  it('removes a stream card when Remove is clicked', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    expect(screen.getByRole('button', { name: /Remove AAPL stream/i })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Remove AAPL stream/i }));

    expect(screen.queryByRole('button', { name: /Remove AAPL stream/i })).not.toBeInTheDocument();
  });

  it('shows Start Live Stream button when streams are added', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    expect(screen.getByRole('button', { name: /Start Live Stream/i })).toBeInTheDocument();
  });

  it('shows Stop Stream button after starting the live stream', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /Start Live Stream/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Stop Stream/i })).toBeInTheDocument();
    });
  });

  it('prevents adding the same symbol twice', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    const removeButtons = screen.getAllByRole('button', { name: /Remove AAPL stream/i });
    expect(removeButtons.length).toBe(1);
  });
});

describe('LiveStreamCard — strategy signals display', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows indicator data after adding a stream (no start required)', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    await waitFor(() => {
      expect(screen.getByText('$175.50')).toBeInTheDocument();
    });
  });

  it('shows strategy signals after stream starts and bars accumulate', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    await waitFor(() => {
      expect(screen.getByText('RSI (Relative Strength Index)')).toBeInTheDocument();
    });
  });

  it('shows BUY signal badge in strategy panel', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    await waitFor(() => {
      expect(screen.getByText('BUY')).toBeInTheDocument();
    });
  });

  it('shows summary counts for BUY and SELL', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    await waitFor(() => {
      expect(screen.getByText(/1 BUY/i)).toBeInTheDocument();
      expect(screen.getByText(/1 SELL/i)).toBeInTheDocument();
    });
  });

  it('shows strategy group label in panel', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));

    await waitFor(() => {
      expect(screen.getByText('Momentum')).toBeInTheDocument();
    });
  });

  it('shows Live badge when stream is running', async () => {
    const user = userEvent.setup();
    render(<LiveTradingPage />);

    await waitFor(() => screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /\+ Add Stream/i }));
    await user.click(screen.getByRole('button', { name: /Start Live Stream/i }));

    await waitFor(() => {
      expect(screen.getByText('Live')).toBeInTheDocument();
    });
  });
});
