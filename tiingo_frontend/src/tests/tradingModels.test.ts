import { describe, expect, it } from 'vitest';
import type { MlModelCatalogItem, MlSavedModel } from '../api/mlBacktestTypes';
import {
  buildCatalogById,
  buildInferenceRunRequest,
  buildMlEditUrl,
  dateRangeFromTrainMetrics,
  formatCreatedAt,
  holdoutRangeFromTrainMetrics,
  mapTradingModelRows,
  resolveModelLabel,
  toTradingModelRow,
} from '../utils/tradingModels';

const catalog: MlModelCatalogItem[] = [
  {
    id: 'ml_logistic',
    label: 'Logistic Regression',
    description: '',
    params: {},
    constraints: {},
  },
  {
    id: 'ml_random_forest',
    label: 'Random Forest',
    description: '',
    params: {},
    constraints: {},
  },
];

describe('resolveModelLabel', () => {
  it('returns catalog label when available', () => {
    const catalogById = buildCatalogById(catalog);
    expect(resolveModelLabel('ml_logistic', catalogById)).toBe('Logistic Regression');
  });

  it('falls back to model type id', () => {
    const catalogById = buildCatalogById(catalog);
    expect(resolveModelLabel('ml_unknown', catalogById)).toBe('ml_unknown');
  });
});

describe('toTradingModelRow', () => {
  it('maps saved model fields including symbol and timeframe from API', () => {
    const model: MlSavedModel = {
      id: 'model-1',
      name: 'AAPL custom model',
      model_type: 'ml_random_forest',
      feature_mode: 'prices_only',
      feature_schema: {},
      hyperparams: {},
      symbol: 'AAPL',
      timeframe: '1d',
      train_metrics: {
        train_accuracy: 0.8123,
        sample_count: 500,
      },
      created_at: '2024-06-01T12:00:00.000Z',
    };

    const row = toTradingModelRow(model, buildCatalogById(catalog));

    expect(row).toMatchObject({
      id: 'model-1',
      symbol: 'AAPL',
      name: 'AAPL custom model',
      algorithm: 'Random Forest',
      featureMode: 'prices_only',
      timeframe: '1d',
      trainAccuracy: '81.2%',
      sampleCount: '500',
    });
    expect(row.createdAt).not.toBe('—');
  });

  it('falls back to train_metrics and model name when symbol is missing', () => {
    const model: MlSavedModel = {
      id: 'model-2',
      name: 'MSFT ml_logistic prices_only',
      model_type: 'ml_logistic',
      feature_mode: 'prices_only',
      feature_schema: {},
      hyperparams: {},
      train_metrics: {
        accuracy: 0.65,
        sample_count: 120,
      },
      created_at: '2024-01-01T00:00:00.000Z',
    };

    const row = toTradingModelRow(model, buildCatalogById(catalog));

    expect(row.symbol).toBe('MSFT');
    expect(row.algorithm).toBe('Logistic Regression');
    expect(row.trainAccuracy).toBe('65.0%');
    expect(row.timeframe).toBe('—');
  });
});

describe('mapTradingModelRows', () => {
  it('maps all models preserving order', () => {
    const models: MlSavedModel[] = [
      {
        id: 'a',
        name: 'First',
        model_type: 'ml_logistic',
        feature_mode: 'prices_only',
        feature_schema: {},
        hyperparams: {},
        symbol: 'AAPL',
        created_at: '2024-01-01T00:00:00.000Z',
      },
      {
        id: 'b',
        name: 'Second',
        model_type: 'ml_random_forest',
        feature_mode: 'prices_macro',
        feature_schema: {},
        hyperparams: {},
        symbol: 'MSFT',
        created_at: '2024-02-01T00:00:00.000Z',
      },
    ];

    const rows = mapTradingModelRows(models, buildCatalogById(catalog));
    expect(rows.map((row) => row.id)).toEqual(['a', 'b']);
  });
});

describe('formatCreatedAt', () => {
  it('returns dash for invalid dates', () => {
    expect(formatCreatedAt('not-a-date')).toBe('—');
  });
});

describe('dateRangeFromTrainMetrics', () => {
  it('maps stored ISO start and end to MAX preset range', () => {
    expect(
      dateRangeFromTrainMetrics({
        start: '2020-01-01T00:00:00Z',
        end: '2024-01-01T00:00:00Z',
      }),
    ).toEqual({
      preset: 'MAX',
      start: '2020-01-01T00:00:00Z',
      end: '2024-01-01T00:00:00Z',
    });
  });

  it('returns null when start or end is missing', () => {
    expect(dateRangeFromTrainMetrics({ start: '2020-01-01T00:00:00Z' })).toBeNull();
  });
});

describe('holdoutRangeFromTrainMetrics', () => {
  it('returns holdout start and end when present', () => {
    expect(
      holdoutRangeFromTrainMetrics({
        holdout_start: '2023-10-01',
        holdout_end: '2024-01-01',
      }),
    ).toEqual({ start: '2023-10-01', end: '2024-01-01' });
  });

  it('returns null when holdout metadata is missing', () => {
    expect(holdoutRangeFromTrainMetrics({ start: '2020-01-01' })).toBeNull();
  });
});

describe('buildInferenceRunRequest', () => {
  it('builds inference request with model_id and full training range', () => {
    const model: MlSavedModel = {
      id: 'model-abc',
      name: 'AAPL model',
      model_type: 'ml_logistic',
      feature_mode: 'prices_only',
      feature_schema: {},
      hyperparams: { label_horizon: 5, buy_threshold: 0.6 },
      symbol: 'AAPL',
      timeframe: '1d',
      train_metrics: {
        start: '2020-01-01T00:00:00Z',
        end: '2024-01-01T00:00:00Z',
        holdout_start: '2023-10-01T00:00:00Z',
        holdout_end: '2024-01-01T00:00:00Z',
      },
      created_at: '2024-06-01T12:00:00.000Z',
    };

    const request = buildInferenceRunRequest(model);

    expect(request).toMatchObject({
      symbol: 'AAPL',
      model_type: 'ml_logistic',
      timeframe: '1d',
      initial_cash: 10_000,
      commission_bps: 5,
      start: '2020-01-01T00:00:00Z',
      end: '2024-01-01T00:00:00Z',
      params: {
        feature_mode: 'prices_only',
        model_id: 'model-abc',
        label_horizon: 5,
        buy_threshold: 0.6,
      },
    });
  });
});

describe('buildMlEditUrl', () => {
  it('builds ML edit URL with symbol and model id', () => {
    const model: MlSavedModel = {
      id: 'model-xyz',
      name: 'MSFT model',
      model_type: 'ml_logistic',
      feature_mode: 'prices_only',
      feature_schema: {},
      hyperparams: {},
      symbol: 'MSFT',
      created_at: '2024-06-01T12:00:00.000Z',
    };

    expect(buildMlEditUrl(model)).toBe('/backtesting/ml/MSFT?editModelId=model-xyz');
  });
});
