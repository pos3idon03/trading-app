import { useState } from 'react';
import type { TrendType } from '../utils/technicalIndicators';

export interface TrendModalResult {
  type: TrendType;
  period: number;
}

type AddTrendModalProps = {
  open: boolean;
  onConfirm: (result: TrendModalResult) => void;
  onCancel: () => void;
};

const MIN_PERIOD = 2;
const MAX_PERIOD = 500;

export default function AddTrendModal({ open, onConfirm, onCancel }: AddTrendModalProps) {
  const [type, setType] = useState<TrendType>('sma');
  const [period, setPeriod] = useState('50');

  if (!open) return null;

  const parsedPeriod = Number.parseInt(period, 10);
  const isValid =
    Number.isFinite(parsedPeriod) && parsedPeriod >= MIN_PERIOD && parsedPeriod <= MAX_PERIOD;

  const handleConfirm = () => {
    if (!isValid) return;
    onConfirm({ type, period: parsedPeriod });
    setType('sma');
    setPeriod('50');
  };

  const handleCancel = () => {
    setType('sma');
    setPeriod('50');
    onCancel();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-trend-modal-title"
    >
      <div className="w-full max-w-md rounded-xl border border-slate-700 bg-surface-900 p-6 shadow-xl">
        <h2 id="add-trend-modal-title" className="text-lg font-medium text-white">
          Add trend overlay
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Choose a moving average type and period to overlay on the macro series.
        </p>

        <div className="mt-4 space-y-4">
          <div>
            <label htmlFor="trend-type" className="block text-xs text-slate-500 mb-1">
              Type
            </label>
            <select
              id="trend-type"
              value={type}
              onChange={(e) => setType(e.target.value as TrendType)}
              className="w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
            >
              <option value="sma">MA (Simple Moving Average)</option>
              <option value="ema">EMA (Exponential Moving Average)</option>
            </select>
          </div>

          <div>
            <label htmlFor="trend-period" className="block text-xs text-slate-500 mb-1">
              Period
            </label>
            <input
              id="trend-period"
              type="number"
              min={MIN_PERIOD}
              max={MAX_PERIOD}
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-full bg-surface-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100"
            />
            {!isValid && (
              <p className="mt-1 text-xs text-red-400">
                Period must be between {MIN_PERIOD} and {MAX_PERIOD}.
              </p>
            )}
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={handleCancel}
            className="px-4 py-2 rounded-lg text-sm border border-slate-700 text-slate-300 hover:bg-surface-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={!isValid}
            className="px-4 py-2 rounded-lg text-sm bg-brand-500 hover:bg-brand-600 text-white disabled:opacity-50"
          >
            Add trend
          </button>
        </div>
      </div>
    </div>
  );
}
