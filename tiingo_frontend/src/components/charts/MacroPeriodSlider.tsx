import { useMemo } from 'react';
import {
  buildSliderYearTicks,
  type PeriodChangePoint,
} from '../../utils/macroStandaloneData';

interface MacroPeriodSliderProps {
  changeSeries: PeriodChangePoint[];
  sliderIndex: number;
  stepLabel: string;
  macroId: string;
  assetId: string;
  disabled?: boolean;
  onChange: (index: number) => void;
}

export default function MacroPeriodSlider({
  changeSeries,
  sliderIndex,
  stepLabel,
  macroId,
  assetId,
  disabled = false,
  onChange,
}: MacroPeriodSliderProps) {
  const yearTicks = useMemo(() => buildSliderYearTicks(changeSeries), [changeSeries]);
  const selectedPoint = changeSeries[sliderIndex];
  const maxIndex = Math.max(0, changeSeries.length - 1);

  const handleInput = (value: string) => {
    onChange(Number.parseInt(value, 10));
  };

  return (
    <div className="space-y-2">
      <label htmlFor="period-slider" className="block text-xs text-slate-500">
        {stepLabel.charAt(0).toUpperCase() + stepLabel.slice(1)} period slider
      </label>

      {yearTicks.length > 0 && (
        <div className="relative h-6 mx-1">
          {yearTicks.map((tick) => (
            <button
              key={tick.year}
              type="button"
              disabled={disabled}
              onClick={() => onChange(tick.index)}
              className="absolute -translate-x-1/2 text-[10px] text-slate-500 hover:text-brand-500 disabled:opacity-50 whitespace-nowrap"
              style={{ left: `${tick.percent}%` }}
              title={`Jump to ${tick.year}`}
            >
              {tick.year}
            </button>
          ))}
        </div>
      )}

      <input
        id="period-slider"
        type="range"
        min={0}
        max={maxIndex}
        value={sliderIndex}
        disabled={disabled || changeSeries.length < 1}
        onInput={(e) => handleInput(e.currentTarget.value)}
        onChange={(e) => handleInput(e.target.value)}
        className="w-full accent-brand-500 disabled:opacity-50"
      />

      {selectedPoint && (
        <p className="text-xs text-slate-400 font-mono">
          {selectedPoint.date} · {macroId}{' '}
          {selectedPoint.macroChange >= 0 ? '+' : ''}
          {selectedPoint.macroChange.toFixed(2)}% · {assetId}{' '}
          {selectedPoint.assetChange >= 0 ? '+' : ''}
          {selectedPoint.assetChange.toFixed(2)}%
        </p>
      )}
    </div>
  );
}
