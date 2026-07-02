import { describe, expect, it } from 'vitest';
import { buildDecisionPlotSteps, resolveOrderedContributors } from '../utils/probabilityExplainability';

describe('probability decision plot', () => {
  it('builds cumulative steps from base and contributors', () => {
    const steps = buildDecisionPlotSteps({
      method: 'shap_tree',
      base_value: 0.1,
      predicted_value: 0.25,
      top_contributors: [
        { feature: 'ret_1', value: 0.02, contribution: 0.05 },
        { feature: 'vol_20', value: 0.1, contribution: -0.02 },
      ],
      ordered_contributors: [
        { feature: 'ret_1', value: 0.02, contribution: 0.05 },
        { feature: 'vol_20', value: 0.1, contribution: -0.02 },
      ],
    });
    expect(steps[0]).toEqual({ feature: 'base', cumulative: 0.1 });
    expect(steps[steps.length - 1].cumulative).toBeCloseTo(0.13, 5);
  });

  it('falls back to top contributors when ordered list is empty', () => {
    const rows = resolveOrderedContributors({
      method: 'shap_linear',
      top_contributors: [{ feature: 'ret_1', value: 1, contribution: 0.1 }],
    });
    expect(rows).toHaveLength(1);
  });
});
