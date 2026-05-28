import type { MlModelCatalogItem, MlRunRequest, MlSavedModel } from '../api/mlBacktestTypes';
import type { DateRangeValue } from '../constants/timeframes';
import { formatMetricPercent, parseMlParams } from './mlBacktestConfig';

export interface TradingModelRow {
  id: string;
  model: MlSavedModel;
  symbol: string;
  name: string;
  algorithm: string;
  featureMode: string;
  timeframe: string;
  trainAccuracy: string;
  sampleCount: string;
  createdAt: string;
  createdAtSort: number;
}

export function resolveModelLabel(
  modelType: string,
  catalogById: Map<string, MlModelCatalogItem>,
): string {
  return catalogById.get(modelType)?.label ?? modelType;
}

export function formatCreatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function resolveSymbol(model: MlSavedModel): string {
  if (model.symbol) return model.symbol;
  const fromMetrics = model.train_metrics?.training_symbol;
  if (typeof fromMetrics === 'string' && fromMetrics) return fromMetrics;
  const firstToken = model.name.trim().split(/\s+/)[0];
  return firstToken || '—';
}

function resolveTimeframe(model: MlSavedModel): string {
  if (model.timeframe) return model.timeframe;
  const fromMetrics = model.train_metrics?.timeframe;
  return typeof fromMetrics === 'string' && fromMetrics ? fromMetrics : '—';
}

function resolveTrainAccuracy(model: MlSavedModel): string {
  const accuracy = model.train_metrics?.train_accuracy;
  return typeof accuracy === 'number'
    ? formatMetricPercent(accuracy)
    : formatMetricPercent(
        typeof model.train_metrics?.accuracy === 'number'
          ? (model.train_metrics.accuracy as number)
          : null,
      );
}

function resolveSampleCount(model: MlSavedModel): string {
  const count = model.train_metrics?.sample_count;
  return typeof count === 'number' ? String(count) : '—';
}

export function dateRangeFromTrainMetrics(
  metrics?: Record<string, unknown> | null,
): DateRangeValue | null {
  const start = metrics?.start;
  const end = metrics?.end;
  if (typeof start !== 'string' || typeof end !== 'string') {
    return null;
  }
  return { preset: 'MAX', start, end };
}

export function holdoutRangeFromTrainMetrics(
  metrics?: Record<string, unknown> | null,
): { start: string; end: string } | null {
  const holdoutStart = metrics?.holdout_start;
  const holdoutEnd = metrics?.holdout_end;
  if (typeof holdoutStart !== 'string' || typeof holdoutEnd !== 'string') {
    return null;
  }
  return { start: holdoutStart, end: holdoutEnd };
}

export function buildInferenceRunRequest(
  model: MlSavedModel,
  overrides?: { initialCash?: number; commissionBps?: number },
): MlRunRequest {
  const symbol = resolveSymbol(model);
  const timeframe = resolveTimeframe(model);
  const request: MlRunRequest = {
    symbol,
    model_type: model.model_type,
    params: {
      ...parseMlParams(model.hyperparams),
      feature_mode: model.feature_mode,
      model_id: model.id,
    },
    timeframe: timeframe !== '—' ? timeframe : '1d',
    initial_cash: overrides?.initialCash ?? 10_000,
    commission_bps: overrides?.commissionBps ?? 5,
  };

  const trainingRange = dateRangeFromTrainMetrics(model.train_metrics);
  if (trainingRange) {
    request.start = trainingRange.start;
    request.end = trainingRange.end;
    return request;
  }

  const start = model.train_metrics?.start;
  const end = model.train_metrics?.end;
  if (typeof start === 'string') request.start = start;
  if (typeof end === 'string') request.end = end;

  return request;
}

export function buildMlEditUrl(model: MlSavedModel): string {
  const symbol = encodeURIComponent(resolveSymbol(model));
  return `/backtesting/ml/${symbol}?editModelId=${encodeURIComponent(model.id)}`;
}

export function toTradingModelRow(
  model: MlSavedModel,
  catalogById: Map<string, MlModelCatalogItem>,
): TradingModelRow {
  const createdAtSort = new Date(model.created_at).getTime();
  return {
    id: model.id,
    model,
    symbol: resolveSymbol(model),
    name: model.name,
    algorithm: resolveModelLabel(model.model_type, catalogById),
    featureMode: model.feature_mode,
    timeframe: resolveTimeframe(model),
    trainAccuracy: resolveTrainAccuracy(model),
    sampleCount: resolveSampleCount(model),
    createdAt: formatCreatedAt(model.created_at),
    createdAtSort: Number.isNaN(createdAtSort) ? 0 : createdAtSort,
  };
}

export function buildCatalogById(models: MlModelCatalogItem[]): Map<string, MlModelCatalogItem> {
  return new Map(models.map((item) => [item.id, item]));
}

export function mapTradingModelRows(
  models: MlSavedModel[],
  catalogById: Map<string, MlModelCatalogItem>,
): TradingModelRow[] {
  return models.map((model) => toTradingModelRow(model, catalogById));
}
