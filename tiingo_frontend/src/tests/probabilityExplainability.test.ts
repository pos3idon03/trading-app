import { describe, expect, it } from 'vitest';
import {
  formatContribution,
  formatFeatureValue,
  formatProbabilityContext,
  formatProbabilityDistance,
  formatProbabilityThresholds,
  hasExplainability,
} from '../utils/probabilityExplainability';

describe('probabilityExplainability utils', () => {
  it('formats thresholds and distance to buy', () => {
    expect(formatProbabilityThresholds(0.6, 0.4)).toBe('buy ≥ 60.0% / sell ≤ 40.0%');
    expect(formatProbabilityDistance(0.78, 0.6, 0.4)).toBe('+18.0 pts above buy');
  });

  it('formats hold band and sell distance', () => {
    expect(formatProbabilityDistance(0.5, 0.6, 0.4)).toBe('In hold band (40–60%)');
    expect(formatProbabilityDistance(0.074, 0.6, 0.4)).toBe('32.6 pts below sell');
  });

  it('builds combined probability context', () => {
    expect(formatProbabilityContext(0.78, 0.6, 0.4)).toContain('buy ≥ 60.0%');
    expect(formatProbabilityContext(0.78, 0.6, 0.4)).toContain('+18.0 pts above buy');
  });

  it('formats feature values and contributions', () => {
    expect(formatFeatureValue('ret_5', 0.031)).toBe('+3.1%');
    expect(formatFeatureValue('rsi_14', 68.2)).toBe('68.2000');
    expect(formatContribution(0.12)).toBe('+12.0 pts');
    expect(formatContribution(-0.04)).toBe('-4.0 pts');
  });

  it('detects usable explainability payloads', () => {
    expect(
      hasExplainability({
        method: 'shap_tree',
        top_contributors: [{ feature: 'ret_1', value: 0.01, contribution: 0.02 }],
      }),
    ).toBe(true);
    expect(hasExplainability({ method: 'unavailable', top_contributors: [] })).toBe(false);
  });
});
