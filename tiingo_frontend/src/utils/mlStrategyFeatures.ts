import type { StrategyCatalogItem } from '../api/backtestTypes';

export interface StrategyFeatureOption {
  id: string;
  label: string;
}

/** Used when /backtest/strategies is unavailable so meta-label UI stays usable. */
export const DEFAULT_META_LABEL_BASE_STRATEGIES: StrategyFeatureOption[] = [
  { id: 'crypto_trend_entry', label: 'Crypto Trend Entry' },
  { id: 'ts_momentum', label: 'Time-Series Momentum' },
  { id: 'sma_crossover', label: 'SMA Crossover' },
  { id: 'ema_crossover', label: 'EMA Crossover' },
  { id: 'donchian_breakout', label: 'Donchian Breakout' },
  { id: 'bollinger_breakout', label: 'Bollinger Breakout' },
];

export function defaultMetaLabelBaseStrategyId(assetType: string): string {
  return assetType === 'crypto' ? 'crypto_trend_entry' : 'ts_momentum';
}

export function eligibleStrategyFeatureOptions(
  catalog: StrategyCatalogItem[],
): StrategyFeatureOption[] {
  return catalog
    .filter((item) => item.ensemble_eligible)
    .map((item) => ({ id: item.id, label: item.label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

/** Base rules that may trigger meta-label entry events (includes crypto_trend_entry). */
export function metaLabelBaseStrategyOptions(
  catalog: StrategyCatalogItem[],
): StrategyFeatureOption[] {
  if (!catalog.length) {
    return [...DEFAULT_META_LABEL_BASE_STRATEGIES];
  }
  const byId = new Map<string, StrategyFeatureOption>();
  const crypto = catalog.find((item) => item.id === 'crypto_trend_entry');
  if (crypto) {
    byId.set(crypto.id, { id: crypto.id, label: crypto.label });
  }
  for (const item of eligibleStrategyFeatureOptions(catalog)) {
    byId.set(item.id, item);
  }
  const merged = [...byId.values()];
  if (!merged.length) {
    return [...DEFAULT_META_LABEL_BASE_STRATEGIES];
  }
  return merged.sort((a, b) => {
    if (a.id === 'crypto_trend_entry') {
      return -1;
    }
    if (b.id === 'crypto_trend_entry') {
      return 1;
    }
    return a.label.localeCompare(b.label);
  });
}
