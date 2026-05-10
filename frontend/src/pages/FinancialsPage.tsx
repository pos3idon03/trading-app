import { useEffect, useState } from 'react';
import { dataApi, financialsApi } from '../api/endpoints';
import type {
  AssetItem,
  CompanyProfile,
  FinancialStatement,
  FinancialStatementRow,
  FundamentalsOverview,
} from '../api/types';
import ErrorAlert from '../components/ErrorAlert';
import MetricCard from '../components/MetricCard';
import Spinner from '../components/Spinner';

// ── Formatting helpers ────────────────────────────────────────────────────────

function formatBig(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1e12) return `${(v / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  return v.toFixed(2);
}

function formatPct(v: number): string {
  return `${(v * 100).toFixed(2)}%`;
}

// ── Metrics config ─────────────────────────────────────────────────────────

type MetricDef = {
  key: string;
  label: string;
  fmt: (v: number) => string;
  pos?: (v: number) => boolean;
  neg?: (v: number) => boolean;
};

const METRICS: MetricDef[] = [
  { key: 'trailingEps',    label: 'EPS (TTM)',          fmt: (v) => `$${v.toFixed(2)}`,   pos: (v) => v > 0,   neg: (v) => v < 0 },
  { key: 'forwardEps',     label: 'EPS (Forward)',       fmt: (v) => `$${v.toFixed(2)}`,   pos: (v) => v > 0,   neg: (v) => v < 0 },
  { key: 'trailingPE',     label: 'P/E (TTM)',           fmt: (v) => v.toFixed(2) },
  { key: 'forwardPE',      label: 'P/E (Forward)',       fmt: (v) => v.toFixed(2) },
  { key: 'priceToBook',    label: 'P/B Ratio',           fmt: (v) => v.toFixed(2) },
  { key: 'dividendYield',  label: 'Dividend Yield',      fmt: formatPct,                   pos: (v) => v > 0 },
  { key: 'debtToEquity',   label: 'Debt / Equity',       fmt: (v) => v.toFixed(2),         neg: (v) => v > 200 },
  { key: 'returnOnEquity', label: 'Return on Equity',    fmt: formatPct,                   pos: (v) => v > 0.10 },
  { key: 'returnOnAssets', label: 'Return on Assets',    fmt: formatPct,                   pos: (v) => v > 0.05 },
  { key: 'profitMargins',  label: 'Profit Margin',       fmt: formatPct,                   pos: (v) => v > 0.10 },
  { key: 'revenueGrowth',  label: 'Revenue Growth',      fmt: formatPct,                   pos: (v) => v > 0, neg: (v) => v < 0 },
  { key: 'marketCap',      label: 'Market Cap',          fmt: formatBig },
  { key: 'freeCashflow',   label: 'Free Cash Flow',      fmt: formatBig,                   pos: (v) => v > 0, neg: (v) => v < 0 },
  { key: 'currentRatio',   label: 'Current Ratio',       fmt: (v) => v.toFixed(2),         pos: (v) => v > 1.5, neg: (v) => v < 1 },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function MetricsGrid({ metrics }: { metrics: Record<string, number> }) {
  return (
    <section>
      <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Key Metrics</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {METRICS.map(({ key, label, fmt, pos, neg }) => {
          const v = metrics[key];
          return (
            <MetricCard
              key={key}
              label={label}
              value={v !== undefined ? fmt(v) : null}
              positive={v !== undefined && pos ? pos(v) : undefined}
              negative={v !== undefined && neg ? neg(v) : undefined}
            />
          );
        })}
      </div>
    </section>
  );
}

function ProfileCard({ profile }: { profile: CompanyProfile }) {
  return (
    <section className="card space-y-3">
      <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
        {profile.sector   && <span><span className="text-slate-400">Sector: </span><span className="text-slate-100">{profile.sector}</span></span>}
        {profile.industry && <span><span className="text-slate-400">Industry: </span><span className="text-slate-100">{profile.industry}</span></span>}
        {profile.country  && <span><span className="text-slate-400">Country: </span><span className="text-slate-100">{profile.country}</span></span>}
        {profile.employees && (
          <span><span className="text-slate-400">Employees: </span><span className="text-slate-100">{profile.employees.toLocaleString()}</span></span>
        )}
        {profile.website && (
          <a href={profile.website} target="_blank" rel="noreferrer" className="text-brand-500 hover:underline">
            {profile.website}
          </a>
        )}
      </div>
      {profile.business_summary && (
        <p className="text-slate-300 text-sm leading-relaxed line-clamp-4">{profile.business_summary}</p>
      )}
    </section>
  );
}

function StatementTable({ statement }: { statement: FinancialStatement }) {
  if (!statement.rows.length) {
    return <p className="text-slate-500 text-sm py-4">No data available. Click "Fetch Financials" to ingest.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead>
          <tr className="border-b border-slate-700">
            <th className="py-2 pr-4 text-slate-400 font-medium w-56">Metric</th>
            {statement.periods.map((p) => (
              <th key={p} className="py-2 px-3 text-slate-400 font-medium text-right whitespace-nowrap">{p}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {statement.rows.map((row: FinancialStatementRow, i) => (
            <tr key={row.metric} className={`border-b border-slate-800 ${i % 2 === 0 ? '' : 'bg-surface-800/30'}`}>
              <td className="py-1.5 pr-4 text-slate-300 capitalize">{row.metric.replace(/_/g, ' ')}</td>
              {statement.periods.map((p) => {
                const v = row.values[p];
                return (
                  <td key={p} className="py-1.5 px-3 text-right text-slate-200 tabular-nums whitespace-nowrap">
                    {v !== undefined ? formatBig(v) : '—'}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Types & hooks ─────────────────────────────────────────────────────────────

type StatementTab = 'income' | 'balance' | 'cashflow';

interface FinancialsState {
  overview: FundamentalsOverview | null;
  profile: CompanyProfile | null;
  income: FinancialStatement | null;
  balance: FinancialStatement | null;
  cashflow: FinancialStatement | null;
}

function useFinancials(symbol: string) {
  const [data, setData] = useState<FinancialsState>({ overview: null, profile: null, income: null, balance: null, cashflow: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(sym: string) {
    setLoading(true);
    setError(null);
    const [ov, prof, inc, bal, cf] = await Promise.allSettled([
      financialsApi.getOverview(sym),
      financialsApi.getProfile(sym),
      financialsApi.getIncomeStatement(sym),
      financialsApi.getBalanceSheet(sym),
      financialsApi.getCashFlow(sym),
    ]);
    setData({
      overview:  ov.status   === 'fulfilled' ? ov.value   : null,
      profile:   prof.status === 'fulfilled' ? prof.value : null,
      income:    inc.status  === 'fulfilled' ? inc.value  : null,
      balance:   bal.status  === 'fulfilled' ? bal.value  : null,
      cashflow:  cf.status   === 'fulfilled' ? cf.value   : null,
    });
    setLoading(false);
  }

  return { data, loading, error, setError, load };
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function FinancialsPage() {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [symbol, setSymbol] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [activeTab, setActiveTab] = useState<StatementTab>('income');
  const { data, loading, error, setError, load } = useFinancials(symbol);

  useEffect(() => {
    dataApi.getAssets()
      .then((res) => {
        const active = res.assets.filter((a) => a.is_active);
        setAssets(active);
        if (active.length > 0) setSymbol(active[0].symbol);
      })
      .catch(() => setError('Failed to load available assets.'));
  }, []);

  useEffect(() => {
    if (symbol) load(symbol);
  }, [symbol]);

  async function handleIngest() {
    if (!symbol) return;
    setIngesting(true);
    setError(null);
    try {
      await financialsApi.ingest(symbol);
      await load(symbol);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? 'Ingestion failed. Check backend logs.');
    } finally {
      setIngesting(false);
    }
  }

  const hasData = !!(data.overview || data.profile);
  const activeStatement = data[activeTab];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-slate-100">Financials</h1>
        <div className="flex items-center gap-3">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
          >
            {assets.map((a) => (
              <option key={a.id} value={a.symbol}>{a.symbol} {a.name ? `— ${a.name}` : ''}</option>
            ))}
          </select>
          <button
            onClick={handleIngest}
            disabled={!symbol || ingesting}
            className="btn-primary whitespace-nowrap"
          >
            {ingesting ? 'Fetching…' : 'Fetch Financials'}
          </button>
        </div>
      </div>

      {error && <ErrorAlert message={error} />}
      {loading && <Spinner label="Loading financials…" />}

      {!loading && !hasData && symbol && (
        <div className="card text-center text-slate-400 py-10">
          No financial data for <strong className="text-slate-200">{symbol}</strong>.
          Click <strong className="text-slate-200">Fetch Financials</strong> to ingest.
        </div>
      )}

      {!loading && hasData && (
        <>
          {data.profile && (
            <section>
              <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
                Company Profile — {symbol}
              </h2>
              <ProfileCard profile={data.profile} />
            </section>
          )}

          {data.overview && <MetricsGrid metrics={data.overview.metrics} />}

          <section>
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Financial Statements</h2>
            <StatementsPanel
              activeTab={activeTab}
              onTabChange={setActiveTab}
              statement={activeStatement}
            />
          </section>
        </>
      )}
    </div>
  );
}

// ── Statements panel (tabs) ───────────────────────────────────────────────────

const TABS: { id: StatementTab; label: string }[] = [
  { id: 'income',   label: 'Income Statement' },
  { id: 'balance',  label: 'Balance Sheet' },
  { id: 'cashflow', label: 'Cash Flow' },
];

function StatementsPanel({
  activeTab,
  onTabChange,
  statement,
}: {
  activeTab: StatementTab;
  onTabChange: (t: StatementTab) => void;
  statement: FinancialStatement | null;
}) {
  return (
    <div className="card space-y-4">
      <div className="flex gap-1 border-b border-slate-700 pb-3">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => onTabChange(t.id)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === t.id
                ? 'bg-surface-700 text-brand-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-surface-800'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {statement ? (
        <StatementTable statement={statement} />
      ) : (
        <p className="text-slate-500 text-sm py-4">
          No statement data available. Click "Fetch Financials" to ingest.
        </p>
      )}
    </div>
  );
}
