import { describe, expect, it } from 'vitest';
import type { DeploymentOverview, ExecutionActivityEvent } from '../api/executionTypes';
import {
  formatOverviewPrice,
  formatOverviewProfit,
  mergeOverviewWithActivity,
  overviewMetricRows,
} from '../utils/tradingOverview';
import {
  formatProbabilityContext,
  PROBABILITY_UP_LABEL,
} from '../utils/probabilityExplainability';

const baseDeployment: DeploymentOverview = {
  id: 'dep-1',
  model_id: 'model-1',
  symbol: 'AAPL',
  timeframe: '5m',
  status: 'active',
  model_name: 'AAPL model',
  last_signal: 'hold',
  last_probability: 0.45,
  buy_threshold: 0.55,
  sell_threshold: 0.45,
  last_explainability: null,
  last_evaluated_bar_time: '2026-05-27T22:55:00Z',
  current_price: 190.25,
  price_updated_at: null,
  round_trip_count: 2,
  open_position_count: 0,
  order_count: 4,
  open_order_count: 0,
  strategy_profit: 12.5,
  strategy_profit_pct: 1.25,
  position_qty: 0,
  position_side: 'flat',
  update_status: 'current',
  expected_latest_bar_time: null,
  ohlcv_latest_bar_time: null,
  missed_slot_count: 0,
};

describe('tradingOverview utils', () => {
  it('formats overview price and profit', () => {
    expect(formatOverviewPrice(190.25)).toBe('$190.25');
    expect(formatOverviewProfit(12.5)).toBe('+$12.50');
    expect(formatOverviewProfit(-3)).toBe('-$3.00');
  });

  it('builds metric rows for a deployment card', () => {
    const rows = overviewMetricRows(baseDeployment);
    expect(rows).toHaveLength(9);
    expect(rows.find((row) => row.label === 'Signal')?.value).toBe('HOLD');
    expect(rows.find((row) => row.label === PROBABILITY_UP_LABEL)?.value).toBe('45.0%');
    expect(rows.find((row) => row.label === PROBABILITY_UP_LABEL)?.sublabel).toBe(
      formatProbabilityContext(0.45, 0.55, 0.45),
    );
    expect(rows.find((row) => row.label === 'Positions executed')?.value).toBe('2');
    const latestUpdate = rows.find((row) => row.label === 'Latest update');
    expect(latestUpdate?.value).not.toBe('—');
    expect(latestUpdate?.sublabel).toBeTruthy();
  });

  it('marks stale deployments in metric rows context', () => {
    const stale = { ...baseDeployment, update_status: 'stale' as const, missed_slot_count: 2 };
    const rows = overviewMetricRows(stale);
    expect(rows.find((row) => row.label === 'Latest update')?.value).toBeTruthy();
  });

  it('merges latest websocket activity into overview rows', () => {
    const event: ExecutionActivityEvent = {
      id: 'evt-1',
      deployment_id: 'dep-1',
      symbol: 'AAPL',
      model_id: 'model-1',
      model_name: 'AAPL model',
      model_type: 'ml_logistic',
      bar_time: '2026-05-28T10:00:00Z',
      signal: 'buy',
      probability: 0.66,
      buy_threshold: 0.52,
      sell_threshold: 0.4,
      position_side: 'flat',
      order_intent_side: 'buy',
      order_qty: 1,
      outcome: 'order_submitted',
      blocked_reason: null,
      order_id: 'order-1',
      warnings: [],
      explainability: {
        method: 'shap_tree',
        top_contributors: [{ feature: 'ret_5', value: 0.03, contribution: 0.08 }],
      },
      created_at: '2026-05-28T10:00:05Z',
    };
    const merged = mergeOverviewWithActivity([baseDeployment], [event]);
    expect(merged[0].last_signal).toBe('buy');
    expect(merged[0].last_probability).toBe(0.66);
    expect(merged[0].buy_threshold).toBe(0.52);
    expect(merged[0].sell_threshold).toBe(0.4);
    expect(merged[0].last_explainability?.method).toBe('shap_tree');
    expect(merged[0].last_evaluated_bar_time).toBe('2026-05-28T10:00:00Z');
  });
});
