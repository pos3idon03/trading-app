import { useCallback, useEffect, useMemo, useState } from 'react';
import { executionApi } from '../../api/endpoints';
import type { AccountSnapshot, PositionSnapshot } from '../../api/executionTypes';
import DataTable, { type DataTableColumn } from '../../components/DataTable';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import { formatCurrency } from '../../utils/tradingDeployments';

interface PositionRow extends PositionSnapshot {
  id: string;
}

export default function PortfolioPage() {
  const [account, setAccount] = useState<AccountSnapshot | null>(null);
  const [positions, setPositions] = useState<PositionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await executionApi.getPortfolio();
      setAccount(response.account);
      setPositions(
        response.positions.map((row, index) => ({
          ...row,
          id: row.symbol ?? `position-${index}`,
        })),
      );
    } catch (err) {
      setAccount(null);
      setPositions([]);
      setError(err instanceof Error ? err.message : 'Failed to load portfolio.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const columns = useMemo((): DataTableColumn<PositionRow>[] => [
    { key: 'symbol', label: 'Symbol', sortValue: (row) => row.symbol ?? '' },
    { key: 'qty', label: 'Qty', align: 'right', sortValue: (row) => row.qty },
    { key: 'side', label: 'Side', sortValue: (row) => row.side ?? '' },
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
      render: (row) => formatCurrency(row.unrealized_pl),
    },
  ], []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Portfolio</h1>
        <p className="text-slate-400 text-sm mt-1">
          Alpaca paper account equity and open positions.
        </p>
      </div>

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

          <DataTable
            columns={columns}
            rows={positions}
            rowKey={(row) => row.id}
            sortResetKey={positions.length ? 'loaded' : 'empty'}
            emptyMessage="No open positions."
          />
        </>
      )}
    </div>
  );
}
