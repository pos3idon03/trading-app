import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';
import { marketDataApi } from '../../api/endpoints';
import type { AssetOverviewRow, MacroOverviewRow } from '../../api/types';
import MacroBriefPanel from '../../components/dashboard/MacroBriefPanel';
import MarketSentimentPanel from '../../components/dashboard/MarketSentimentPanel';
import DataTable, {
  formatMaBadge,
  formatPctCell,
  type DataTableColumn,
} from '../../components/DataTable';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import { formatPerformancePct } from '../../utils/stockPerformance';
import { maPositionSortValue } from '../../utils/dataTableSort';

const ASSET_TABS = [
  { id: 'stock', label: 'Stocks' },
  { id: 'etf', label: 'ETF' },
  { id: 'crypto', label: 'Crypto' },
] as const;

const MACRO_TABS = [
  { id: 'all', label: 'All' },
  { id: 'growth', label: 'Growth' },
  { id: 'labor', label: 'Labor' },
  { id: 'inflation', label: 'Inflation' },
  { id: 'consumer', label: 'Consumer' },
  { id: 'rates', label: 'Rates' },
  { id: 'housing', label: 'Housing' },
  { id: 'energy', label: 'Energy' },
  { id: 'goods', label: 'Goods' },
] as const;

const PRICE_PERIODS = ['1W', '1M', '3M', '6M', 'YTD', '1Y', '2Y', '5Y'] as const;

type AssetTabId = (typeof ASSET_TABS)[number]['id'];
type MacroTabId = (typeof MACRO_TABS)[number]['id'];

