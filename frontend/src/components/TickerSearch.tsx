import { useEffect, useRef, useState } from 'react';
import { dataApi } from '../api/endpoints';
import type { TickerSearchResult } from '../api/types';

interface TickerSearchProps {
  selected: string[];
  onChange: (symbols: string[]) => void;
}

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

export default function TickerSearch({ selected, onChange }: TickerSearchProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<TickerSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debouncedQuery = useDebounce(query, DEBOUNCE_MS);

  useEffect(() => {
    if (debouncedQuery.length < MIN_QUERY_LENGTH) {
      setResults([]);
      setOpen(false);
      return;
    }

    let cancelled = false;
    setLoading(true);

    dataApi
      .searchTickers(debouncedQuery)
      .then((res) => {
        if (cancelled) return;
        const filtered = res.results.filter((r) => !selected.includes(r.symbol));
        setResults(filtered);
        setOpen(filtered.length > 0);
        setActiveIndex(-1);
      })
      .catch(() => {
        if (!cancelled) setResults([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, selected]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  function selectTicker(result: TickerSearchResult) {
    onChange([...selected, result.symbol]);
    setQuery('');
    setResults([]);
    setOpen(false);
    setActiveIndex(-1);
    inputRef.current?.focus();
  }

  function removeTicker(symbol: string) {
    onChange(selected.filter((s) => s !== symbol));
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || results.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, 0));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      selectTicker(results[activeIndex]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div ref={containerRef} className="relative">
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            className="w-full bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500 pr-8"
            placeholder="Search by name or symbol (e.g. Microsoft)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => {
              if (results.length > 0) setOpen(true);
            }}
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
        </div>

        {open && results.length > 0 && (
          <ul
            role="listbox"
            className="absolute z-50 mt-1 w-full bg-surface-800 border border-slate-700 rounded-lg shadow-lg overflow-hidden max-h-64 overflow-y-auto"
          >
            {results.map((result, idx) => (
              <li
                key={result.symbol}
                role="option"
                aria-selected={idx === activeIndex}
                onMouseDown={(e) => {
                  e.preventDefault();
                  selectTicker(result);
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
                <span className="truncate">{result.name}</span>
                {result.exchange && (
                  <span className="ml-auto text-xs text-slate-500 shrink-0">{result.exchange}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-1.5" role="list" aria-label="Selected symbols">
          {selected.map((symbol) => (
            <span
              key={symbol}
              role="listitem"
              className="inline-flex items-center gap-1 px-2 py-0.5 bg-brand-500/15 border border-brand-500/40 rounded text-xs font-mono text-brand-300"
            >
              {symbol}
              <button
                type="button"
                onClick={() => removeTicker(symbol)}
                className="ml-0.5 text-brand-400 hover:text-red-400 transition-colors leading-none"
                aria-label={`Remove ${symbol}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
