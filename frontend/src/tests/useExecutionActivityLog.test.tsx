import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useExecutionActivityLog } from '../hooks/useExecutionActivityLog';
import type { ExecutionAssetMonitor } from '../api/types';

vi.mock('../api/endpoints', () => ({
  liveApi: {
    getStatus: vi.fn().mockResolvedValue({
      connected: true,
      subscribed_symbols: ['AAPL'],
      last_tick_at: null,
      error: null,
      reconnect_count: 0,
    }),
  },
}));

const monitorV1: ExecutionAssetMonitor = {
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
  combinedVoteCount: 0,
  algoSignals: [],
  comboSignals: [],
  latestPrice: 100,
  priceUpdatedAt: '2026-05-16T12:00:00Z',
  indicatorSnapshot: null,
  lastLivePollAt: null,
  orders: [],
  ordersTotal: 0,
  ordersPage: 1,
  loading: false,
  error: null,
};

describe('useExecutionActivityLog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not emit lines on initial monitor baseline', async () => {
    const { result, rerender } = renderHook(
      ({ monitors }) => useExecutionActivityLog(monitors),
      { initialProps: { monitors: [] as ExecutionAssetMonitor[] } },
    );

    rerender({ monitors: [monitorV1] });
    await waitFor(() => {
      expect(result.current.lines).toHaveLength(0);
    });
  });

  it('appends lines when monitor snapshot changes', async () => {
    const { result, rerender } = renderHook(
      ({ monitors }) => useExecutionActivityLog(monitors),
      { initialProps: { monitors: [monitorV1] } },
    );

    await waitFor(() => {
      expect(result.current.lines).toHaveLength(0);
    });

    rerender({
      monitors: [{ ...monitorV1, latestPrice: 101, priceUpdatedAt: '2026-05-16T12:01:00Z' }],
    });

    await waitFor(() => {
      expect(result.current.lines.length).toBeGreaterThan(0);
      expect(result.current.lines[0].text).toContain('stock price');
    });
  });

  it('clear resets accumulated lines', async () => {
    const { result, rerender } = renderHook(
      ({ monitors }) => useExecutionActivityLog(monitors),
      { initialProps: { monitors: [monitorV1] } },
    );

    rerender({
      monitors: [{ ...monitorV1, latestPrice: 101 }],
    });

    await waitFor(() => {
      expect(result.current.lines.length).toBeGreaterThan(0);
    });

    result.current.clear();
    await waitFor(() => {
      expect(result.current.lines).toHaveLength(0);
    });
  });
});
