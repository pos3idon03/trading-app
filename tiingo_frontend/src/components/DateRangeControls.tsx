import { useEffect, useRef, useState } from 'react';
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
  autoApply?: boolean;
  autoApplyDelayMs?: number;
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

function buildCustomRange(
  customStart: string,
  customEnd: string,
  mode: 'datetime' | 'date',
): DateRangeValue {
  if (!customStart && !customEnd) {
    return { preset: 'MAX' };
  }
  return {
    preset: 'MAX',
    start: customStart ? fromLocalInputValue(customStart, mode) : undefined,
    end: customEnd ? fromLocalInputValue(customEnd, mode) : undefined,
  };
}

export default function DateRangeControls({
  value,
  onChange,
  mode = 'datetime',
  autoApply = false,
  autoApplyDelayMs = 300,
}: DateRangeControlsProps) {
  const [customStart, setCustomStart] = useState(toLocalInputValue(value.start, mode));
  const [customEnd, setCustomEnd] = useState(toLocalInputValue(value.end, mode));
  const skipAutoApplyRef = useRef(false);

  useEffect(() => {
    setCustomStart(toLocalInputValue(value.start, mode));
    setCustomEnd(toLocalInputValue(value.end, mode));
  }, [value.start, value.end, mode]);

  const handlePreset = (preset: DateRangePreset) => {
    skipAutoApplyRef.current = true;
    const next = computePresetRange(preset, mode);
    onChange(next);
    setCustomStart(toLocalInputValue(next.start, mode));
    setCustomEnd(toLocalInputValue(next.end, mode));
  };

  const handleCustomApply = () => {
    skipAutoApplyRef.current = true;
    if (!customStart && !customEnd) {
      setCustomStart('');
      setCustomEnd('');
      onChange({ preset: 'MAX' });
      return;
    }
    onChange(buildCustomRange(customStart, customEnd, mode));
  };

  useEffect(() => {
    if (!autoApply || skipAutoApplyRef.current) {
      skipAutoApplyRef.current = false;
      return;
    }

    const timer = window.setTimeout(() => {
      const next = buildCustomRange(customStart, customEnd, mode);
      const samePreset = next.preset === value.preset;
      const sameStart = (next.start ?? '') === (value.start ?? '');
      const sameEnd = (next.end ?? '') === (value.end ?? '');
      if (samePreset && sameStart && sameEnd) {
        return;
      }
      onChange(next);
    }, autoApplyDelayMs);

    return () => window.clearTimeout(timer);
  }, [autoApply, autoApplyDelayMs, customStart, customEnd, mode, onChange, value]);

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
