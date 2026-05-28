import { describe, expect, it } from 'vitest';
import type { FoundationModelCatalogItem } from '../api/foundationBacktestTypes';
import {
  mergeFoundationParams,
  scalarFoundationParams,
  clampParam,
} from '../utils/foundationBacktestConfig';

const catalogItem: FoundationModelCatalogItem = {
  id: 'foundation_timesfm_2_5',
  label: 'TimesFM',
  description: 'test',
  params: {
    context_length: 128,
    forecast_horizon: 5,
    buy_return_threshold: 0.01,
    sell_return_threshold: -0.01,
  },
  constraints: {
    context_length: { min: 32, max: 1024 },
  },
};

describe('foundationBacktestConfig', () => {
  it('merges catalog defaults with overrides', () => {
    const merged = mergeFoundationParams(catalogItem, { context_length: 64 });
    expect(merged.context_length).toBe(64);
    expect(merged.forecast_horizon).toBe(5);
  });

  it('extracts scalar params for API', () => {
    const scalars = scalarFoundationParams({
      context_length: 64,
      signal_mode: 'next_point',
    });
    expect(scalars.context_length).toBe(64);
    expect(scalars.signal_mode).toBeUndefined();
  });

  it('clamps values to constraints', () => {
    expect(clampParam('context_length', 10, catalogItem.constraints)).toBe(32);
    expect(clampParam('context_length', 2000, catalogItem.constraints)).toBe(1024);
  });
});
