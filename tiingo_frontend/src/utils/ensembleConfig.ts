import type { CombineMode, EnsembleLeg, EnsembleParams, StrategyCatalogItem } from '../api/backtestTypes';

export const ENSEMBLE_STRATEGY_ID = 'strategy_ensemble';
export const MIN_ENSEMBLE_LEGS = 2;
export const MAX_ENSEMBLE_LEGS = 5;

export function combineModeLabel(mode: CombineMode): string {
  if (mode === 'unanimous') return 'Unanimous';
  if (mode === 'majority') return 'Majority';
  return 'Weighted';
}

export function isEnsembleParams(value: unknown): value is EnsembleParams {
  if (!value || typeof value !== 'object') return false;
  const record = value as Record<string, unknown>;
  return Array.isArray(record.legs) && typeof record.combine_mode === 'string';
}

export function parseEnsembleParams(raw: unknown): EnsembleParams {
  if (isEnsembleParams(raw)) {
    return {
      combine_mode: raw.combine_mode,
      threshold: Number(raw.threshold ?? 0.5),
      legs: raw.legs.map((leg) => normalizeLeg(leg)),
    };
  }

  const record = (raw ?? {}) as Record<string, unknown>;
  const legs = Array.isArray(record.legs)
    ? record.legs.map((leg) => normalizeLeg(leg))
    : defaultLegsFromCatalog([]);
  return {
    combine_mode: (record.combine_mode as CombineMode) ?? 'majority',
    threshold: Number(record.threshold ?? 0.5),
    legs: legs.length >= MIN_ENSEMBLE_LEGS ? legs : defaultLegsFromCatalog([]),
  };
}

function normalizeLeg(raw: unknown, defaultSignalTimeframe?: string): EnsembleLeg {
  const leg = (raw ?? {}) as Record<string, unknown>;
  const signalTimeframe = leg.signal_timeframe
    ? String(leg.signal_timeframe)
    : defaultSignalTimeframe;
  return {
    strategy_id: String(leg.strategy_id ?? 'sma_crossover'),
    params: (leg.params as Record<string, number>) ?? {},
    weight: Number(leg.weight ?? 1),
    ...(signalTimeframe ? { signal_timeframe: signalTimeframe } : {}),
  };
}

export function defaultLegsFromCatalog(catalog: StrategyCatalogItem[]): EnsembleLeg[] {
  const sma = catalog.find((item) => item.id === 'sma_crossover');
  const rsi = catalog.find((item) => item.id === 'rsi_reversion');
  return [
    createLeg('sma_crossover', sma?.params ?? { fast_period: 20, slow_period: 50 }),
    createLeg('rsi_reversion', rsi?.params ?? { period: 14, oversold: 30, overbought: 70 }),
  ];
}

export function createLeg(
  strategyId: string,
  params: Record<string, number>,
  signalTimeframe?: string,
): EnsembleLeg {
  return {
    strategy_id: strategyId,
    params: { ...params },
    weight: 1,
    ...(signalTimeframe ? { signal_timeframe: signalTimeframe } : {}),
  };
}

export function defaultEnsembleParams(catalog: StrategyCatalogItem[]): EnsembleParams {
  const ensemble = catalog.find((item) => item.id === ENSEMBLE_STRATEGY_ID);
  if (ensemble && isEnsembleParams(ensemble.params)) {
    return parseEnsembleParams(ensemble.params);
  }
  return {
    combine_mode: 'majority',
    threshold: 0.5,
    legs: defaultLegsFromCatalog(catalog),
  };
}

export function canAddLeg(legs: EnsembleLeg[]): boolean {
  return legs.length < MAX_ENSEMBLE_LEGS;
}

export function canRemoveLeg(legs: EnsembleLeg[]): boolean {
  return legs.length > MIN_ENSEMBLE_LEGS;
}

export function addLeg(
  value: EnsembleParams,
  catalog: StrategyCatalogItem[],
  decisionTimeframe?: string,
): EnsembleParams {
  if (!canAddLeg(value.legs)) return value;
  const eligible = catalog.filter((item) => item.ensemble_eligible);
  const fallback = eligible[0]?.id ?? 'sma_crossover';
  const strategy = eligible.find((item) => item.id === fallback) ?? eligible[0];
  return {
    ...value,
    legs: [
      ...value.legs,
      createLeg(
        strategy?.id ?? fallback,
        (strategy?.params as Record<string, number>) ?? {},
        decisionTimeframe,
      ),
    ],
  };
}

export function removeLeg(value: EnsembleParams, index: number): EnsembleParams {
  if (!canRemoveLeg(value.legs)) return value;
  return {
    ...value,
    legs: value.legs.filter((_, legIndex) => legIndex !== index),
  };
}

export function parseEnsembleLegs(params: Record<string, unknown>): EnsembleLeg[] {
  return parseEnsembleParams(params).legs;
}

export function ensembleResultsTitle(params: Record<string, unknown>): string {
  const ensemble = parseEnsembleParams(params);
  return `Strategy trend (${combineModeLabel(ensemble.combine_mode)})`;
}
