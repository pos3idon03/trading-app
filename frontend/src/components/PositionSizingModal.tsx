import { useEffect, useRef, useState } from 'react';
import type { UpdatePositionSizingRequest } from '../api/types';
import Spinner from './Spinner';

interface Props {
  symbol: string;
  onConfirm: (req: UpdatePositionSizingRequest) => Promise<void>;
  onClose: () => void;
}

export default function PositionSizingModal({ symbol, onConfirm, onClose }: Props) {
  const [maxAmount, setMaxAmount] = useState('');
  const [maxPct, setMaxPct] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  };

  const handleConfirm = async () => {
    setError(null);
    const req: UpdatePositionSizingRequest = {};
    if (maxAmount !== '') {
      const parsed = parseFloat(maxAmount);
      if (isNaN(parsed) || parsed <= 0) {
        setError('Max amount must be a positive number.');
        return;
      }
      req.max_amount_per_position = parsed;
    }
    if (maxPct !== '') {
      const parsed = parseFloat(maxPct);
      if (isNaN(parsed) || parsed <= 0 || parsed > 100) {
        setError('Max % must be between 0 and 100.');
        return;
      }
      req.max_pct_of_capital = parsed;
    }
    setLoading(true);
    try {
      await onConfirm(req);
      onClose();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? 'Failed to start auto-trading.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleOverlayClick}
    >
      <div className="bg-surface-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-md mx-4 p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-slate-100 font-semibold text-base">
            Start Auto-Trading — <span className="text-brand-500">{symbol}</span>
          </h2>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-200 text-lg leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <p className="text-slate-400 text-sm leading-relaxed">
          Optionally set a position size limit. If neither is set, the size will be
          calculated dynamically as a percentage of available uninvested capital.
        </p>

        <div className="space-y-4">
          <div>
            <label className="metric-label block mb-1">
              Max Amount per Position ($)
              <span className="text-slate-600 ml-1 font-normal">optional</span>
            </label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              placeholder="e.g. 1000"
              value={maxAmount}
              onChange={(e) => setMaxAmount(e.target.value)}
              className="w-full bg-surface-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500"
            />
          </div>

          <div>
            <label className="metric-label block mb-1">
              Max % of Available Capital
              <span className="text-slate-600 ml-1 font-normal">optional</span>
            </label>
            <input
              type="number"
              min="0.01"
              max="100"
              step="0.01"
              placeholder="e.g. 5"
              value={maxPct}
              onChange={(e) => setMaxPct(e.target.value)}
              className="w-full bg-surface-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {(maxAmount !== '' && maxPct !== '') && (
          <p className="text-xs text-yellow-500">
            Both limits set — max dollar amount takes priority.
          </p>
        )}

        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}

        <div className="flex gap-3 justify-end pt-1">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-400 hover:text-slate-100 transition-colors"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={loading}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? <Spinner size="sm" /> : null}
            Start Trading
          </button>
        </div>
      </div>
    </div>
  );
}
