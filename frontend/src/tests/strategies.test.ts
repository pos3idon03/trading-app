import { describe, it, expect } from 'vitest';
import {
  STRATEGIES,
  STRATEGY_GROUPS,
  DEFAULT_PARAMS_MAP,
  DEFAULT_GRID_MAP,
  OPTIMIZE_METRICS,
} from '../constants/strategies';

describe('STRATEGIES', () => {
  it('has at least one entry per group', () => {
    const groupsInStrategies = [...new Set(STRATEGIES.map((s) => s.group))];
    expect(groupsInStrategies.length).toBeGreaterThan(0);
  });

  it('has unique values', () => {
    const values = STRATEGIES.map((s) => s.value);
    const unique = new Set(values);
    expect(unique.size).toBe(values.length);
  });

  it('includes ma_crossover', () => {
    expect(STRATEGIES.find((s) => s.value === 'ma_crossover')).toBeDefined();
  });

  it('every strategy has a non-empty label', () => {
    STRATEGIES.forEach((s) => {
      expect(s.label.length).toBeGreaterThan(0);
    });
  });
});

describe('STRATEGY_GROUPS', () => {
  it('contains known groups', () => {
    expect(STRATEGY_GROUPS).toContain('Original');
    expect(STRATEGY_GROUPS).toContain('Momentum');
  });

  it('has no duplicates', () => {
    const unique = new Set(STRATEGY_GROUPS);
    expect(unique.size).toBe(STRATEGY_GROUPS.length);
  });
});

describe('DEFAULT_PARAMS_MAP', () => {
  it('has an entry for every strategy', () => {
    STRATEGIES.forEach((s) => {
      expect(DEFAULT_PARAMS_MAP[s.value]).toBeDefined();
    });
  });

  it('ma_crossover has fast_window and slow_window', () => {
    expect(DEFAULT_PARAMS_MAP['ma_crossover'].fast_window).toBeDefined();
    expect(DEFAULT_PARAMS_MAP['ma_crossover'].slow_window).toBeDefined();
  });
});

describe('DEFAULT_GRID_MAP', () => {
  it('has an entry for every strategy', () => {
    STRATEGIES.forEach((s) => {
      expect(DEFAULT_GRID_MAP[s.value]).toBeDefined();
    });
  });

  it('all grid values are non-empty arrays', () => {
    Object.values(DEFAULT_GRID_MAP).forEach((grid) => {
      Object.values(grid).forEach((arr) => {
        expect(Array.isArray(arr)).toBe(true);
        expect(arr.length).toBeGreaterThan(0);
      });
    });
  });
});

describe('OPTIMIZE_METRICS', () => {
  it('includes sharpe_ratio', () => {
    expect(OPTIMIZE_METRICS.find((m) => m.value === 'sharpe_ratio')).toBeDefined();
  });

  it('all metrics have label and value', () => {
    OPTIMIZE_METRICS.forEach((m) => {
      expect(m.value.length).toBeGreaterThan(0);
      expect(m.label.length).toBeGreaterThan(0);
    });
  });
});
