import {
  CHART_TYPES,
  STYLE_PRESET_OPTIONS,
  type CandleStylePreset,
  type OhlcvChartType,
} from '../../utils/ohlcvChartConfig';
import { MA_QUICK_PRESETS } from '../../utils/ohlcvTrendOverlays';
import {
  MAX_TREND_OVERLAYS,
  TREND_COLORS,
  trendSeriesLabel,
  type TrendOverlayConfig,
  type TrendType,
} from '../../utils/technicalIndicators';

interface OhlcvChartToolbarProps {
  chartType: OhlcvChartType;
  stylePreset: CandleStylePreset;
  overlays: TrendOverlayConfig[];
  showMarkerLegend: boolean;
  showTradeLegend: boolean;
  onChartTypeChange: (type: OhlcvChartType) => void;
  onStylePresetChange: (preset: CandleStylePreset) => void;
  onAddOverlay: (type: TrendType, period: number) => void;
  onRemoveOverlay: (id: string) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
}

const selectClass =
  'bg-surface-900 border border-slate-700 rounded-lg px-2 py-1.5 text-xs text-slate-100';

const buttonClass =
  'px-2.5 py-1.5 rounded-lg text-xs font-medium bg-surface-800 border border-slate-700 text-slate-200 hover:bg-surface-700';

export default function OhlcvChartToolbar({
  chartType,
  stylePreset,
  overlays,
  showMarkerLegend,
  showTradeLegend,
  onChartTypeChange,
  onStylePresetChange,
  onAddOverlay,
  onRemoveOverlay,
  onZoomIn,
  onZoomOut,
  onResetView,
}: OhlcvChartToolbarProps) {
  const canAddOverlay = overlays.length < MAX_TREND_OVERLAYS;

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={chartType}
          onChange={(e) => onChartTypeChange(e.target.value as OhlcvChartType)}
          className={selectClass}
          aria-label="Chart type"
        >
          {CHART_TYPES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          value={stylePreset}
          onChange={(e) => onStylePresetChange(e.target.value as CandleStylePreset)}
          className={selectClass}
          aria-label="Color preset"
        >
          {STYLE_PRESET_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <div className="h-5 w-px bg-slate-700 hidden sm:block" />

        {MA_QUICK_PRESETS.map((preset) => {
          const active = overlays.some(
            (o) => o.type === preset.type && o.period === preset.period,
          );
          return (
            <button
              key={preset.label}
              type="button"
              disabled={!canAddOverlay || active}
              onClick={() => onAddOverlay(preset.type, preset.period)}
              className={`${buttonClass} disabled:opacity-40`}
            >
              + {preset.label}
            </button>
          );
        })}

        <div className="h-5 w-px bg-slate-700 hidden sm:block" />

        <button type="button" onClick={onZoomIn} className={buttonClass}>
          Zoom in
        </button>
        <button type="button" onClick={onZoomOut} className={buttonClass}>
          Zoom out
        </button>
        <button type="button" onClick={onResetView} className={buttonClass}>
          Reset view
        </button>
      </div>

      {overlays.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {overlays.map((overlay, idx) => (
            <span
              key={overlay.id}
              className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs bg-surface-800 border border-slate-700 text-slate-300"
            >
              <span
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: TREND_COLORS[idx % TREND_COLORS.length] }}
              />
              {trendSeriesLabel(overlay.type, overlay.period)}
              <button
                type="button"
                onClick={() => onRemoveOverlay(overlay.id)}
                className="text-slate-500 hover:text-red-400"
                aria-label={`Remove ${trendSeriesLabel(overlay.type, overlay.period)}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      {showMarkerLegend && (
        <div className="flex flex-wrap gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
            Dividend (D)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-sm bg-purple-500" />
            Split (S)
          </span>
          {showTradeLegend && (
            <>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-500" />
                Entry (B)
              </span>
              <span className="flex items-center gap-1">
                <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
                Exit (S)
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
