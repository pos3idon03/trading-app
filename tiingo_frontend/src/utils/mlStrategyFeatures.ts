import type { StrategyCatalogItem } from '../api/backtestTypes';

export interface StrategyFeatureOption {
  id: string;
  label: string;
}

export function eligibleStrategyFeatureOptions(
  catalog: StrategyCatalogItem[],
): StrategyFeatureOption[] {
  return catalog
    .filter((item) => item.ensemble_eligible)
    .map((item) => ({ id: item.id, label: item.label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}
