import { NavLink, Outlet } from 'react-router-dom';
import clsx from 'clsx';

const TABS = [
  { path: '.', label: 'Overview', end: true },
  { path: 'watchlist', label: 'Watchlist', end: false },
  { path: 'market', label: 'Market Data', end: false },
  { path: 'stream', label: 'Live Stream', end: false },
  { path: 'news', label: 'News', end: false },
  { path: 'fundamentals', label: 'Fundamentals', end: false },
  { path: 'fred', label: 'FRED Macro', end: false },
] as const;

export default function IngestionLayout() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Tiingo Ingestion</h1>
        <p className="text-slate-400 text-sm mt-1">
          Watchlist-driven market data, news, fundamentals, and FRED macro pipelines.
        </p>
      </div>

      <nav className="flex flex-wrap gap-1 border-b border-slate-800 pb-2">
        {TABS.map((t) => (
          <NavLink
            key={t.path}
            to={t.path}
            end={t.end}
            className={({ isActive }) =>
              clsx(
                'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-surface-800 text-brand-500'
                  : 'text-slate-400 hover:text-slate-100',
              )
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  );
}
