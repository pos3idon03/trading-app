import { describe, expect, it } from 'vitest';
import type { StrategyCatalogItem } from '../api/backtestTypes';
import { eligibleStrategyFeatureOptions } from '../utils/mlStrategyFeatures';

const CATALOG: StrategyCatalogItem[] = [
  {
    id: 'buy_and_hold',
    label: 'Buy and Hold',
    description: '',
    params: {},
    constraints: {},
    ensemble_eligible: false,
  },
  {
    id: 'sma_crossover',
    label: 'SMA Crossover',
    description: '',
    params: {},
    constraints: {},
    ensemble_eligible: true,
  },
  {
    id: 'donchian_breakout',
    label: 'Donchian Breakout',
    description: '',
    params: {},
    constraints: {},
    ensemble_eligible: true,
  },
  {
    id: 'strategy_ensemble',
    label: 'Strategy Ensemble',
    description: '',
    params: {},
    constraints: {},
    ensemble_eligible: false,
  },
  {
    id: 'mfi_reversion',
    label: 'MFI Mean Reversion',
    description: '',
    params: {},
    constraints: {},
    ensemble_eligible: true,
  },
];

describe('eligibleStrategyFeatureOptions', () => {
  it('returns only ensemble-eligible strategies sorted by label', () => {
    const options = eligibleStrategyFeatureOptions(CATALOG);
    expect(options.map((item) => item.id)).toEqual([
      'donchian_breakout',
      'mfi_reversion',
      'sma_crossover',
    ]);
  });

  it('excludes buy_and_hold and strategy_ensemble', () => {
    const ids = eligibleStrategyFeatureOptions(CATALOG).map((item) => item.id);
    expect(ids).not.toContain('buy_and_hold');
    expect(ids).not.toContain('strategy_ensemble');
  });

  it('preserves catalog labels', () => {
    const options = eligibleStrategyFeatureOptions(CATALOG);
    expect(options.find((item) => item.id === 'donchian_breakout')?.label).toBe(
      'Donchian Breakout',
    );
  });
});
