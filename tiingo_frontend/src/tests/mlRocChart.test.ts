import { describe, expect, it } from 'vitest';
import { buildRocChartData, RANDOM_ROC_AUC } from '../utils/mlRocChartData';

describe('buildRocChartData', () => {
  it('includes diagonal random baseline points', () => {
    const data = buildRocChartData([
      {
        class_label: '1',
        fpr: [0, 0.25, 0.5, 1],
        tpr: [0, 0.4, 0.7, 1],
        auc: 0.65,
      },
    ]);

    expect(data.length).toBeGreaterThan(0);
    expect(data[0].random).toBe(data[0].fpr);
    expect(data[data.length - 1].random).toBeCloseTo(1, 5);
    expect(RANDOM_ROC_AUC).toBe(0.5);
  });

  it('maps class tpr series alongside fpr', () => {
    const data = buildRocChartData([
      {
        class_label: '1',
        fpr: [0, 1],
        tpr: [0, 0.8],
        auc: 0.8,
      },
    ]);

    expect(data[1].fpr).toBe(1);
    expect(data[1].tpr_1).toBe(0.8);
    expect(data[1].random).toBe(1);
  });
});
