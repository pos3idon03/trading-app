import { describe, expect, it } from 'vitest';

import {
  deploymentStatusClass,
  formatDeploymentStatus,
  formatSignal,
  mapDeploymentRows,
  toDeploymentRow,
} from '../utils/tradingDeployments';
import type { TradingDeployment } from '../api/executionTypes';

const SAMPLE_DEPLOYMENT: TradingDeployment = {
  id: 'dep-1',
  model_id: 'model-1',
  symbol: 'AAPL',
  timeframe: '1d',
  status: 'active',
  trading_mode: 'paper',
  allocation_pct: 50,
  hyperparams_snapshot: {},
  model_name: 'AAPL rf prices_only',
  model_type: 'ml_random_forest',
  feature_mode: 'prices_only',
  last_evaluated_bar_time: '2024-01-02T00:00:00Z',
  last_signal: 'buy',
  last_blocked_reason: null,
  last_probability: 0.61,
  last_outcome: 'order_submitted',
  last_error: null,
  activated_at: '2024-01-01T00:00:00Z',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
};

describe('tradingDeployments utils', () => {
  it('maps deployment rows', () => {
    const rows = mapDeploymentRows([SAMPLE_DEPLOYMENT]);
    expect(rows).toHaveLength(1);
    expect(rows[0].symbol).toBe('AAPL');
    expect(rows[0].modelName).toBe('AAPL rf prices_only');
    expect(rows[0].allocationPct).toBe('50%');
  });

  it('formats status and signal', () => {
    expect(formatDeploymentStatus('active')).toBe('Active');
    expect(formatSignal('buy')).toBe('BUY');
    expect(deploymentStatusClass('error')).toBe('text-red-400');
  });

  it('builds sortable last evaluated timestamp', () => {
    const row = toDeploymentRow(SAMPLE_DEPLOYMENT);
    expect(row.lastEvaluatedSort).toBeGreaterThan(0);
  });
});
