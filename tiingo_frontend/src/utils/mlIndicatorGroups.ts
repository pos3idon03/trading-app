import type { MlParams } from '../api/mlBacktestTypes';

export type MlIndicatorGroupId = 'momentum' | 'mean_reversion' | 'volatility';

export const ML_INDICATOR_GROUP_IDS: MlIndicatorGroupId[] = [
  'momentum',
  'mean_reversion',
  'volatility',
];

export const ML_INDICATOR_GROUPS: {
  id: MlIndicatorGroupId;
  label: string;
  features: string[];
}[] = [
  {
    id: 'momentum',
    label: 'Momentum',
    features: ['ret_5', 'ret_20', 'ema20_dist', 'ema50_dist'],
  },
  {
    id: 'mean_reversion',
    label: 'Mean reversion',
    features: ['rsi_14', 'sma20_dist', 'sma50_dist'],
  },
  {
    id: 'volatility',
    label: 'Volatility',
    features: ['vol_20', 'atr_14', 'hl_range'],
  },
];

export const DEFAULT_INDICATOR_GROUPS: MlIndicatorGroupId[] = [...ML_INDICATOR_GROUP_IDS];

export function parseIndicatorGroups(raw: unknown): MlIndicatorGroupId[] {
  if (!Array.isArray(raw) || raw.length === 0) {
    return [...DEFAULT_INDICATOR_GROUPS];
  }
  const parsed = raw
    .map(String)
    .filter((id): id is MlIndicatorGroupId =>
      ML_INDICATOR_GROUP_IDS.includes(id as MlIndicatorGroupId),
    );
  return parsed.length > 0 ? parsed : [...DEFAULT_INDICATOR_GROUPS];
}

export function validateIndicatorGroups(params: Pick<
  MlParams,
  'dynamic_indicator_selection' | 'indicator_groups'
>): string | null {
  if (!params.dynamic_indicator_selection) {
    return null;
  }
  const groups = params.indicator_groups ?? DEFAULT_INDICATOR_GROUPS;
  if (groups.length === 0) {
    return 'Select at least one dynamic indicator group when dynamic selection is enabled.';
  }
  return null;
}

export function formatIndicatorGroupsSummary(
  dynamic: boolean,
  groups: string[] | undefined,
): string {
  if (!dynamic) {
    return 'dynamic: off';
  }
  const ids = groups?.length ? groups : DEFAULT_INDICATOR_GROUPS;
  return `dynamic: ${ids.map((g) => g.replace('_', ' ')).join(', ')}`;
}
