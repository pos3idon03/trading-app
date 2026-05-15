import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ExecutionAssetCard from '../components/ExecutionAssetCard';
import type { ExecutionAssetMonitor, OrderItem } from '../api/types';

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
  orders: [baseOrder],
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
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getByText('AAPL')).toBeTruthy();
    expect(screen.getByText('Apple Inc.')).toBeTruthy();
  });

  it('renders the timeframe badge', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getAllByText('5m').length).toBeGreaterThan(0);
  });

  it('renders the combined signal', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getByText('Combined Signal')).toBeTruthy();
    const buyLabels = screen.getAllByText(/BUY/);
    expect(buyLabels.length).toBeGreaterThan(0);
  });

  it('renders all four criteria labels', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getByText('MC Prob+')).toBeTruthy();
    expect(screen.getByText('AI Conviction')).toBeTruthy();
    expect(screen.getByText('AI Sentiment')).toBeTruthy();
    expect(screen.getByText('AI Macro')).toBeTruthy();
  });

  it('renders latest price', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getAllByText('$185.50').length).toBeGreaterThan(0);
  });

  it('renders standalone algo strategy signals with resolved labels', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    // Card resolves strategy key "rsi" → "RSI (Relative Strength Index)" via STRATEGIES constant
    expect(screen.getByText('RSI (Relative Strength Index)')).toBeTruthy();
    expect(screen.getByText('MACD')).toBeTruthy();
  });

  it('renders the transactions table with an order', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getByText('Transactions (1)')).toBeTruthy();
    expect(screen.getAllByText('$185.50').length).toBeGreaterThan(0);
  });

  it('shows empty state when no orders', () => {
    const monitor = { ...baseMonitor, orders: [] };
    render(<ExecutionAssetCard monitor={monitor} />);
    expect(screen.getByText('Transactions (0)')).toBeTruthy();
    expect(screen.getByText(/No orders created by this ruleset yet/)).toBeTruthy();
  });

  it('shows empty algo panel message when no algos configured', () => {
    const monitor = { ...baseMonitor, algoSignals: [], comboSignals: [] };
    render(<ExecutionAssetCard monitor={monitor} />);
    expect(screen.getByText(/No algo strategies configured/)).toBeTruthy();
  });

  it('shows Running status indicator', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getByText('Running')).toBeTruthy();
  });

  it('shows NEUTRAL combined signal correctly', () => {
    const monitor = { ...baseMonitor, overallSignal: 'NEUTRAL' as const };
    render(<ExecutionAssetCard monitor={monitor} />);
    expect(screen.getByText('◆ NEUTRAL')).toBeTruthy();
  });

  it('shows SELL combined signal correctly', () => {
    const monitor = { ...baseMonitor, overallSignal: 'SELL' as const };
    render(<ExecutionAssetCard monitor={monitor} />);
    expect(screen.getByText('▼ SELL')).toBeTruthy();
  });

  it('renders threshold hints for criteria', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
    expect(screen.getByText('buy ≥ 0.65')).toBeTruthy();
  });

  it('renders combination mode badge', () => {
    render(<ExecutionAssetCard monitor={baseMonitor} />);
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
    render(<ExecutionAssetCard monitor={monitor} />);
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
    render(<ExecutionAssetCard monitor={monitor} />);
    expect(screen.getByText('buy ≥ 30 / sell ≤ 70')).toBeTruthy();
  });

  it('does not render indicator hint when no indicator data is available', () => {
    const monitor = {
      ...baseMonitor,
      algoSignals: [
        { strategy: 'rsi', label: 'RSI', signal: 'NEUTRAL' as const },
      ],
    };
    const { queryByText } = render(<ExecutionAssetCard monitor={monitor} />);
    expect(queryByText(/RSI:/)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Combo group rendering
// ---------------------------------------------------------------------------

describe('ExecutionAssetCard – combo group', () => {
  it('renders the combo group header with mode label', () => {
    render(<ExecutionAssetCard monitor={comboMonitor} />);
    expect(screen.getByText('Combo: majority')).toBeTruthy();
  });

  it('renders the combo aggregate signal badge in the header', () => {
    render(<ExecutionAssetCard monitor={comboMonitor} />);
    // The combo header shows its own signal badge
    const buyBadges = screen.getAllByText('BUY');
    expect(buyBadges.length).toBeGreaterThan(0);
  });

  it('renders individual strategy rows inside the combo group', () => {
    render(<ExecutionAssetCard monitor={comboMonitor} />);
    // MA Crossover label resolved from STRATEGIES constant
    expect(screen.getByText('MA Crossover')).toBeTruthy();
    // RSI resolved label
    expect(screen.getByText('RSI (Relative Strength Index)')).toBeTruthy();
  });

  it('shows NEUTRAL badge for rsi inside the combo group', () => {
    render(<ExecutionAssetCard monitor={comboMonitor} />);
    expect(screen.getByText('NEUTRAL')).toBeTruthy();
  });
});
