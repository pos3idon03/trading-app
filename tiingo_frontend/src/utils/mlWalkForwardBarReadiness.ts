import {
  estimateWalkForwardFoldCount,
  FEATURE_WARMUP_BARS,
  minimumBarsRequired,
  type WalkForwardParams,
} from './mlBacktestConfig';
import type { WalkForwardBudget } from './mlUniverseBudget';

export type WalkForwardBarReadinessStatus =
  | 'loading'
  | 'unknown'
  | 'insufficient_bars'
  | 'ready';

export interface WalkForwardBarReadiness {
  status: WalkForwardBarReadinessStatus;
  availableBars: number | null;
  minimumRequired: number;
  shortfall: number | null;
  headroom: number | null;
  structuralFolds: number;
  walkForwardBudget: number | null;
  breakdown: {
    warmup: number;
    train: number;
    test: number;
    labelHorizon: number;
  };
  headline: string;
  detail: string | null;
  cryptoTip: string | null;
}

export type WalkForwardBarReadinessOptions = {
  loading?: boolean;
  budget?: WalkForwardBudget | null;
  assetType?: string;
  timeframe?: string;
  labelMode?: 'binary' | 'ternary' | 'meta_label';
  maxHorizonBars?: number;
};

export function cryptoBarReadinessTip(
  assetType?: string,
  timeframe?: string,
): string | null {
  if (assetType !== 'crypto') {
    return null;
  }
  if (timeframe === '1h') {
    return (
      'Crypto trains 24/7; hourly needs ~4,000+ bars for ~6 months train window. ' +
      'Prefer 1h over 1d for the crypto preset.'
    );
  }
  if (timeframe === '1d') {
    return 'The crypto preset is tuned for hourly bars; daily bars may need a longer range or smaller train window.';
  }
  return null;
}

function labelTailBars(
  params: WalkForwardParams,
  options?: WalkForwardBarReadinessOptions,
): number {
  if (options?.labelMode === 'meta_label') {
    return options.maxHorizonBars ?? 48;
  }
  return params.label_horizon;
}

function minimumParams(
  params: WalkForwardParams,
  options?: WalkForwardBarReadinessOptions,
) {
  return {
    ...params,
    label_mode: options?.labelMode,
    max_horizon_bars: options?.maxHorizonBars ?? 48,
  };
}

function appendDetail(base: string | null, extra: string | null): string | null {
  if (!extra) {
    return base;
  }
  if (!base) {
    return extra;
  }
  return `${base} ${extra}`;
}

export function assessWalkForwardBarReadiness(
  barCount: number | null,
  params: WalkForwardParams,
  options?: WalkForwardBarReadinessOptions,
): WalkForwardBarReadiness {
  const labelTail = labelTailBars(params, options);
  const minimumRequired = minimumBarsRequired(minimumParams(params, options));
  const breakdown = {
    warmup: FEATURE_WARMUP_BARS,
    train: params.train_bars,
    test: params.test_bars,
    labelHorizon: labelTail,
  };
  const cryptoTip = cryptoBarReadinessTip(options?.assetType, options?.timeframe);

  if (options?.loading) {
    return {
      status: 'loading',
      availableBars: null,
      minimumRequired,
      shortfall: null,
      headroom: null,
      structuralFolds: 0,
      walkForwardBudget: null,
      breakdown,
      headline: 'Loading available bars for this period…',
      detail: null,
      cryptoTip,
    };
  }

  if (barCount == null || barCount <= 0) {
    return {
      status: 'unknown',
      availableBars: null,
      minimumRequired,
      shortfall: null,
      headroom: null,
      structuralFolds: 0,
      walkForwardBudget: null,
      breakdown,
      headline: 'Select a symbol and date range to see available bars.',
      detail: appendDetail(
        `Data Prep needs at least ${minimumRequired} bars (warmup + train + test + label tail).`,
        cryptoTip,
      ),
      cryptoTip,
    };
  }

  const budget = options?.budget;
  const walkForwardBudget =
    budget?.walkForwardBudget ?? barCount - FEATURE_WARMUP_BARS - labelTail;
  const headroom = barCount - minimumRequired;
  const shortfall = headroom < 0 ? -headroom : null;
  const structuralFolds =
    budget?.structuralFolds ??
    estimateWalkForwardFoldCount(
      barCount,
      params.train_bars,
      params.test_bars,
      params.step_bars,
    );

  if (shortfall != null && shortfall > 0) {
    return {
      status: 'insufficient_bars',
      availableBars: barCount,
      minimumRequired,
      shortfall,
      headroom,
      structuralFolds,
      walkForwardBudget,
      breakdown,
      headline: `Not enough bars for Data Prep (${barCount.toLocaleString()} available, ${minimumRequired} required)`,
      detail: appendDetail(
        `Short by ${shortfall.toLocaleString()} bars. Lower train/test bars or extend the simulation period.`,
        cryptoTip,
      ),
      cryptoTip,
    };
  }

  return {
    status: 'ready',
    availableBars: barCount,
    minimumRequired,
    shortfall: null,
    headroom,
    structuralFolds,
    walkForwardBudget,
    breakdown,
    headline: `Ready for Data Prep (${barCount.toLocaleString()} bars, ~${structuralFolds} structural fold${structuralFolds === 1 ? '' : 's'})`,
    detail: appendDetail(
      `${headroom.toLocaleString()} bars of headroom after warmup, train, test, and label tail.`,
      cryptoTip,
    ),
    cryptoTip,
  };
}

export function formatWalkForwardMinimumBreakdown(
  breakdown: WalkForwardBarReadiness['breakdown'],
): string {
  const total =
    breakdown.warmup + breakdown.train + breakdown.test + breakdown.labelHorizon;
  return (
    `${breakdown.warmup} warmup + ${breakdown.train} train + ${breakdown.test} test + ` +
    `${breakdown.labelHorizon} label tail = ${total}`
  );
}
