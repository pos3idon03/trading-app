import clsx from 'clsx';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { formatPerformancePct, performanceSublineClass } from '../utils/stockPerformance';
import { sortRows, type SortDirection } from '../utils/dataTableSort';

export type DataTableAlign = 'left' | 'right' | 'center';

export interface DataTableColumn<T> {
  key: string;
  label: string;
  align?: DataTableAlign;
  render?: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number | null | undefined;
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  emptyMessage?: string;
  sortResetKey?: string;
}

const alignClass = (align: DataTableAlign = 'left') => {
  if (align === 'right') return 'text-right';
  if (align === 'center') return 'text-center';
  return 'text-left';
};

function SortIndicator({ active, direction }: { active: boolean; direction: SortDirection }) {
  if (!active) {
    return <span className="ml-1 text-slate-600">↕</span>;
  }
  return <span className="ml-1 text-brand-500">{direction === 'asc' ? '↑' : '↓'}</span>;
}

export function formatPctCell(value: number | null | undefined): ReactNode {
  return (
    <span className={performanceSublineClass(value)}>
      {formatPerformancePct(value)}
    </span>
  );
}

export function formatMaBadge(position: string): ReactNode {
  if (position === 'Above') {
    return <span className="text-emerald-400">Above</span>;
  }
  if (position === 'Below') {
    return <span className="text-red-400">Below</span>;
  }
  if (position === 'At') {
    return <span className="text-slate-400">At</span>;
  }
  return <span className="text-slate-500">—</span>;
}

export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  emptyMessage = 'No data available.',
  sortResetKey,
}: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  useEffect(() => {
    setSortKey(null);
    setSortDirection('asc');
  }, [sortResetKey]);

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;
    const column = columns.find((col) => col.key === sortKey);
    if (!column?.sortValue) return rows;
    return sortRows(rows, column.sortValue, sortDirection);
  }, [columns, rows, sortDirection, sortKey]);

  const toggleSort = (column: DataTableColumn<T>) => {
    if (!column.sortValue) return;
    if (sortKey !== column.key) {
      setSortKey(column.key);
      setSortDirection('asc');
      return;
    }
    setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
  };

  if (rows.length === 0) {
    return (
      <p className="text-sm text-slate-500 bg-surface-900 border border-slate-800 rounded-xl p-6 text-center">
        {emptyMessage}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto bg-surface-900 border border-slate-800 rounded-xl">
      <table className="w-full text-sm min-w-max">
        <thead className="bg-surface-800 text-slate-400">
          <tr>
            {columns.map((col) => {
              const sortable = Boolean(col.sortValue);
              return (
                <th key={col.key} className={clsx('p-3 whitespace-nowrap', alignClass(col.align))}>
                  {sortable ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(col)}
                      className={clsx(
                        'inline-flex items-center gap-0.5 hover:text-slate-200 transition-colors',
                        sortKey === col.key && 'text-brand-500',
                        col.align === 'right' && 'ml-auto',
                        col.align === 'center' && 'mx-auto',
                      )}
                    >
                      <span>{col.label}</span>
                      <SortIndicator active={sortKey === col.key} direction={sortDirection} />
                    </button>
                  ) : (
                    col.label
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => (
            <tr key={rowKey(row)} className="border-t border-slate-800 hover:bg-surface-800/40">
              {columns.map((col) => (
                <td key={col.key} className={clsx('p-3 whitespace-nowrap', alignClass(col.align))}>
                  {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
