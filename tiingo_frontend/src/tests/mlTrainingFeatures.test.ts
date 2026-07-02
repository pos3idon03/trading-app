import { describe, expect, it } from 'vitest';
import { featureGroupLabel, orderedFeatureGroupKeys } from '../utils/mlFeatureGroups';

describe('mlFeatureGroups', () => {
  it('orders non-empty groups', () => {
    const keys = orderedFeatureGroupKeys({
      strategy: ['strat_a'],
      price: ['ret_1'],
      volume: ['volume_rel_20'],
    });
    expect(keys.indexOf('price')).toBeLessThan(keys.indexOf('volume'));
    expect(keys).toContain('strategy');
  });

  it('labels volume group', () => {
    expect(featureGroupLabel('volume')).toBe('Volume');
  });
});
