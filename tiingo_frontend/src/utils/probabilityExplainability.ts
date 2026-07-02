import type { ProbabilityExplainability } from '../api/executionTypes';

export const PROBABILITY_UP_LABEL = 'Probability (up)';

const PERCENT_FEATURES = new Set([
  'ret_1',
  'ret_5',
  'ret_20',
  'vol_20',
  'sma20_dist',
  'sma50_dist',
  'hl_range',
]);

export function formatProbabilityThresholds(
  buy: number | null | undefined,
  sell: number | null | undefined,
): string {
  if (buy == null || sell == null || Number.isNaN(buy) || Number.isNaN(sell)) return '';
  return `buy ≥ ${(buy * 100).toFixed(1)}% / sell ≤ ${(sell * 100).toFixed(1)}%`;
}

export function formatProbabilityDistance(
  probability: number | null | undefined,
  buy: number | null | undefined,
  sell: number | null | undefined,
): string {
  if (
    probability == null ||
    buy == null ||
    sell == null ||
    Number.isNaN(probability) ||
    Number.isNaN(buy) ||
    Number.isNaN(sell)
  ) {
    return '';
  }
  const pct = probability * 100;
  const buyPct = buy * 100;
  const sellPct = sell * 100;
  if (probability >= buy) {
    return `+${(pct - buyPct).toFixed(1)} pts above buy`;
  }
  if (probability <= sell) {
    return `${(sellPct - pct).toFixed(1)} pts below sell`;
  }
  return `In hold band (${sellPct.toFixed(0)}–${buyPct.toFixed(0)}%)`;
}

export function formatProbabilityContext(
  probability: number | null | undefined,
  buy: number | null | undefined,
  sell: number | null | undefined,
): string {
  const thresholds = formatProbabilityThresholds(buy, sell);
  const distance = formatProbabilityDistance(probability, buy, sell);
  return [thresholds, distance].filter(Boolean).join(' · ');
}

export function hasExplainability(
  data: ProbabilityExplainability | null | undefined,
): data is ProbabilityExplainability {
  return Boolean(
    data &&
      data.method !== 'unavailable' &&
      Array.isArray(data.top_contributors) &&
      data.top_contributors.length > 0,
  );
}

export function formatFeatureValue(feature: string, value: number): string {
  if (PERCENT_FEATURES.has(feature)) {
    const pct = value * 100;
    const sign = pct > 0 ? '+' : '';
    return `${sign}${pct.toFixed(1)}%`;
  }
  if (feature.startsWith('news_sent_avg_score') || feature.includes('sent')) {
    return value.toFixed(2);
  }
  return value.toFixed(4);
}

export function formatContribution(value: number): string {
  const points = value * 100;
  const sign = points > 0 ? '+' : '';
  return `${sign}${points.toFixed(1)} pts`;
}

export function maxContributionMagnitude(
  contributors: ProbabilityExplainability['top_contributors'],
): number {
  if (!contributors.length) return 0;
  return Math.max(...contributors.map((row) => Math.abs(row.contribution)));
}

export function resolveOrderedContributors(
  explainability: ProbabilityExplainability,
): ProbabilityExplainability['top_contributors'] {
  if (explainability.ordered_contributors?.length) {
    return explainability.ordered_contributors;
  }
  return explainability.top_contributors;
}

export function buildDecisionPlotSteps(
  explainability: ProbabilityExplainability,
): Array<{ feature: string; cumulative: number }> {
  const base = explainability.base_value ?? 0;
  const ordered = [...resolveOrderedContributors(explainability)].sort(
    (left, right) => Math.abs(right.contribution) - Math.abs(left.contribution),
  );
  let cumulative = base;
  const steps: Array<{ feature: string; cumulative: number }> = [
    { feature: 'base', cumulative: base },
  ];
  for (const row of ordered) {
    cumulative += row.contribution;
    steps.push({ feature: row.feature, cumulative });
  }
  return steps;
}