function TabBar<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: readonly { id: T; label: string }[];
  active: T;
  onChange: (id: T) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={clsx(
            'px-3 py-2 rounded-lg text-sm font-medium transition-colors capitalize',
            active === tab.id
              ? 'bg-surface-800 text-brand-500'
              : 'text-slate-400 hover:text-slate-100 hover:bg-surface-800/50',
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

function formatRatio(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toFixed(2);
}

function assetLink(assetType: AssetTabId, symbol: string): string {
  if (assetType === 'crypto') return `/dashboard/crypto/${symbol}`;
  return `/dashboard/stocks/${symbol}`;
}

function stockColumns(assetType: AssetTabId): DataTableColumn<AssetOverviewRow>[] {
  return [
    {
      key: 'symbol',
      label: 'Symbol',
      sortValue: (row) => row.symbol,
      render: (row) => (
        <Link to={assetLink(assetType, row.symbol)} className="font-mono text-brand-500 hover:text-brand-400">
          {row.symbol}
        </Link>
      ),
    },
    { key: 'pe_ratio', label: 'P/E', align: 'right', sortValue: (row) => row.pe_ratio, render: (row) => formatRatio(row.pe_ratio) },
    {
      key: 'dividend_yield',
      label: 'Div Yield',
      align: 'right',
      sortValue: (row) => row.dividend_yield,
      render: (row) => formatPerformancePct(row.dividend_yield),
    },
    {
      key: 'debt_equity',
      label: 'Debt/Equity',
      align: 'right',
      sortValue: (row) => row.debt_equity,
      render: (row) => formatRatio(row.debt_equity),
    },
    {
      key: 'current_ratio',
      label: 'Current Ratio',
      align: 'right',
      sortValue: (row) => row.current_ratio,
      render: (row) => formatRatio(row.current_ratio),
    },
    {
      key: 'eps_ttm',
      label: 'EPS (TTM)',
      align: 'right',
      sortValue: (row) => row.eps_ttm,
      render: (row) => formatRatio(row.eps_ttm),
    },
    {
      key: 'revenue_yoy',
      label: 'Revenue YoY',
      align: 'right',
      sortValue: (row) => row.revenue_growth?.yoy,
      render: (row) => formatPctCell(row.revenue_growth?.yoy),
    },
    {
      key: 'revenue_qoq',
      label: 'Revenue QoQ',
      align: 'right',
      sortValue: (row) => row.revenue_growth?.qoq,
      render: (row) => formatPctCell(row.revenue_growth?.qoq),
    },
    {
      key: 'revenue_cagr',
      label: 'Revenue CAGR (4Q)',
      align: 'right',
      sortValue: (row) => row.revenue_growth?.cagr,
      render: (row) => formatPctCell(row.revenue_growth?.cagr),
    },
    {
      key: 'ebitda_yoy',
      label: 'EBITDA YoY',
      align: 'right',
      sortValue: (row) => row.ebitda_growth?.yoy,
      render: (row) => formatPctCell(row.ebitda_growth?.yoy),
    },
    {
      key: 'ebitda_qoq',
      label: 'EBITDA QoQ',
      align: 'right',
      sortValue: (row) => row.ebitda_growth?.qoq,
      render: (row) => formatPctCell(row.ebitda_growth?.qoq),
    },
    {
      key: 'ebitda_cagr',
      label: 'EBITDA CAGR (4Q)',
      align: 'right',
      sortValue: (row) => row.ebitda_growth?.cagr,
      render: (row) => formatPctCell(row.ebitda_growth?.cagr),
    },
    {
      key: 'ocf_yoy',
      label: 'OCF YoY',
      align: 'right',
      sortValue: (row) => row.ocf_growth?.yoy,
      render: (row) => formatPctCell(row.ocf_growth?.yoy),
    },
    {
      key: 'ocf_qoq',
      label: 'OCF QoQ',
      align: 'right',
      sortValue: (row) => row.ocf_growth?.qoq,
      render: (row) => formatPctCell(row.ocf_growth?.qoq),
    },
    {
      key: 'ocf_cagr',
      label: 'OCF CAGR (4Q)',
      align: 'right',
      sortValue: (row) => row.ocf_growth?.cagr,
      render: (row) => formatPctCell(row.ocf_growth?.cagr),
    },
    {
      key: 'price_change_6m',
      label: 'Price Δ 6M',
      align: 'right',
      sortValue: (row) => row.price_change_6m,
      render: (row) => formatPctCell(row.price_change_6m),
    },
  ];
}

function priceColumns(assetType: AssetTabId): DataTableColumn<AssetOverviewRow>[] {
  const cols: DataTableColumn<AssetOverviewRow>[] = [
    {
      key: 'symbol',
      label: 'Symbol',
      sortValue: (row) => row.symbol,
      render: (row) => (
        <Link to={assetLink(assetType, row.symbol)} className="font-mono text-brand-500 hover:text-brand-400">
          {row.symbol}
        </Link>
      ),
    },
    {
      key: 'dividend_yield',
      label: 'Div Yield',
      align: 'right',
      sortValue: (row) => row.dividend_yield,
      render: (row) => formatPerformancePct(row.dividend_yield),
    },
  ];

  for (const period of PRICE_PERIODS) {
    cols.push({
      key: period,
      label: `Δ ${period}`,
      align: 'right',
      sortValue: (row) => row.performance?.[period],
      render: (row) => formatPctCell(row.performance?.[period]),
    });
  }
  return cols;
}

function macroColumns(): DataTableColumn<MacroOverviewRow>[] {
  return [
    {
      key: 'series_id',
      label: 'Series',
      sortValue: (row) => row.series_id,
      render: (row) => (
        <Link
          to={`/dashboard/macro/${row.series_id}`}
          className="hover:text-brand-400"
        >
          <span className="font-mono text-brand-500">{row.series_id}</span>
          <span className="text-slate-500 ml-2">{row.title}</span>
        </Link>
      ),
    },
    { key: 'change_1m', label: 'Δ 1M', align: 'right', sortValue: (row) => row.change_1m, render: (row) => formatPctCell(row.change_1m) },
    { key: 'change_3m', label: 'Δ 3M', align: 'right', sortValue: (row) => row.change_3m, render: (row) => formatPctCell(row.change_3m) },
    { key: 'change_6m', label: 'Δ 6M', align: 'right', sortValue: (row) => row.change_6m, render: (row) => formatPctCell(row.change_6m) },
    { key: 'change_ytd', label: 'Δ YTD', align: 'right', sortValue: (row) => row.change_ytd, render: (row) => formatPctCell(row.change_ytd) },
    {
      key: 'ma50',
      label: 'vs 50 MA',
      align: 'center',
      sortValue: (row) => maPositionSortValue(row.ma50_position),
      render: (row) => formatMaBadge(row.ma50_position),
    },
    {
      key: 'ma200',
      label: 'vs 200 MA',
      align: 'center',
      sortValue: (row) => maPositionSortValue(row.ma200_position),
      render: (row) => formatMaBadge(row.ma200_position),
    },
  ];
}

function AssetOverviewSection() {
  const [assetTab, setAssetTab] = useState<AssetTabId>('stock');
  const [rows, setRows] = useState<AssetOverviewRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (tab: AssetTabId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await marketDataApi.getAssetOverview(tab);
      setRows(data.rows);
    } catch (e) {
      setRows([]);
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(assetTab);
  }, [assetTab, load]);

  const columns = useMemo(
    () => (assetTab === 'stock' ? stockColumns(assetTab) : priceColumns(assetTab)),
    [assetTab],
  );

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-200">Markets</h2>
        <p className="text-sm text-slate-500 mt-1">
          Active watchlist instruments with fundamentals and price performance.
        </p>
      </div>
      <TabBar tabs={ASSET_TABS} active={assetTab} onChange={setAssetTab} />
      {error && <ErrorAlert message={error} />}
      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.symbol}
          sortResetKey={assetTab}
          emptyMessage="No active instruments in your watchlist for this asset type."
        />
      )}
    </section>
  );
}

function MacroOverviewSection() {
  const [macroTab, setMacroTab] = useState<MacroTabId>('all');
  const [rows, setRows] = useState<MacroOverviewRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (tab: MacroTabId) => {
    setLoading(true);
    setError(null);
    try {
      const data = await marketDataApi.getMacroOverview(tab);
      setRows(data.rows);
    } catch (e) {
      setRows([]);
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(macroTab);
  }, [macroTab, load]);

  const columns = useMemo(() => macroColumns(), []);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-slate-200">Macros</h2>
        <p className="text-sm text-slate-500 mt-1">
          FRED macro series with period changes and moving-average position.
        </p>
      </div>
      <MacroBriefPanel />
      <TabBar tabs={MACRO_TABS} active={macroTab} onChange={setMacroTab} />
      {error && <ErrorAlert message={error} />}
      {loading ? (
        <div className="flex justify-center py-10">
          <Spinner />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.series_id}
          sortResetKey={macroTab}
          emptyMessage="No macro series data available. Seed and backfill from Ingestion → FRED Macro."
        />
      )}
    </section>
  );
}

export default function OverviewPage() {
  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Overview</h1>
        <p className="text-slate-400 text-sm mt-1">
          Watchlist summary tables for stocks, ETFs, crypto, and macro indicators.
        </p>
      </div>
      <MarketSentimentPanel />
      <AssetOverviewSection />
      <MacroOverviewSection />
    </div>
  );
}
