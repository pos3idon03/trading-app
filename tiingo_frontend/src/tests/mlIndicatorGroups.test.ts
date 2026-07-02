import { describe, expect, it } from 'vitest';
import { parseMlParams } from '../utils/mlBacktestConfig';
import {
  DEFAULT_INDICATOR_GROUPS,
  parseIndicatorGroups,
  validateIndicatorGroups,
  formatIndicatorGroupsSummary,
} from '../utils/mlIndicatorGroups';

describe('mlIndicatorGroups', () => {
  it('parseIndicatorGroups defaults when empty', () => {
    expect(parseIndicatorGroups([])).toEqual(DEFAULT_INDICATOR_GROUPS);
    expect(parseIndicatorGroups(undefined)).toEqual(DEFAULT_INDICATOR_GROUPS);
  });

  it('parseIndicatorGroups keeps valid subset', () => {
    expect(parseIndicatorGroups(['momentum', 'volatility'])).toEqual([
      'momentum',
      'volatility',
    ]);
  });

  it('validateIndicatorGroups requires group when dynamic on', () => {
    expect(
      validateIndicatorGroups({
        dynamic_indicator_selection: true,
        indicator_groups: [],
      }),
    ).toMatch(/at least one/i);
    expect(
      validateIndicatorGroups({
        dynamic_indicator_selection: true,
        indicator_groups: ['momentum'],
      }),
    ).toBeNull();
  });

  it('parseMlParams includes indicator_groups', () => {
    const params = parseMlParams({
      indicator_groups: ['momentum', 'mean_reversion'],
      dynamic_indicator_selection: true,
    });
    expect(params.indicator_groups).toEqual(['momentum', 'mean_reversion']);
    expect(params.dynamic_indicator_selection).toBe(true);
  });

  it('formatIndicatorGroupsSummary', () => {
    expect(formatIndicatorGroupsSummary(false, [])).toBe('dynamic: off');
    expect(formatIndicatorGroupsSummary(true, ['momentum'])).toContain('momentum');
  });
});
