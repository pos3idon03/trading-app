import { describe, it, expect } from 'vitest';
import {
  diffMonitors,
  isInitialOrderHydration,
  resolveBarSourceLabel,
  snapshotMonitors,
  type DiffContext,
} from '../utils/executionActivityLog';
import type { OrderItem } from '../api/types';
import type { ExecutionAssetMonitor } from '../api/types';

function baseMonitor(overrides: Partial<ExecutionAssetMonitor> = {}): ExecutionAssetMonitor {
  return {
    strategyId: 1,
    symbol: 'AAPL',
    assetName: 'Apple',
    assetType: 'stock',
    combinationMode: 'all',
    algoTimeframe: '1h',
    criteria: [
      {
        label: 'MC Prob+',
        value: 0.54,
        buyThreshold: 0.5,
        sellThreshold: 0.3,
        signal: 'BUY',
      },
    ],
    overallSignal: 'NEUTRAL',
    combinedVoteCount: 2,
    algoSignals: [
      {
        strategy: 'ma_crossover',
        label: 'MA Crossover',
        signal: 'NEUTRAL',
        indicatorValue: 10,
        indicatorLabel: 'spread',
      },
    ],
    comboSignals: [],
    latestPrice: 133.34,
    priceUpdatedAt: '2026-05-16T11:10:34Z',
    indicatorSnapshot: null,
    lastLivePollAt: null,
    orders: [],
    ordersTotal: 0,
    ordersPage: 1,
    loading: false,
    error: null,
    ...overrides,
  };
}

function makeCtx(symbols: string[] = ['AAPL']): DiffContext {
  let n = 0;
  const barSourceBySymbol = new Map(symbols.map((s) => [s, 'alpaca']));
  return {
    barSourceBySymbol,
    nowISO: '2026-05-16T12:00:00.000Z',
    nextLineId: () => {
      n += 1;
      return `line-${n}`;
    },
  };
}

describe('resolveBarSourceLabel', () => {
  it('returns alpaca when stream is connected and symbol subscribed', () => {
    expect(
      resolveBarSourceLabel('AAPL', {
        connected: true,
        subscribed_symbols: ['AAPL'],
        last_tick_at: null,
        error: null,
        reconnect_count: 0,
      }),
    ).toBe('alpaca');
  });

  it('returns DB bars when stream disconnected', () => {
    expect(
      resolveBarSourceLabel('AAPL', {
        connected: false,
        subscribed_symbols: ['AAPL'],
        last_tick_at: null,
        error: null,
        reconnect_count: 0,
      }),
    ).toBe('DB bars');
  });

  it('returns alpaca for BTC-USD when subscribed with app symbol', () => {
    expect(
      resolveBarSourceLabel('BTC-USD', {
        connected: true,
        crypto_connected: true,
        subscribed_symbols: ['BTC-USD'],
        last_tick_at: null,
        error: null,
        reconnect_count: 0,
      }),
    ).toBe('alpaca');
  });

  it('returns DB bars for crypto when crypto channel is down', () => {
    expect(
      resolveBarSourceLabel('BTC-USD', {
        connected: true,
        stock_connected: true,
        crypto_connected: false,
        subscribed_symbols: ['BTC-USD'],
        last_tick_at: null,
        error: null,
        reconnect_count: 0,
      }),
    ).toBe('DB bars');
  });
});

