import { NavLink } from 'react-router-dom';
import clsx from 'clsx';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'block px-3 py-2 rounded-lg text-sm font-medium transition-colors',
    isActive
      ? 'bg-surface-800 text-brand-500'
      : 'text-slate-400 hover:text-slate-100 hover:bg-surface-800/50',
  );

const subLinkClass = ({ isActive }: { isActive: boolean }) =>
  clsx(
    'block pl-6 pr-3 py-2 rounded-lg text-sm transition-colors',
    isActive
      ? 'text-brand-500 bg-surface-800/60'
      : 'text-slate-400 hover:text-slate-100 hover:bg-surface-800/40',
  );

export default function Sidebar() {
  return (
    <aside className="w-56 shrink-0 border-r border-slate-800 bg-surface-900 flex flex-col">
      <div className="h-14 flex items-center px-4 border-b border-slate-800">
        <span className="text-brand-500 font-bold text-lg">
          Tiingo<span className="text-slate-400"> App</span>
        </span>
      </div>

      <nav className="flex-1 p-3 space-y-6">
        <div>
          <NavLink to="/ingestion" className={linkClass}>
            Ingestion
          </NavLink>
        </div>

        <div>
          <p className="px-3 mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Dashboard
          </p>
          <div className="space-y-1">
            <NavLink to="/dashboard/stocks" className={subLinkClass}>
              Stocks
            </NavLink>
            <NavLink to="/dashboard/crypto" className={subLinkClass}>
              Crypto
            </NavLink>
            <NavLink to="/dashboard/macro" className={subLinkClass}>
              Macro
            </NavLink>
          </div>
        </div>
      </nav>
    </aside>
  );
}
