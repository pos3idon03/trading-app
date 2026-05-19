import { describe, it, expect, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import ExecutionAssetCard from '../components/ExecutionAssetCard';
import type { ExecutionAssetMonitor, OrderItem } from '../api/types';

const noopPageChange = vi.fn();

function renderCard(monitor: ExecutionAssetMonitor, onOrdersPageChange = noopPageChange) {
  return render(
    <ExecutionAssetCard monitor={monitor} onOrdersPageChange={onOrdersPageChange} />,
  );
}

function expandCard() {
  fireEvent.click(screen.getByRole('button', { name: /expand asset details/i }));
}

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const baseOrder: OrderItem = {
  id: 42,
  symbol: 'AAPL',
  side: 'buy',
  qty: 10,
  order_type: 'market',
  limit_price: null,
  stop_price: null,
  status: 'filled',
  alpaca_order_id: 'abc-123',
  filled_price: 185.5,
  filled_qty: 10,
  filled_at: '2026-05-13T12:00:00Z',
  signal_id: null,
  error_message: null,
  created_at: '2026-05-13T11:59:00Z',
  updated_at: '2026-05-13T12:00:00Z',
};

const baseMonitor: ExecutionAssetMonitor = {
  strategyId: 1,
  symbol: 'AAPL',
  assetName: 'Apple Inc.',
  assetType: 'stock',
  combinationMode: 'all',
  algoTimeframe: '5m',
  criteria: [
    { label: 'MC Prob+', value: 0.72, buyThreshold: 0.65, sellThreshold: 0.4, signal: 'BUY' },
    { label: 'AI Conviction', value: 0.85, buyThreshold: 0.7, sellThreshold: 0.3, signal: 'BUY' },
    { label: 'AI Sentiment', value: 0.4, buyThreshold: 0.2, sellThreshold: -0.1, signal: 'BUY' },
    { label: 'AI Macro', value: 0.3, buyThreshold: 0.1, sellThreshold: -0.2, signal: 'BUY' },
  ],
  overallSignal: 'BUY',
  // Standalone (non-combo) strategy signals — card resolves label from STRATEGIES constant
  algoSignals: [
    { strategy: 'rsi', label: 'RSI (Relative Strength Index)', signal: 'BUY' },
    { strategy: 'macd', label: 'MACD', signal: 'NEUTRAL' },
  ],
  comboSignals: [],
  latestPrice: 185.5,
  priceUpdatedAt: '2026-05-13T12:00:00Z',
  indicatorSnapshot: null,
  lastLivePollAt: null,
  orders: [baseOrder],
  ordersTotal: 1,
  ordersPage: 1,
  loading: false,
  error: null,
};

// Monitor fixture with a combo group (ma_crossover + rsi inside combo:majority)
const comboMonitor: ExecutionAssetMonitor = {
  ...baseMonitor,
  algoSignals: [
    { strategy: 'ma_crossover', label: 'MA Crossover', signal: 'BUY', comboGroup: 'combo:majority' },
    { strategy: 'rsi', label: 'RSI (Relative Strength Index)', signal: 'NEUTRAL', comboGroup: 'combo:majority' },
  ],
  comboSignals: [
    { comboName: 'combo:majority', combinationMode: 'majority', signal: 'BUY' },
  ],
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ExecutionAssetCard', () => {
  it('renders the symbol and asset name', () => {
    renderCard(baseMonitor);
    expect(screen.getByText('AAPL')).toBeTruthy();
    expect(screen.getByText('Apple Inc.')).toBeTruthy();
  });

  it('renders the timeframe badge', () => {
    renderCard(baseMonitor);
    expect(screen.getAllByText('5m').length).toBeGreaterThan(0);
  });

  it('keeps detail sections collapsed by default', () => {
    renderCard(baseMonitor);
    expect(screen.getByText('AAPL')).toBeTruthy();
    expect(screen.getByText('Running')).toBeTruthy();
    expect(screen.getByText('Combo: All')).toBeTruthy();
    expect(screen.getByText('Combined Signal')).toBeTruthy();
    expect(screen.getAllByText('$185.50').length).toBeGreaterThan(0);
    expect(screen.queryByText('MC Prob+')).toBeNull();
    expect(screen.queryByText('Transactions (1)')).toBeNull();
  });

  it('expands detail sections when header toggle is clicked', () => {
    renderCard(baseMonitor);
    expandCard();
    expect(screen.getByText('MC Prob+')).toBeTruthy();
    expect(screen.getByText('Transactions (1)')).toBeTruthy();
  });

  it('renders the combined signal', () => {
    renderCard(baseMonitor);
    expect(screen.getByText('Combined Signal')).toBeTruthy();
    const buyLabels = screen.getAllByText(/BUY/);
    expect(buyLabels.length).toBeGreaterThan(0);
  });

  it('renders all four criteria labels', () => {
    renderCard(baseMonitor);
    expandCard();
    expect(screen.getByText('MC Prob+')).toBeTruthy();
    expect(screen.getByText('AI Conviction')).toBeTruthy();
    expect(screen.getByText('AI Sentiment')).toBeTruthy();
    expect(screen.getByText('AI Macro')).toBeTruthy();
  });

  it('renders latest price', () => {
    renderCard(baseMonitor);
    expect(screen.getAllByText('$185.50').length).toBeGreaterThan(0);
  });

  it('renders standalone algo strategy signals with resolved labels', () => {
    renderCard(baseMonitor);
    expandCard();
    // Card resolves strategy key "rsi" → "RSI (Relative Strength Index)" via STRATEGIES constant
    expect(screen.getByText('RSI (Relative Strength Index)')).toBeTruthy();
    expect(screen.getByText('MACD')).toBeTruthy();
  });

  it('renders the transactions table with an order', () => {
    renderCard(baseMonitor);
    expandCard();
    expect(screen.getByText('Transactions (1)')).toBeTruthy();
    expect(screen.getAllByText('$185.50').length).toBeGreaterThan(0);
  });

  it('shows empty state when no orders', () => {
    const monitor = { ...baseMonitor, orders: [], ordersTotal: 0, ordersPage: 1 };
    renderCard(monitor);
    expandCard();
    expect(screen.getByText('Transactions (0)')).toBeTruthy();
    expect(screen.getByText(/No orders created by this ruleset yet/)).toBeTruthy();
  });

  it('shows empty algo panel message when no algos configured', () => {
    const monitor = { ...baseMonitor, algoSignals: [], comboSignals: [] };
    renderCard(monitor);
    expandCard();
    expect(screen.getByText(/No algo strategies configured/)).toBeTruthy();
  });

  it('shows Running status indicator', () => {
    renderCard(baseMonitor);
    expect(screen.getByText('Running')).toBeTruthy();
  });

  it('shows NEUTRAL combined signal correctly', () => {
    const monitor = { ...baseMonitor, overallSignal: 'NEUTRAL' as const };
    renderCard(monitor);
    expect(screen.getByText('◆ NEUTRAL')).toBeTruthy();
  });

  it('shows SELL combined signal correctly', () => {
    const monitor = { ...baseMonitor, overallSignal: 'SELL' as const };
    renderCard(monitor);
    expect(screen.getByText('▼ SELL')).toBeTruthy();
  });

  it('renders threshold hints for criteria', () => {
    renderCard(baseMonitor);
    expandCard();
    expect(screen.getByText('buy ≥ 0.65')).toBeTruthy();
  });

  it('renders combination mode badge', () => {
    renderCard(baseMonitor);
    expect(screen.getByText('Combo: All')).toBeTruthy();
  });

  it('renders indicator value when present on an algo signal', () => {
    const monitor = {
      ...baseMonitor,
      algoSignals: [
        {
          strategy: 'rsi',
          label: 'RSI (Relative Strength Index)',
          signal: 'NEUTRAL' as const,
          indicatorValue: 45.2,
          indicatorLabel: 'RSI',
          params: { period: 14, overbought: 70, oversold: 30 },
        },
      ],
    };
    renderCard(monitor);
    expandCard();
    expect(screen.getAllByText(/RSI: 45\.2/).length).toBeGreaterThan(0);
  });

  it('renders threshold hint when indicator params are present', () => {
    const monitor = {
      ...baseMonitor,
      algoSignals: [
        {
          strategy: 'rsi',
          label: 'RSI (Relative Strength Index)',
          signal: 'NEUTRAL' as const,
          indicatorValue: 45.2,
          indicatorLabel: 'RSI',
          params: { period: 14, overbought: 70, oversold: 30 },
        },
      ],
    };
    renderCard(monitor);
    expandCard();
    expect(screen.getByText('buy ≥ 30 / sell ≤ 70')).toBeTruthy();
  });

  it('does not render indicator hint when no indicator data is available', () => {
    const monitor = {
      ...baseMonitor,
      algoSignals: [
        { strategy: 'rsi', label: 'RSI', signal: 'NEUTRAL' as const },
      ],
    };
    const { queryByText } = renderCard(monitor);
    expandCard();
    expect(queryByText(/RSI:/)).toBeNull();
  });

  it('shows pagination controls when ordersTotal exceeds page size', () => {
    const monitor = { ...baseMonitor, ordersTotal: 25, ordersPage: 1 };
    renderCard(monitor);
    expandCard();
    expect(screen.getByText('Page 1 of 3')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Next' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Previous' })).toHaveProperty('disabled', true);
  });

  it('calls onOrdersPageChange when Next is clicked', () => {
    const onPageChange = vi.fn();
    const monitor = { ...baseMonitor, ordersTotal: 25, ordersPage: 1 };
    renderCard(monitor, onPageChange);
    expandCard();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });
});

// ---------------------------------------------------------------------------
// Combo group rendering
// ---------------------------------------------------------------------------

describe('ExecutionAssetCard – combo group', () => {
  it('renders the combo group header with mode label', () => {
    renderCard(comboMonitor);
    expandCard();
    expect(screen.getByText('Combo: majority')).toBeTruthy();
  });

  it('renders the combo aggregate signal badge in the header', () => {
    renderCard(comboMonitor);
    expandCard();
    // The combo header shows its own signal badge
    const buyBadges = screen.getAllByText('BUY');
    expect(buyBadges.length).toBeGreaterThan(0);
  });

  it('renders individual strategy rows inside the combo group', () => {
    renderCard(comboMonitor);
    expandCard();
    // MA Crossover label resolved from STRATEGIES constant
    expect(screen.getByText('MA Crossover')).toBeTruthy();
    // RSI resolved label
    expect(screen.getByText('RSI (Relative Strength Index)')).toBeTruthy();
  });

  it('shows NEUTRAL badge for rsi inside the combo group', () => {
    renderCard(comboMonitor);
    expandCard();
    expect(screen.getByText('NEUTRAL')).toBeTruthy();
  });
});
