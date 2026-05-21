import { useEffect, useRef, useState } from 'react';
import { ingestionApi } from '../api/endpoints';
import type { MacroSeries } from '../api/types';

const DEBOUNCE_MS = 200;

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function formatLabel(series: MacroSeries): string {
  return `${series.series_id} — ${series.title}`;
}

interface MacroSeriesSearchProps {
  selected: MacroSeries | null;
  onSelect: (series: MacroSeries | null) => void;
  placeholder?: string;
  className?: string;
}

export default function MacroSeriesSearch({
  selected,
  onSelect,
  placeholder = 'Search FRED series (e.g. GDP, CPI)',
  className = '',
}: MacroSeriesSearchProps) {
  const [catalog, setCatalog] = useState<MacroSeries[]>([]);
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounce(query, DEBOUNCE_MS);

  useEffect(() => {
    ingestionApi.listMacroSeries().then(setCatalog).catch(() => setCatalog([]));
  }, []);

  useEffect(() => {
    if (selected) {
      setQuery(formatLabel(selected));
    }
  }, [selected]);

  const filtered = catalog.filter((s) => {
    if (!debouncedQuery.trim() || selected) return true;
    const q = debouncedQuery.toLowerCase();
    return (
      s.series_id.toLowerCase().includes(q) ||
      s.title.toLowerCase().includes(q) ||
      s.category.toLowerCase().includes(q)
    );
  });

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const pickSeries = (series: MacroSeries) => {
    onSelect(series);
    setQuery(formatLabel(series));
    setOpen(false);
    setActiveIndex(-1);
  };

  const clearSelection = () => {
    onSelect(null);
    setQuery('');
    setOpen(false);
    inputRef.current?.focus();
  };

  const handleChange = (value: string) => {
    if (selected) onSelect(null);
    setQuery(value);
    setOpen(true);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (selected) {
      if (e.key === 'Escape' || e.key === 'Backspace') clearSelection();
      return;
    }
    if (!open || filtered.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      pickSeries(filtered[activeIndex]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={`relative min-w-[280px] flex-1 ${className}`}>
      <input
        ref={inputRef}
        type="text"
        className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 pr-8"
        placeholder={placeholder}
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (!selected) setOpen(true);
        }}
        readOnly={!!selected}
        autoComplete="off"
      />
      {selected && (
        <button
          type="button"
          onClick={clearSelection}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-red-400 text-lg leading-none"
          aria-label="Clear selection"
        >
          ×
        </button>
      )}

      {open && !selected && filtered.length > 0 && (
        <ul className="absolute z-50 mt-1 w-full bg-surface-800 border border-slate-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          {filtered.slice(0, 50).map((series, idx) => (
            <li
              key={series.series_id}
              onMouseDown={(ev) => {
                ev.preventDefault();
                pickSeries(series);
              }}
              onMouseEnter={() => setActiveIndex(idx)}
              className={`px-3 py-2.5 cursor-pointer text-sm transition-colors ${
                idx === activeIndex
                  ? 'bg-brand-500/20 text-slate-100'
                  : 'text-slate-300 hover:bg-slate-700/50'
              }`}
            >
              <span className="font-mono font-semibold text-brand-400">{series.series_id}</span>
              <span className="mx-2 text-slate-500">·</span>
              <span className="truncate">{series.title}</span>
              <span className="ml-2 text-xs text-slate-500 capitalize">{series.category}</span>
            </li>
          ))}
        </ul>
      )}

      {open && !selected && debouncedQuery && filtered.length === 0 && (
        <div className="absolute z-50 mt-1 w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-500">
          No matching series.
        </div>
      )}
    </div>
  );
}
