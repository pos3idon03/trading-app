import { useMemo, useState } from 'react';
import type { MacroSeries } from '../../api/types';
import {
  filterMacroSeriesByCategory,
  MACRO_CATEGORIES,
  sortMacroSeriesForDisplay,
  type MacroCategoryFilter,
} from '../../utils/macroCatalog';

interface MacroSeriesCategoryPickerProps {
  series: MacroSeries[];
  selectedIds: string[];
  onToggle: (seriesId: string) => void;
  ingestedIds?: Set<string>;
}

function pillClass(active: boolean): string {
  return `text-xs px-2 py-1 rounded capitalize transition-colors ${
    active ? 'bg-brand-600/30 text-brand-200 border border-brand-600/50' : 'bg-surface-800 text-slate-400 border border-transparent hover:text-slate-200'
  }`;
}

export default function MacroSeriesCategoryPicker({
  series,
  selectedIds,
  onToggle,
  ingestedIds,
}: MacroSeriesCategoryPickerProps) {
  const [activeCategory, setActiveCategory] = useState<MacroCategoryFilter>('all');

  const sortedSeries = useMemo(() => sortMacroSeriesForDisplay(series), [series]);

  const visibleSeries = useMemo(
    () => filterMacroSeriesByCategory(sortedSeries, activeCategory),
    [sortedSeries, activeCategory],
  );

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  return (
    <div className="space-y-2">
      <div className="flex gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => setActiveCategory('all')}
          className={pillClass(activeCategory === 'all')}
        >
          All
        </button>
        {MACRO_CATEGORIES.map((category) => (
          <button
            key={category}
            type="button"
            onClick={() => setActiveCategory(category)}
            className={pillClass(activeCategory === category)}
          >
            {category}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-48 overflow-y-auto border border-slate-800 rounded-lg p-3">
        {visibleSeries.length === 0 ? (
          <p className="text-sm text-slate-500 col-span-full">No macro series in this category.</p>
        ) : (
          visibleSeries.map((item) => {
            const ingested = ingestedIds?.has(item.series_id) ?? true;
            return (
              <label
                key={item.series_id}
                className="flex items-start gap-2 text-sm text-slate-300 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedSet.has(item.series_id)}
                  onChange={() => onToggle(item.series_id)}
                  className="mt-1"
                />
                <span>
                  <span className="font-medium text-slate-200">{item.series_id}</span>
                  <span className="block text-xs text-slate-500">{item.title}</span>
                  {!ingested && (
                    <span className="block text-xs text-amber-200/70">Not ingested</span>
                  )}
                </span>
              </label>
            );
          })
        )}
      </div>
    </div>
  );
}
