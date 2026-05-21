import { useEffect, useRef, useState } from 'react';
import { ingestionApi } from '../api/endpoints';
import type { DashboardSeriesRef } from '../api/types';
import {
  formatSeriesLabel,
  instrumentToRef,
  macroToRef,
} from '../utils/seriesData';

const DEBOUNCE_MS = 300;
const INSTRUMENT_TYPES = ['stock', 'etf', 'crypto'];

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

interface SearchResult {
  ref: DashboardSeriesRef;
  badge: string;
}

interface UnifiedSeriesSearchProps {
  selected: DashboardSeriesRef | null;
  onSelect: (ref: DashboardSeriesRef | null) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export default function UnifiedSeriesSearch({
  selected,
  onSelect,
  placeholder = 'Search macro, stock, ETF, or crypto',
  className = '',
  disabled = false,
}: UnifiedSeriesSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounce(query, DEBOUNCE_MS);

  useEffect(() => {
    if (selected) {
      setQuery(formatSeriesLabel(selected));
    }
  }, [selected]);

  useEffect(() => {
    if (selected || disabled) {
      setResults([]);
      setOpen(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setSearchError(null);

    const q = debouncedQuery.trim();

    const macroPromise = ingestionApi.listMacroSeries({
      ingestedOnly: true,
      query: q || undefined,
      limit: 25,
    });
    const instrumentPromise =
      q.length > 0
        ? ingestionApi.searchDbInstruments(q, INSTRUMENT_TYPES, 25)
        : Promise.resolve([]);

    Promise.all([macroPromise, instrumentPromise])
      .then(([macroItems, instruments]) => {
        if (cancelled) return;

        const merged: SearchResult[] = [
          ...macroItems.map((s) => ({
            ref: macroToRef(s),
            badge: 'FRED',
          })),
          ...instruments.map((i) => ({
            ref: instrumentToRef(i),
            badge: i.asset_type,
          })),
        ];

        setResults(merged);
        setHasSearched(true);
        setOpen(true);
        setActiveIndex(-1);
      })
      .catch(() => {
        if (cancelled) return;
        setResults([]);
        setHasSearched(true);
        setOpen(true);
        setSearchError('Search failed. Check that tiingo_backend is running.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, selected, disabled]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const pickResult = (item: SearchResult) => {
    onSelect(item.ref);
    setQuery(formatSeriesLabel(item.ref));
    setResults([]);
    setOpen(false);
    setActiveIndex(-1);
  };

  const clearSelection = () => {
    onSelect(null);
    setQuery('');
    setResults([]);
    setOpen(false);
    inputRef.current?.focus();
  };

  const handleChange = (value: string) => {
    if (selected) onSelect(null);
    setQuery(value);
    setHasSearched(false);
    setSearchError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (selected) {
      if (e.key === 'Escape' || e.key === 'Backspace') clearSelection();
      return;
    }
    if (!open || results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      pickResult(results[activeIndex]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={`relative min-w-[280px] flex-1 ${className}`}>
      <input
        ref={inputRef}
        type="text"
        disabled={disabled}
        className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 pr-8 disabled:opacity-50"
        placeholder={placeholder}
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (!selected && !disabled) setOpen(true);
        }}
        readOnly={!!selected}
        autoComplete="off"
      />
      {loading && (
        <span className="absolute right-2.5 top-1/2 -translate-y-1/2">
          <span className="block w-3.5 h-3.5 border border-brand-500 border-t-transparent rounded-full animate-spin" />
        </span>
      )}
      {selected && !disabled && (
        <button
          type="button"
          onClick={clearSelection}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-red-400 text-lg leading-none"
          aria-label="Clear selection"
        >
          ×
        </button>
      )}

      {open && !selected && results.length > 0 && (
        <ul className="absolute z-50 mt-1 w-full bg-surface-800 border border-slate-700 rounded-lg shadow-lg max-h-64 overflow-y-auto">
          {results.map((item, idx) => (
            <li
              key={`${item.ref.source}-${item.ref.id}`}
              onMouseDown={(ev) => {
                ev.preventDefault();
                pickResult(item);
              }}
              onMouseEnter={() => setActiveIndex(idx)}
              className={`px-3 py-2.5 cursor-pointer text-sm transition-colors ${
                idx === activeIndex
                  ? 'bg-brand-500/20 text-slate-100'
                  : 'text-slate-300 hover:bg-slate-700/50'
              }`}
            >
              <span className="font-mono font-semibold text-brand-400">{item.ref.id}</span>
              <span className="mx-2 text-slate-500">·</span>
              <span className="truncate">{item.ref.label}</span>
              <span className="ml-2 text-xs text-slate-500 uppercase">{item.badge}</span>
            </li>
          ))}
        </ul>
      )}

      {open && !selected && !loading && hasSearched && results.length === 0 && (
        <div className="absolute z-50 mt-1 w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-500">
          {searchError ??
            'No ingested series match. Backfill macro from FRED or add instruments via Watchlist.'}
        </div>
      )}
    </div>
  );
}
