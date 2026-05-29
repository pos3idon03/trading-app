import { describe, expect, it } from 'vitest';
import type { MacroSeries } from '../api/types';
import {
  filterMacroSeriesByCategory,
  MACRO_CATEGORIES,
  sortMacroSeriesForDisplay,
} from '../utils/macroCatalog';

function series(
  seriesId: string,
  category: string,
  title = seriesId,
): MacroSeries {
  return {
    series_id: seriesId,
    title,
    category,
    is_enabled: false,
  };
}

const SAMPLE_CATALOG: MacroSeries[] = [
  series('DFF', 'rates'),
  series('WALCL', 'rates'),
  series('CPIAUCSL', 'inflation'),
  series('GDPC1', 'growth'),
  series('UNRATE', 'labor'),
  series('HOUST', 'housing'),
  series('DCOILWTICO', 'energy'),
  series('PPIACO', 'goods'),
];

describe('macroCatalog', () => {
  it('exposes eight macro categories in display order', () => {
    expect(MACRO_CATEGORIES).toEqual([
      'growth',
      'labor',
      'inflation',
      'consumer',
      'rates',
      'housing',
      'energy',
      'goods',
    ]);
  });

  it('filterMacroSeriesByCategory returns all series for all tab', () => {
    expect(filterMacroSeriesByCategory(SAMPLE_CATALOG, 'all')).toHaveLength(
      SAMPLE_CATALOG.length,
    );
  });

  it('filterMacroSeriesByCategory returns only matching category', () => {
    const rates = filterMacroSeriesByCategory(SAMPLE_CATALOG, 'rates');
    expect(rates.map((item) => item.series_id).sort()).toEqual(['DFF', 'WALCL']);
  });

  it('sortMacroSeriesForDisplay orders by category then series_id', () => {
    const shuffled = [
      series('WALCL', 'rates'),
      series('GDPC1', 'growth'),
      series('DFF', 'rates'),
      series('CPIAUCSL', 'inflation'),
    ];
    const sorted = sortMacroSeriesForDisplay(shuffled);
    expect(sorted.map((item) => item.series_id)).toEqual([
      'GDPC1',
      'CPIAUCSL',
      'DFF',
      'WALCL',
    ]);
  });

  it('category filter does not depend on selected ids', () => {
    const selectedIds = new Set(['WALCL']);
    const visible = filterMacroSeriesByCategory(SAMPLE_CATALOG, 'rates');
    const uncheckedStillVisible = visible.filter((item) => !selectedIds.has(item.series_id));
    expect(uncheckedStillVisible.map((item) => item.series_id)).toContain('DFF');
    expect(visible).toHaveLength(2);
  });
});
