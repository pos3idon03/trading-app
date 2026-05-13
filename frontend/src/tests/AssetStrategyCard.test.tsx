import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import AssetStrategyCard from '../components/AssetStrategyCard';
import type { StrategyRecord, StrategyFullResponse } from '../api/types';

const mockStrategy: StrategyRecord = {
  id: 1,
  asset_id: 10,
  symbol: 'AAPL',
  asset_name: 'Apple Inc.',
  is_active: true,
  mc_buy_prob_positive: null,
  mc_sell_prob_positive: null,
  ai_buy_conviction: null,
  ai_sell_conviction: null,
  ai_buy_sentiment: null,
  ai_sell_sentiment: null,
  ai_buy_macro: null,
  ai_sell_macro: null,
  combination_mode: 'all',
  algo_timeframe: '1d',
  auto_trading_enabled: false,
  auto_trading_started: false,
  max_amount_per_position: null,
  max_pct_of_capital: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockFullResponse: StrategyFullResponse = {
  strategy_id: 1,
  asset_id: 10,
  symbol: 'AAPL',
  asset_name: 'Apple Inc.',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  mc_buy_prob_positive: null,
  mc_sell_prob_positive: null,
  ai_buy_conviction: null,
  ai_sell_conviction: null,
  ai_buy_sentiment: null,
  ai_sell_sentiment: null,
  ai_buy_macro: null,
  ai_sell_macro: null,
  combination_mode: 'all',
  algo_timeframe: '1d',
  auto_trading_enabled: false,
  auto_trading_started: false,
  max_amount_per_position: null,
  max_pct_of_capital: null,
  monte_carlo: {
    simulation_id: 1,
    prob_positive_return: 0.65,
    mean_max_drawdown: -0.18,
    p5: 80.0,
    p25: 95.0,
    p50: 110.0,
    p75: 125.0,
    p95: 145.0,
    mean_terminal: 112.0,
    std_terminal: 15.0,
    cached: false,
  },
  ai_agents: {
    analysis_id: 5,
    bias: 'bullish',
    conviction_score: 0.75,
    sentiment_score: 0.6,
    macro_score: null,
    fundamental_summary: 'Strong earnings',
    macro_summary: null,
    reasoning: null,
    key_risk: 'Regulatory risk',
    created_at: '2024-01-01T00:00:00Z',
  },
  financials: {
    revenue_growth: 0.08,
    free_cash_flow: 90e9,
    current_ratio: 1.5,
    pe_ttm: 28.0,
    pe_forward: 24.0,
    pb_ratio: 45.0,
    eps_ttm: 6.1,
    eps_forward: 7.2,
    market_cap: 3e12,
    fetched_at: '2024-01-01T00:00:00Z',
    is_stale: false,
  },
  algo_strategies: [
    {
      backtest_id: 42,
      strategy_name: 'ma_crossover',
      total_return: 0.25,
      sharpe_ratio: 1.2,
      max_drawdown: -0.1,
      win_rate: 0.55,
      num_trades: 12,
      added_at: '2024-01-01T00:00:00Z',
    },
  ],
  monte_carlo_error: null,
  ai_agents_error: null,
  financials_error: null,
};

vi.mock('../api/endpoints', () => ({
  strategyBuilderApi: {
    getFull: vi.fn(),
    remove: vi.fn().mockResolvedValue({ deleted: true }),
    detachBacktest: vi.fn().mockResolvedValue({}),
    attachBacktest: vi.fn().mockResolvedValue({}),
    updateThresholds: vi.fn(),
    list: vi.fn().mockResolvedValue([]),
    create: vi.fn().mockResolvedValue({}),
  },
}));

describe('AssetStrategyCard', () => {
  const onRemove = vi.fn();
  const onUpdated = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();
    const { strategyBuilderApi } = await import('../api/endpoints');
    (strategyBuilderApi.getFull as ReturnType<typeof vi.fn>).mockResolvedValue(mockFullResponse);
    (strategyBuilderApi.updateThresholds as ReturnType<typeof vi.fn>).mockResolvedValue(mockStrategy);
  });

  it('renders the asset symbol and name', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    expect(screen.getByText('AAPL')).toBeInTheDocument();
    expect(screen.getByText('Apple Inc.')).toBeInTheDocument();
  });

  it('shows spinner while loading', () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    expect(document.querySelector('[class*="animate"]') || screen.queryByRole('img')).toBeTruthy();
  });

  it('renders Monte Carlo section after load', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('Prob. Positive Return')).toBeInTheDocument();
      expect(screen.getByText('65.00%')).toBeInTheDocument();
    });
  });

  it('renders MC buy/sell threshold inputs', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('Min Prob. Positive (BUY)')).toBeInTheDocument();
      expect(screen.getByText('Max Prob. Positive (SELL)')).toBeInTheDocument();
    });
  });

  it('renders AI Agents section with bias', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('bullish')).toBeInTheDocument();
      expect(screen.getByText('Conviction Score')).toBeInTheDocument();
    });
  });

  it('renders AI buy and sell threshold inputs', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('Min Conviction (BUY)')).toBeInTheDocument();
      expect(screen.getByText('Max Conviction (SELL)')).toBeInTheDocument();
      expect(screen.getByText('Min Sentiment (BUY)')).toBeInTheDocument();
      expect(screen.getByText('Max Sentiment (SELL)')).toBeInTheDocument();
      expect(screen.getByText('Min Macro (BUY)')).toBeInTheDocument();
      expect(screen.getByText('Max Macro (SELL)')).toBeInTheDocument();
    });
  });

  it('renders algo timeframe selector', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('Trading Timeframe')).toBeInTheDocument();
      expect(screen.getByDisplayValue('1d')).toBeInTheDocument();
    });
  });

  it('renders combination mode selector', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('Signal Combination')).toBeInTheDocument();
      expect(screen.getByDisplayValue('All Agree (AND)')).toBeInTheDocument();
    });
  });

  it('renders auto-trading toggle', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    expect(screen.getByText('Auto-Trading')).toBeInTheDocument();
    expect(screen.getByLabelText('Toggle auto-trading')).toBeInTheDocument();
  });

  it('calls updateThresholds with new field names when Save Thresholds is clicked', async () => {
    const { strategyBuilderApi } = await import('../api/endpoints');
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => screen.getByText('Save Thresholds'));
    fireEvent.click(screen.getByText('Save Thresholds'));
    await waitFor(() => {
      expect(strategyBuilderApi.updateThresholds).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          mc_buy_prob_positive: null,
          mc_sell_prob_positive: null,
          ai_buy_conviction: null,
          ai_sell_conviction: null,
        }),
      );
    });
  });

  it('calls updateThresholds when auto-trading toggle is clicked', async () => {
    const { strategyBuilderApi } = await import('../api/endpoints');
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    fireEvent.click(screen.getByLabelText('Toggle auto-trading'));
    await waitFor(() => {
      expect(strategyBuilderApi.updateThresholds).toHaveBeenCalledWith(
        1, expect.objectContaining({ auto_trading_enabled: true })
      );
    });
  });

  it('renders Financials section', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('P/E (TTM)')).toBeInTheDocument();
      expect(screen.getByText('28.00')).toBeInTheDocument();
    });
  });

  it('renders Algo Strategies section', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText('MA Crossover')).toBeInTheDocument();
      expect(screen.getByText(/25.00%/)).toBeInTheDocument();
    });
  });

  it('shows error when getFull fails', async () => {
    const { strategyBuilderApi } = await import('../api/endpoints');
    (strategyBuilderApi.getFull as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('network error'));

    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => {
      expect(screen.getByText(/Failed to load strategy data/i)).toBeInTheDocument();
    });
  });

  it('renders section collapse toggles', async () => {
    render(<AssetStrategyCard strategy={mockStrategy} onRemove={onRemove} onUpdated={onUpdated} />);
    await waitFor(() => screen.getByText('Monte Carlo (Merton Jump-Diffusion)'));
    const sectionToggle = screen.getByText('Monte Carlo (Merton Jump-Diffusion)');
    fireEvent.click(sectionToggle);
    await waitFor(() => {
      expect(screen.queryByText('Prob. Positive Return')).not.toBeInTheDocument();
    });
  });
});
