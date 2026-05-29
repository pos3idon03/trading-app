import type { MacroSeries } from '../api/types';

export const MACRO_CATEGORIES = [
  'growth',
  'labor',
  'inflation',
  'consumer',
  'rates',
  'housing',
  'energy',
  'goods',
] as const;

export type MacroCategory = (typeof MACRO_CATEGORIES)[number];
export type MacroCategoryFilter = 'all' | MacroCategory;

const CATEGORY_ORDER = new Map<string, number>(
  MACRO_CATEGORIES.map((category, index) => [category, index]),
);

export function sortMacroSeriesForDisplay(series: MacroSeries[]): MacroSeries[] {
  return [...series].sort((a, b) => {
    const categoryDiff =
      (CATEGORY_ORDER.get(a.category) ?? MACRO_CATEGORIES.length) -
      (CATEGORY_ORDER.get(b.category) ?? MACRO_CATEGORIES.length);
    if (categoryDiff !== 0) return categoryDiff;
    return a.series_id.localeCompare(b.series_id);
  });
}

export function filterMacroSeriesByCategory(
  series: MacroSeries[],
  category: MacroCategoryFilter,
): MacroSeries[] {
  if (category === 'all') return series;
  return series.filter((item) => item.category === category);
}