describe('diffMonitors', () => {
  it('emits no lines on first snapshot (baseline)', () => {
    const monitors = [baseMonitor()];
    const prev = snapshotMonitors([]);
    const lines = diffMonitors(prev, monitors, makeCtx());
    expect(lines).toHaveLength(0);
  });

  it('emits price line when price changes', () => {
    const prev = snapshotMonitors([baseMonitor()]);
    const next = [baseMonitor({ latestPrice: 134.0, priceUpdatedAt: '2026-05-16T11:11:00Z' })];
    const lines = diffMonitors(prev, next, makeCtx());
    expect(lines.some((l) => l.text.includes('stock price is 134.00'))).toBe(true);
    expect(lines.some((l) => l.text.includes('source: alpaca'))).toBe(true);
  });

  it('emits MC criterion delta with percent formatting', () => {
    const prev = snapshotMonitors([baseMonitor()]);
    const next = [
      baseMonitor({
        criteria: [
          {
            label: 'MC Prob+',
            value: 0.55,
            buyThreshold: 0.5,
            sellThreshold: 0.3,
            signal: 'BUY',
          },
        ],
      }),
    ];
    const lines = diffMonitors(prev, next, makeCtx());
    expect(lines.some((l) => l.text.includes('MC Prob+'))).toBe(true);
    expect(lines.some((l) => l.text.includes('54% -> 55%'))).toBe(true);
  });

  it('emits algo recalculation with signal', () => {
    const prev = snapshotMonitors([baseMonitor()]);
    const next = [
      baseMonitor({
        algoSignals: [
          {
            strategy: 'ma_crossover',
            label: 'MA Crossover',
            signal: 'BUY',
            indicatorValue: 10.2,
            indicatorLabel: 'spread',
          },
        ],
      }),
    ];
    const lines = diffMonitors(prev, next, makeCtx());
    expect(lines.some((l) => l.text.includes('MA Crossover'))).toBe(true);
    expect(lines.some((l) => l.text.includes('10 -> 10.2'))).toBe(true);
    expect(lines.some((l) => l.text.includes('Signal is BUY'))).toBe(true);
  });

  it('skips historical orders on first orders fetch (empty -> populated)', () => {
    const prev = snapshotMonitors([baseMonitor({ orders: [] })]);
    const next = [
      baseMonitor({
        orders: [
          {
            id: 25,
            symbol: 'AAPL',
            side: 'buy',
            qty: 5,
            order_type: 'market',
            limit_price: null,
            stop_price: null,
            status: 'filled',
            alpaca_order_id: null,
            filled_price: 300,
            filled_qty: 5,
            filled_at: '2026-05-16T08:00:00Z',
            signal_id: null,
            error_message: null,
            created_at: '2026-05-16T08:00:00Z',
            updated_at: '2026-05-16T08:00:00Z',
          },
        ],
      }),
    ];
    const lines = diffMonitors(prev, next, makeCtx());
    expect(lines.some((l) => l.text.includes('Order #25'))).toBe(false);
    expect(isInitialOrderHydration([], next[0].orders)).toBe(true);
  });

  it('logs genuinely new orders with created_at timestamp', () => {
    const existingOrder: OrderItem = {
      id: 1,
      symbol: 'AAPL',
      side: 'buy',
      qty: 1,
      order_type: 'market',
      limit_price: null,
      stop_price: null,
      status: 'filled',
      alpaca_order_id: null,
      filled_price: 100,
      filled_qty: 1,
      filled_at: '2026-05-16T08:00:00Z',
      signal_id: null,
      error_message: null,
      created_at: '2026-05-16T08:00:00Z',
      updated_at: '2026-05-16T08:00:00Z',
    };
    const prev = snapshotMonitors([baseMonitor({ orders: [existingOrder] })]);
    const newOrder: OrderItem = {
      ...existingOrder,
      id: 99,
      created_at: '2026-05-16T10:30:00Z',
      updated_at: '2026-05-16T10:30:00Z',
    };
    const next = [baseMonitor({ orders: [existingOrder, newOrder] })];
    const lines = diffMonitors(prev, next, makeCtx());
    const orderLine = lines.find((l) => l.text.includes('Order #99'));
    expect(orderLine).toBeDefined();
    expect(orderLine?.tsISO).toBe('2026-05-16T10:30:00Z');
    expect(orderLine?.text).toContain('submitted');
  });

  it('emits full evaluation block on each live poll when logPollEvaluations is on', () => {
    const prev = snapshotMonitors([
      baseMonitor({
        lastLivePollAt: '2026-05-16T12:00:00Z',
        latestPrice: 300.19,
        algoSignals: [
          {
            strategy: 'ma_crossover',
            label: 'MA Crossover',
            signal: 'NEUTRAL',
            indicatorValue: 10,
            indicatorLabel: 'spread',
          },
        ],
      }),
    ]);
    const next = [
      baseMonitor({
        lastLivePollAt: '2026-05-16T12:01:00Z',
        latestPrice: 300.19,
        algoSignals: [
          {
            strategy: 'ma_crossover',
            label: 'MA Crossover',
            signal: 'NEUTRAL',
            indicatorValue: 10,
            indicatorLabel: 'spread',
          },
        ],
      }),
    ];
    const lines = diffMonitors(prev, next, makeCtx(), { logPollEvaluations: true });
    expect(lines.some((l) => l.text.includes('Live evaluation'))).toBe(true);
    expect(lines.some((l) => l.text.includes('MA Crossover evaluated'))).toBe(true);
    expect(lines.some((l) => l.text.includes('Combined signal'))).toBe(true);
    expect(lines.some((l) => l.text.includes('Poll complete'))).toBe(false);
  });

  it('emits poll heartbeat when live poll ran but metrics unchanged', () => {
    const prev = snapshotMonitors([
      baseMonitor({
        lastLivePollAt: '2026-05-16T12:00:00Z',
        latestPrice: 300.19,
      }),
    ]);
    const next = [
      baseMonitor({
        lastLivePollAt: '2026-05-16T12:01:00Z',
        latestPrice: 300.19,
      }),
    ];
    const lines = diffMonitors(prev, next, makeCtx(), { logPollHeartbeat: true });
    expect(lines).toHaveLength(1);
    expect(lines[0].text).toContain('Poll complete');
    expect(lines[0].text).toContain('no metric changes');
    expect(lines[0].tsISO).toBe('2026-05-16T12:01:00Z');
  });

  it('emits overall signal change', () => {
    const prev = snapshotMonitors([baseMonitor({ overallSignal: 'NEUTRAL' })]);
    const next = [baseMonitor({ overallSignal: 'BUY' })];
    const lines = diffMonitors(prev, next, makeCtx());
    expect(lines.some((l) => l.text.includes('Overall signal'))).toBe(true);
    expect(lines.some((l) => l.text.includes('NEUTRAL -> BUY'))).toBe(true);
  });
});
