import { useState } from 'react';
import {
  DATE_RANGE_PRESETS,
  type DateRangePreset,
  type DateRangeValue,
  computePresetRange,
} from '../constants/timeframes';

interface DateRangeControlsProps {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
  mode?: 'datetime' | 'date';
}

function toLocalInputValue(iso: string | undefined, mode: 'datetime' | 'date'): string {
  if (!iso) return '';
  if (mode === 'date') return iso.slice(0, 10);
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInputValue(local: string, mode: 'datetime' | 'date'): string {
  if (!local) return '';
  if (mode === 'date') return local;
  return new Date(local).toISOString();
}

export default function DateRangeControls({
  value,
  onChange,
  mode = 'datetime',
}: DateRangeControlsProps) {
  const [customStart, setCustomStart] = useState(toLocalInputValue(value.start, mode));
  const [customEnd, setCustomEnd] = useState(toLocalInputValue(value.end, mode));

  const handlePreset = (preset: DateRangePreset) => {
    const next = computePresetRange(preset, mode);
    onChange(next);
    setCustomStart(toLocalInputValue(next.start, mode));
    setCustomEnd(toLocalInputValue(next.end, mode));
  };

  const handleCustomApply = () => {
    if (!customStart && !customEnd) {
      setCustomStart('');
      setCustomEnd('');
      onChange({ preset: 'MAX' });
      return;
    }
    onChange({
      preset: 'MAX',
      start: customStart ? fromLocalInputValue(customStart, mode) : undefined,
      end: customEnd ? fromLocalInputValue(customEnd, mode) : undefined,
    });
  };

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-wrap gap-1">
        {DATE_RANGE_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            onClick={() => handlePreset(preset)}
            className={`px-2.5 py-1.5 rounded-md text-xs font-medium border transition-colors ${
              value.preset === preset
                ? 'bg-brand-600 border-brand-500 text-white'
                : 'bg-surface-900 border-slate-700 text-slate-300 hover:border-slate-500'
            }`}
          >
            {preset}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          From
          <input
            type={mode === 'date' ? 'date' : 'datetime-local'}
            value={customStart}
            onChange={(e) => setCustomStart(e.target.value)}
            className="bg-surface-900 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-100"
          />
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          To
          <input
            type={mode === 'date' ? 'date' : 'datetime-local'}
            value={customEnd}
            onChange={(e) => setCustomEnd(e.target.value)}
            className="bg-surface-900 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-slate-100"
          />
        </label>
        <button
          type="button"
          onClick={handleCustomApply}
          className="px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-800 border border-slate-600 text-slate-200 hover:border-slate-400"
        >
          Apply
        </button>
      </div>
    </div>
  );
}
