import { useParams, useSearchParams } from 'react-router-dom';
import clsx from 'clsx';
import MacroCompareTab from './MacroCompareTab';
import MacroRegressionTab from './MacroRegressionTab';
import MacroStandaloneTab from './MacroStandaloneTab';

const TABS = [
  { id: 'standalone', label: 'Standalone' },
  { id: 'compare', label: 'Compare' },
  { id: 'regression', label: 'Regression' },
] as const;

type TabId = (typeof TABS)[number]['id'];

function activeTab(param: string | null): TabId {
  if (param === 'standalone') return 'standalone';
  if (param === 'regression') return 'regression';
  return 'compare';
}

export default function MacroDashboardPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = activeTab(searchParams.get('tab'));

  const setTab = (next: TabId) => {
    const nextParams = new URLSearchParams(searchParams);
    if (next === 'compare') {
      nextParams.delete('tab');
      nextParams.delete('asset');
    } else {
      nextParams.set('tab', next);
      nextParams.delete('compare');
      nextParams.delete('compareKind');
      if (next === 'regression') {
        nextParams.delete('asset');
      }
    }
    setSearchParams(nextParams, { replace: true });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Macro Dashboard</h1>
        <p className="text-slate-400 text-sm mt-1">
          Analyze macro series standalone with trend overlays, compare with market instruments, or
          run cross-series regression analysis.
        </p>
      </div>

      <nav className="flex flex-wrap gap-1 border-b border-slate-800 pb-2">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={clsx(
              'px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              tab === t.id
                ? 'bg-surface-800 text-brand-500'
                : 'text-slate-400 hover:text-slate-100',
            )}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {tab === 'standalone' && <MacroStandaloneTab />}
      {tab === 'compare' && <MacroCompareTab />}
      {tab === 'regression' && <MacroRegressionTab />}
    </div>
  );
}
