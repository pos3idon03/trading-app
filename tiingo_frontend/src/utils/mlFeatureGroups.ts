export const ML_FEATURE_GROUP_LABELS: Record<string, string> = {
  price: 'Price / technical',
  volume: 'Volume',
  macro: 'Macro (FRED)',
  fundamental: 'Fundamentals',
  news: 'News sentiment',
  context: 'Multi-timeframe context',
  strategy: 'Algo strategy',
  cross_sectional: 'Cross-sectional factors',
  metadata: 'Instrument metadata',
  other: 'Other',
};

export function featureGroupLabel(groupKey: string): string {
  return ML_FEATURE_GROUP_LABELS[groupKey] ?? groupKey;
}

export function orderedFeatureGroupKeys(groups: Record<string, string[]>): string[] {
  const order = Object.keys(ML_FEATURE_GROUP_LABELS);
  return order.filter((key) => (groups[key]?.length ?? 0) > 0);
}
