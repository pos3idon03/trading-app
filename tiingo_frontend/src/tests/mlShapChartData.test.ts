import { describe, expect, it } from 'vitest';
import {
  buildShapChartData,
  discoverShapClassLabels,
  getMlClassDisplayName,
} from '../utils/mlShapChartData';

describe('getMlClassDisplayName', () => {
  it('maps binary classes to Down and Up', () => {
    expect(getMlClassDisplayName('0', 'binary')).toBe('Down');
    expect(getMlClassDisplayName('1', 'binary')).toBe('Up');
  });

  it('maps ternary classes to Ranging, Sell, and Buy', () => {
    expect(getMlClassDisplayName('0', 'ternary')).toBe('Ranging');
    expect(getMlClassDisplayName('1', 'ternary')).toBe('Sell');
    expect(getMlClassDisplayName('2', 'ternary')).toBe('Buy');
  });
});

describe('discoverShapClassLabels', () => {
  it('returns only classes present in items sorted numerically', () => {
    expect(
      discoverShapClassLabels([
        { class_label: '1', feature: 'ret_1', mean_abs_shap: 0.2 },
        { class_label: '0', feature: 'ret_1', mean_abs_shap: 0.1 },
        { class_label: '1', feature: 'rsi_14', mean_abs_shap: 0.3 },
      ]),
    ).toEqual(['0', '1']);
  });
});

describe('buildShapChartData', () => {
  it('totals and sorts using discovered classes only', () => {
    const data = buildShapChartData(
      [
        { class_label: '1', feature: 'ret_1', mean_abs_shap: 0.2 },
        { class_label: '1', feature: 'rsi_14', mean_abs_shap: 0.5 },
      ],
      ['1'],
      12,
    );

    expect(data).toHaveLength(2);
    expect(data[0].feature).toBe('rsi_14');
    expect(data[0].total).toBe(0.5);
    expect(data[1].feature).toBe('ret_1');
    expect(data[1].total).toBe(0.2);
  });
});
