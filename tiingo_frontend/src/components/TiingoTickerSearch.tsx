import { useEffect, useRef, useState } from 'react';
import { ingestionApi } from '../api/endpoints';
import type { TickerSearchResult } from '../api/types';

const MIN_QUERY_LENGTH = 2;
const DEBOUNCE_MS = 300;

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function formatLabel(result: TickerSearchResult): string {
  const parts = [result.symbol, result.name];
  if (result.exchange) parts.push(`(${result.exchange})`);
  return parts.join(' — ');
}

interface TiingoTickerSearchProps {
  selected: TickerSearchResult | null;
  onSelect: (result: TickerSearchResult | null) => void;
  excludeSymbols?: string[];
  assetTypeFilter?: string[];
  placeholder?: string;
  className?: string;
}

export default function TiingoTickerSearch({
  selected,
  onSelect,
  excludeSymbols = [],
  assetTypeFilter,
  placeholder = 'Search by name or symbol (e.g. Apple)',
  className = '',
}: TiingoTickerSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<TickerSearchResult[]>([]);
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
      setQuery(formatLabel(selected));
    }
  }, [selected]);

  useEffect(() => {
    if (selected) {
      setResults([]);
      setOpen(false);
      return;
    }
    if (debouncedQuery.length < MIN_QUERY_LENGTH) {
      setResults([]);
      setOpen(false);
      setSearchError(null);
      setHasSearched(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setSearchError(null);

    ingestionApi
      .searchInstruments(debouncedQuery)
      .then((res) => {
        if (cancelled) return;
        const filtered = res.results.filter((r) => {
          if (excludeSymbols.includes(r.symbol)) return false;
          if (assetTypeFilter?.length && !assetTypeFilter.includes(r.asset_type)) return false;
          return true;
        });
        setResults(filtered);
        setHasSearched(true);
        setOpen(true);
        setActiveIndex(-1);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setResults([]);
        setHasSearched(true);
        setOpen(true);
        const msg =
          err && typeof err === 'object' && 'response' in err
            ? `Search failed (${(err as { response?: { status?: number } }).response?.status ?? 'error'})`
            : 'Search failed. Check that tiingo_backend is running.';
        setSearchError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, excludeSymbols, assetTypeFilter, selected]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const pickResult = (result: TickerSearchResult) => {
    onSelect(result);
    setQuery(formatLabel(result));
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
    if (selected) {
      onSelect(null);
    }
    setQuery(value);
    setHasSearched(false);
    setSearchError(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (selected) {
      if (e.key === 'Escape' || e.key === 'Backspace') {
        clearSelection();
      }
      return;
    }

    if (!open || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
      return;
    }
    if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      pickResult(results[activeIndex]);
      return;
    }
    if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={`relative min-w-[240px] flex-1 ${className}`}>
      <input
        ref={inputRef}
        type="text"
        className="w-full bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 pr-8"
        placeholder={placeholder}
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (!selected && results.length > 0) setOpen(true);
        }}
        readOnly={!!selected}
        autoComplete="off"
        aria-autocomplete="list"
        aria-expanded={open}
        aria-haspopup="listbox"
      />
      {loading && (
        <span className="absolute right-2.5 top-1/2 -translate-y-1/2">
          <span className="block w-3.5 h-3.5 border border-brand-500 border-t-transparent rounded-full animate-spin" />
        </span>
      )}
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

      {open && !selected && results.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-50 mt-1 w-full bg-surface-800 border border-slate-700 rounded-lg shadow-lg overflow-hidden max-h-64 overflow-y-auto"
        >
          {results.map((result, idx) => (
            <li
              key={`${result.symbol}-${result.exchange ?? ''}`}
              role="option"
              aria-selected={idx === activeIndex}
              onMouseDown={(ev) => {
                ev.preventDefault();
                pickResult(result);
              }}
              onMouseEnter={() => setActiveIndex(idx)}
              className={`flex items-center gap-3 px-3 py-2.5 cursor-pointer text-sm transition-colors ${
                idx === activeIndex
                  ? 'bg-brand-500/20 text-slate-100'
                  : 'text-slate-300 hover:bg-slate-700/50'
              }`}
            >
              <span className="font-mono font-semibold text-brand-400 w-16 shrink-0">
                {result.symbol}
              </span>
              <span className="truncate flex-1">{result.name}</span>
              <span className="text-xs text-slate-500 shrink-0 capitalize">{result.asset_type}</span>
              {result.exchange && (
                <span className="text-xs text-slate-500 shrink-0">{result.exchange}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {open && !selected && !loading && hasSearched && results.length === 0 && (
        <div className="absolute z-50 mt-1 w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-500">
          {searchError ?? 'No matches. Pick a symbol from Tiingo search results.'}
        </div>
      )}
    </div>
  );
}
