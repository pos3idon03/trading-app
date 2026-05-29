import { useCallback, useEffect, useMemo, useState } from 'react';
import { executionApi } from '../../api/endpoints';
import type {
  AccountSnapshot,
  PortfolioPositionRow,
  PortfolioSummary,
} from '../../api/executionTypes';
import DataTable, { type DataTableColumn } from '../../components/DataTable';
import DateRangeControls from '../../components/DateRangeControls';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import {
  defaultPortfolioDateRange,
  toPortfolioApiRange,
  type DateRangeValue,
} from '../../constants/timeframes';
import { formatCurrency } from '../../utils/tradingDeployments';
import {
  buildPortfolioSummaryCards,
  formatPortfolioPeriodLabel,
  formatPortfolioPl,
  portfolioPlCellClass,
} from '../../utils/tradingPortfolio';

interface PositionRow extends PortfolioPositionRow {
  id: string;
}

export default function PortfolioPage() {
  const [account, setAccount] = useState<AccountSnapshot | null>(null);
  const [positionRows, setPositionRows] = useState<PositionRow[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [periodLabel, setPeriodLabel] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRangeValue>(defaultPortfolioDateRange);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (range: DateRangeValue) => {
    setLoading(true);
    setError(null);
    try {
      const response = await executionApi.getPortfolio(toPortfolioApiRange(range));
      setAccount(response.account);
      setSummary(response.summary);
      setPeriodLabel(
        response.period
          ? formatPortfolioPeriodLabel(response.period.start, response.period.end)
          : null,
      );
      setPositionRows(
        (response.position_rows ?? []).map((row) => ({
          ...row,
          id: row.symbol,
        })),
      );
    } catch (err) {
      setAccount(null);
      setPositionRows([]);
      setSummary(null);
      setPeriodLabel(null);
      setError(err instanceof Error ? err.message : 'Failed to load portfolio.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(dateRange);
  }, [dateRange, load]);

  const summaryCards = useMemo(
    () => buildPortfolioSummaryCards(summary, periodLabel),
    [summary, periodLabel],
  );

  const positionColumns = useMemo((): DataTableColumn<PositionRow>[] => [
    { key: 'symbol', label: 'Symbol', sortValue: (row) => row.symbol },
    { key: 'source', label: 'Source', sortValue: (row) => row.source },
    { key: 'qty', label: 'Qty', align: 'right', sortValue: (row) => row.qty },
    { key: 'side', label: 'Side', sortValue: (row) => row.side },
    {
      key: 'market_value',
      label: 'Market value',
      align: 'right',
      sortValue: (row) => row.market_value,
      render: (row) => formatCurrency(row.market_value),
    },
    {
      key: 'unrealized_pl',
      label: 'Unrealized P/L',
      align: 'right',
      sortValue: (row) => row.unrealized_pl,
      render: (row) => (
        <span className={portfolioPlCellClass(row.unrealized_pl)}>
          {formatPortfolioPl(row.unrealized_pl)}
        </span>
      ),
    },
    {
      key: 'period_pl',
      label: 'Period P/L',
      align: 'right',
      sortValue: (row) => row.period_pl,
      render: (row) => (
        <span className={portfolioPlCellClass(row.period_pl)}>
          {formatPortfolioPl(row.period_pl)}
        </span>
      ),
    },
  ], []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Portfolio</h1>
        <p className="text-slate-400 text-sm mt-1">
          Alpaca paper account with deployment-attributed and untracked positions.
        </p>
      </div>

      <DateRangeControls
        value={dateRange}
        onChange={setDateRange}
        mode="date"
        autoApply
      />

      {error && <ErrorAlert message={error} />}

      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : (
        <>
          {account && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Equity', account.equity],
                ['Cash', account.cash],
                ['Buying power', account.buying_power],
                ['Portfolio value', account.portfolio_value],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-xl border border-slate-800 bg-surface-900 p-4"
                >
                  <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
                  <p className="text-xl font-semibold text-slate-100 mt-1">
                    {formatCurrency(value as number)}
                  </p>
                </div>
              ))}
            </div>
          )}

          {summaryCards.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {summaryCards.map((card) => (
                <div
                  key={card.label}
                  className={`rounded-xl border bg-surface-900 p-4 ${portfolioPlCellClass(card.toneValue)}`}
                >
                  <p className="text-xs uppercase tracking-wide text-slate-500">{card.label}</p>
                  <p className="text-xl font-semibold mt-1">{card.value}</p>
                  {card.sublabel && (
                    <p className="text-xs text-slate-500 mt-1">{card.sublabel}</p>
                  )}
                </div>
              ))}
            </div>
          )}

          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-slate-200">Positions</h2>
            <p className="text-xs text-slate-500">
              One row per symbol (Alpaca total) with deployment and untracked attribution in Source.
            </p>
            <DataTable
              columns={positionColumns}
              rows={positionRows}
              rowKey={(row) => row.id}
              sortResetKey={positionRows.length ? 'loaded' : 'empty'}
              emptyMessage="No open positions."
            />
          </section>
        </>
      )}
    </div>
  );
}
