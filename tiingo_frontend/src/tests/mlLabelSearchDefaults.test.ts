import { describe, expect, it } from 'vitest';
import { DEFAULT_LABEL_MODE_BY_MODEL } from '../utils/mlBacktestConfig';
import {
  buildDefaultLabelSearchMatrix,
  buildLabelSearchGate,
  defaultLabelModeForModel,
  enabledLabelSearchConfigs,
  isLabelSearchCoverageComplete,
} from '../utils/mlLabelSearchMatrix';
import type { MlModelCatalogItem } from '../api/mlBacktestTypes';

const CATALOG: MlModelCatalogItem[] = [
  { id: 'ml_logistic', label: 'Logistic Regression', description: '', params: {}, constraints: {} },
  { id: 'ml_lstm', label: 'Stacked LSTM', description: '', params: {}, constraints: {} },
  { id: 'ml_random_forest', label: 'Random Forest', description: '', params: {}, constraints: {} },
];

describe('DEFAULT_LABEL_MODE_BY_MODEL', () => {
  it('matches literature-aligned defaults', () => {
    expect(DEFAULT_LABEL_MODE_BY_MODEL.ml_logistic).toBe('binary');
    expect(DEFAULT_LABEL_MODE_BY_MODEL.ml_lstm).toBe('meta_label');
    expect(DEFAULT_LABEL_MODE_BY_MODEL.ml_random_forest).toBe('ternary');
  });

  it('defaultLabelModeForModel falls back to binary', () => {
    expect(defaultLabelModeForModel('ml_logistic')).toBe('binary');
    expect(defaultLabelModeForModel('unknown')).toBe('binary');
  });
});

describe('label search matrix helpers', () => {
  it('buildDefaultLabelSearchMatrix enables all models with defaults', () => {
    const matrix = buildDefaultLabelSearchMatrix(CATALOG);
    expect(matrix.ml_logistic).toEqual({ enabled: true, labelMode: 'binary' });
    expect(matrix.ml_lstm).toEqual({ enabled: true, labelMode: 'meta_label' });
    expect(enabledLabelSearchConfigs(matrix)).toHaveLength(3);
  });

  it('isLabelSearchCoverageComplete requires matching model and mode', () => {
    const matrix = buildDefaultLabelSearchMatrix(CATALOG);
    expect(
      isLabelSearchCoverageComplete(matrix, [
        {
          label_key: 'a',
          model_type: 'ml_logistic',
          label_mode: 'binary',
          label_horizon: 5,
          oos_window_count: 1,
          class_distribution: {},
        },
      ]),
    ).toBe(false);

    expect(
      isLabelSearchCoverageComplete(matrix, [
        {
          label_key: 'a',
          model_type: 'ml_logistic',
          label_mode: 'binary',
          label_horizon: 5,
          oos_window_count: 1,
          class_distribution: {},
        },
        {
          label_key: 'b',
          model_type: 'ml_lstm',
          label_mode: 'meta_label',
          label_horizon: 5,
          oos_window_count: 1,
          class_distribution: {},
        },
        {
          label_key: 'c',
          model_type: 'ml_random_forest',
          label_mode: 'ternary',
          label_horizon: 5,
          oos_window_count: 1,
          class_distribution: {},
        },
      ]),
    ).toBe(true);
  });

  it('buildLabelSearchGate reflects coverage state', () => {
    const matrix = buildDefaultLabelSearchMatrix([
      { id: 'ml_logistic', label: 'Logistic', description: '', params: {}, constraints: {} },
    ]);
    const gate = buildLabelSearchGate(matrix, []);
    expect(gate.enabledModelIds).toEqual(['ml_logistic']);
    expect(gate.coverageComplete).toBe(false);
  });
});
