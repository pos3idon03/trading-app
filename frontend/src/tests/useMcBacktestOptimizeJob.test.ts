import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useMcBacktestOptimizeJob } from '../hooks/useMcBacktestOptimizeJob';

const mockOptimizeBacktest = vi.fn();
const mockGetOptimizeBacktestJob = vi.fn();

vi.mock('../api/endpoints', () => ({
  simulationApi: {
    optimizeBacktest: (...args: unknown[]) => mockOptimizeBacktest(...args),
    getOptimizeBacktestJob: (...args: unknown[]) => mockGetOptimizeBacktestJob(...args),
  },
}));

const doneStatus = {
  job_id: 1,
  asset_id: 1,
  symbol: 'AAPL',
  status: 'done',
  optimize_metric: 'sharpe_ratio',
  n_splits: 5,
  progress_pct: 100,
  completed_steps: 10,
  total_steps: 10,
  best_params: { buy_threshold: 0.52 },
  best_metric: 1.2,
  duration_ms: 800,
};

describe('useMcBacktestOptimizeJob', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
    mockOptimizeBacktest.mockResolvedValue({ job_id: 1, status: 'pending' });
    mockGetOptimizeBacktestJob.mockResolvedValue(doneStatus);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts job and polls until done', async () => {
    const { result } = renderHook(() => useMcBacktestOptimizeJob());

    await act(async () => {
      await result.current.start({
        symbol: 'AAPL',
        start_date: '2024-01-01T00:00:00.000Z',
        end_date: '2024-06-01T00:00:00.000Z',
        model_type: 'merton',
        param_grid: { buy_threshold: [52] },
      });
    });

    expect(mockOptimizeBacktest).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(result.current.result).not.toBeNull());
    expect(result.current.loading).toBe(false);
    expect(result.current.result?.best_params).toEqual({ buy_threshold: 0.52 });
    expect(mockGetOptimizeBacktestJob).toHaveBeenCalledWith(1);
  });

  it('sets error when job fails', async () => {
    mockGetOptimizeBacktestJob.mockResolvedValue({
      ...doneStatus,
      status: 'error',
      error_message: 'No feasible combinations',
      best_params: undefined,
    });

    const { result } = renderHook(() => useMcBacktestOptimizeJob());

    await act(async () => {
      await result.current.start({
        symbol: 'AAPL',
        start_date: '2024-01-01T00:00:00.000Z',
        end_date: '2024-06-01T00:00:00.000Z',
        model_type: 'merton',
        param_grid: { buy_threshold: [52] },
      });
    });

    await waitFor(() => expect(result.current.error).toBe('No feasible combinations'));
    expect(result.current.loading).toBe(false);
  });
});
