import { useEffect, useState } from 'react';
import { autoTradingApi } from '../api/endpoints';
import type { AutoTradingAssetRow, UpdatePositionSizingRequest } from '../api/types';
import ErrorAlert from '../components/ErrorAlert';
import PositionSizingModal from '../components/PositionSizingModal';
import Spinner from '../components/Spinner';

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function fmtPctVal(v: number | null): string {
  if (v == null) return '—';
  return `${(v * 100).toFixed(1)}%`;
}

function fmtVal(v: number | null, decimals = 2): string {
  if (v == null) return '—';
  return v.toFixed(decimals);
}

// ---------------------------------------------------------------------------
// Threshold indicator cell – shows value with BUY/SELL threshold hints
// ---------------------------------------------------------------------------

function ThresholdCell({
  value,
  buyThreshold,
  sellThreshold,
  isPercent,
}: {
  value: number | null;
  buyThreshold: number | null;
  sellThreshold: number | null;
  isPercent?: boolean;
}) {
  const display = isPercent ? fmtPctVal(value) : fmtVal(value);
  const fmt = isPercent ? fmtPctVal : fmtVal;

  let colorClass = 'text-slate-400';
  if (value != null) {
    if (buyThreshold != null && value >= buyThreshold) colorClass = 'text-green-400';
    else if (sellThreshold != null && value <= sellThreshold) colorClass = 'text-red-400';
  }

  return (
    <div>
      <span className={colorClass}>{display}</span>
      {(buyThreshold != null || sellThreshold != null) && (
        <div className="text-slate-600 text-xs space-y-0.5 mt-0.5">
          {buyThreshold != null && <div>buy ≥ {fmt(buyThreshold)}</div>}
          {sellThreshold != null && <div>sell ≤ {fmt(sellThreshold)}</div>}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Combo mode badge
// ---------------------------------------------------------------------------

const COMBO_LABELS: Record<string, string> = {
  all: 'All',
  majority: 'Majority',
  any: 'Any',
};

function ComboModeBadge({ mode }: { mode: string }) {
  return (
    <span className="px-2 py-0.5 rounded text-xs bg-surface-800 border border-slate-700 text-slate-300">
      {COMBO_LABELS[mode] ?? mode}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function StatusBadge({ started }: { started: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${
        started
          ? 'bg-green-900/40 text-green-400 border border-green-800'
          : 'bg-slate-800 text-slate-400 border border-slate-700'
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${started ? 'bg-green-400' : 'bg-slate-500'}`} />
      {started ? 'Running' : 'Stopped'}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AutoTradingPage() {
  const [rows, setRows] = useState<AutoTradingAssetRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [modalRow, setModalRow] = useState<AutoTradingAssetRow | null>(null);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    autoTradingApi
      .list()
      .then(setRows)
      .catch(() => setError('Failed to load auto-trading assets.'))
      .finally(() => setLoading(false));
  }, []);

  const handleStart = (row: AutoTradingAssetRow) => {
    setActionError(null);
    setModalRow(row);
  };

  const handleConfirmStart = async (req: UpdatePositionSizingRequest) => {
    if (!modalRow) return;
    setActionLoading(modalRow.strategy_id);
    try {
      const updated = await autoTradingApi.start(modalRow.strategy_id, req);
      setRows((prev) => prev.map((r) => (r.strategy_id === updated.strategy_id ? updated : r)));
      setModalRow(null);
    } finally {
      setActionLoading(null);
    }
  };

  const handleStop = async (row: AutoTradingAssetRow) => {
    setActionError(null);
    setActionLoading(row.strategy_id);
    try {
      const updated = await autoTradingApi.stop(row.strategy_id);
      setRows((prev) => prev.map((r) => (r.strategy_id === updated.strategy_id ? updated : r)));
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Failed to stop auto-trading.';
      setActionError(msg);
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="text-xl font-bold text-slate-100">Auto-Trading</h1>
        <p className="text-slate-400 text-sm">
          Assets with auto-trading enabled. Configure thresholds in Strategy Builder.
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}

      {error && <ErrorAlert message={error} />}
      {actionError && <ErrorAlert message={actionError} />}

      {!loading && !error && rows.length === 0 && (
        <div className="card text-center py-12 text-slate-500">
          No assets have auto-trading enabled. Enable it for an asset in the Strategy Builder.
        </div>
      )}

      {!loading && rows.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-2 px-3 text-slate-400 font-medium text-xs">Symbol</th>
                <th className="text-left py-2 px-3 text-slate-400 font-medium text-xs">Asset Name</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">MC Prob+</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">AI Conviction</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">AI Sentiment</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">AI Macro</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">Combo</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">Timeframe</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">Status</th>
                <th className="text-center py-2 px-3 text-slate-400 font-medium text-xs">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr
                  key={row.strategy_id}
                  className="border-b border-slate-800 hover:bg-surface-800/50 transition-colors"
                >
                  <td className="py-3 px-3 font-semibold text-brand-500">{row.symbol}</td>
                  <td className="py-3 px-3 text-slate-300">{row.asset_name ?? '—'}</td>

                  <td className="py-3 px-3 text-center">
                    <ThresholdCell
                      value={row.mc_prob_positive}
                      buyThreshold={row.mc_buy_prob_positive}
                      sellThreshold={row.mc_sell_prob_positive}
                      isPercent
                    />
                  </td>

                  <td className="py-3 px-3 text-center">
                    <ThresholdCell
                      value={row.ai_conviction}
                      buyThreshold={row.ai_buy_conviction}
                      sellThreshold={row.ai_sell_conviction}
                    />
                  </td>

                  <td className="py-3 px-3 text-center">
                    <ThresholdCell
                      value={row.ai_sentiment}
                      buyThreshold={row.ai_buy_sentiment}
                      sellThreshold={row.ai_sell_sentiment}
                    />
                  </td>

                  <td className="py-3 px-3 text-center">
                    <ThresholdCell
                      value={row.ai_macro}
                      buyThreshold={row.ai_buy_macro}
                      sellThreshold={row.ai_sell_macro}
                    />
                  </td>

                  <td className="py-3 px-3 text-center">
                    <ComboModeBadge mode={row.combination_mode} />
                  </td>

                  <td className="py-3 px-3 text-center">
                    <span className="px-2 py-0.5 rounded text-xs bg-surface-800 border border-slate-700 text-slate-300">
                      {row.algo_timeframe}
                    </span>
                  </td>

                  <td className="py-3 px-3 text-center">
                    <StatusBadge started={row.auto_trading_started} />
                  </td>

                  <td className="py-3 px-3 text-center">
                    {actionLoading === row.strategy_id ? (
                      <Spinner size="sm" />
                    ) : row.auto_trading_started ? (
                      <button
                        onClick={() => handleStop(row)}
                        className="px-3 py-1 text-xs rounded-lg bg-red-900/40 text-red-400 border border-red-800 hover:bg-red-800/50 transition-colors"
                      >
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => handleStart(row)}
                        className="px-3 py-1 text-xs rounded-lg bg-green-900/40 text-green-400 border border-green-800 hover:bg-green-800/50 transition-colors"
                      >
                        Start
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modalRow && (
        <PositionSizingModal
          symbol={modalRow.symbol}
          onConfirm={handleConfirmStart}
          onClose={() => setModalRow(null)}
        />
      )}
    </div>
  );
}
