import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { executionApi } from '../../api/endpoints';
import type { ExecutionOrder, TradingDeployment } from '../../api/executionTypes';
import DataTable, { type DataTableColumn } from '../../components/DataTable';
import ErrorAlert from '../../components/ErrorAlert';
import Spinner from '../../components/Spinner';
import { formatDateTime, formatSignal } from '../../utils/tradingDeployments';

interface OrderRow extends ExecutionOrder {
  modelLabel: string;
}

export default function OrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [deployments, setDeployments] = useState<TradingDeployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const statusFilter = searchParams.get('status') ?? '';
  const deploymentFilter = searchParams.get('deployment_id') ?? '';

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ordersResponse, deploymentsResponse] = await Promise.all([
        executionApi.listOrders({
          status: statusFilter || undefined,
          deployment_id: deploymentFilter || undefined,
        }),
        executionApi.listDeployments(),
      ]);
      setDeployments(deploymentsResponse.deployments);
      setOrders(
        ordersResponse.orders.map((order) => ({
          ...order,
          modelLabel: order.model_name ?? '—',
        })),
      );
    } catch (err) {
      setOrders([]);
      setDeployments([]);
      setError(err instanceof Error ? err.message : 'Failed to load orders.');
    } finally {
      setLoading(false);
    }
  }, [deploymentFilter, statusFilter]);

  useEffect(() => {
    void load();
  }, [load]);

  const columns = useMemo((): DataTableColumn<OrderRow>[] => [
    { key: 'symbol', label: 'Symbol', sortValue: (row) => row.symbol },
    { key: 'modelLabel', label: 'Model', sortValue: (row) => row.modelLabel },
    { key: 'side', label: 'Side', sortValue: (row) => row.side },
    { key: 'qty', label: 'Qty', align: 'right', sortValue: (row) => row.qty },
    {
      key: 'signal',
      label: 'Signal',
      sortValue: (row) => row.signal,
      render: (row) => formatSignal(row.signal),
    },
    { key: 'status', label: 'Status', sortValue: (row) => row.status },
    {
      key: 'submitted_at',
      label: 'Submitted',
      sortValue: (row) => new Date(row.submitted_at).getTime(),
      render: (row) => formatDateTime(row.submitted_at),
    },
    {
      key: 'filled_avg_price',
      label: 'Fill price',
      align: 'right',
      sortValue: (row) => row.filled_avg_price ?? 0,
      render: (row) => (row.filled_avg_price != null ? row.filled_avg_price.toFixed(2) : '—'),
    },
  ], []);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Orders</h1>
          <p className="text-slate-400 text-sm mt-1">
            Paper trading order history. If a signal did not become an order, check{' '}
            <Link to="/trading/activity" className="text-brand-500 hover:text-brand-400">
              Activity
            </Link>{' '}
            for blocked evaluations.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={statusFilter}
            onChange={(e) => {
              const params = new URLSearchParams(searchParams);
              if (e.target.value) params.set('status', e.target.value);
              else params.delete('status');
              setSearchParams(params);
            }}
            className="rounded-lg border border-slate-700 bg-surface-800 px-3 py-2 text-sm text-slate-100"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="filled">Filled</option>
            <option value="canceled">Canceled</option>
            <option value="rejected">Rejected</option>
          </select>
          <select
            value={deploymentFilter}
            onChange={(e) => {
              const params = new URLSearchParams(searchParams);
              if (e.target.value) params.set('deployment_id', e.target.value);
              else params.delete('deployment_id');
              setSearchParams(params);
            }}
            className="rounded-lg border border-slate-700 bg-surface-800 px-3 py-2 text-sm text-slate-100"
          >
            <option value="">All deployments</option>
            {deployments.map((deployment) => (
              <option key={deployment.id} value={deployment.id}>
                {deployment.symbol} · {deployment.model_name ?? deployment.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && <ErrorAlert message={error} />}

      {loading ? (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      ) : (
        <DataTable
          columns={columns}
          rows={orders}
          rowKey={(row) => row.id}
          sortResetKey={`${orders.length}-${statusFilter}-${deploymentFilter}`}
          emptyMessage="No orders yet. Blocked or hold signals appear under Activity, not Orders."
        />
      )}
    </div>
  );
}
