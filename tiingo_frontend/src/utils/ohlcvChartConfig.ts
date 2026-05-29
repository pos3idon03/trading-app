import {
  ColorType,
  CrosshairMode,
  type ChartOptions,
  type DeepPartial,
  type IChartApi,
} from 'lightweight-charts';

export type OhlcvChartType = 'candlestick' | 'bar' | 'line' | 'area';

export type CandleStylePreset = 'classic' | 'blueOrange' | 'monochrome';

export interface CandleStyleColors {
  upColor: string;
  downColor: string;
  wickUpColor: string;
  wickDownColor: string;
}

export const CANDLE_STYLE_PRESETS: Record<
  CandleStylePreset,
  CandleStyleColors & { label: string }
> = {
  classic: {
    label: 'Classic',
    upColor: '#22c55e',
    downColor: '#ef4444',
    wickUpColor: '#22c55e',
    wickDownColor: '#ef4444',
  },
  blueOrange: {
    label: 'Blue / Orange',
    upColor: '#3b82f6',
    downColor: '#f97316',
    wickUpColor: '#3b82f6',
    wickDownColor: '#f97316',
  },
  monochrome: {
    label: 'Monochrome',
    upColor: '#e2e8f0',
    downColor: '#64748b',
    wickUpColor: '#e2e8f0',
    wickDownColor: '#64748b',
  },
};

export const CHART_TYPES: { value: OhlcvChartType; label: string }[] = [
  { value: 'candlestick', label: 'Candles' },
  { value: 'bar', label: 'Bars' },
  { value: 'line', label: 'Line' },
  { value: 'area', label: 'Area' },
];

export const STYLE_PRESET_OPTIONS = (
  Object.entries(CANDLE_STYLE_PRESETS) as [CandleStylePreset, (typeof CANDLE_STYLE_PRESETS)[CandleStylePreset]][]
).map(([value, preset]) => ({ value, label: preset.label }));

const ZOOM_IN_FACTOR = 0.8;
const ZOOM_OUT_FACTOR = 1.25;
const MIN_VISIBLE_BARS = 5;

export function buildChartOptions(width: number, height: number): DeepPartial<ChartOptions> {
  return {
    layout: {
      background: { type: ColorType.Solid, color: '#0f172a' },
      textColor: '#94a3b8',
    },
    grid: {
      vertLines: { color: '#1e293b' },
      horzLines: { color: '#1e293b' },
    },
    width,
    height,
    handleScroll: {
      mouseWheel: true,
      pressedMouseMove: true,
      horzTouchDrag: true,
      vertTouchDrag: false,
    },
    handleScale: {
      axisPressedMouseMove: { time: true, price: true },
      mouseWheel: true,
      pinch: true,
    },
    timeScale: {
      fixLeftEdge: false,
      fixRightEdge: false,
      rightOffset: 12,
    },
    crosshair: {
      mode: CrosshairMode.Normal,
    },
  };
}

export function supportsOhlcMarkers(chartType: OhlcvChartType): boolean {
  return chartType === 'candlestick' || chartType === 'bar';
}

export function zoomTimeScaleIn(chart: IChartApi, barCount: number): void {
  zoomTimeScale(chart, ZOOM_IN_FACTOR, barCount);
}

export function zoomTimeScaleOut(chart: IChartApi, barCount: number): void {
  zoomTimeScale(chart, ZOOM_OUT_FACTOR, barCount);
}

export function zoomTimeScale(chart: IChartApi, factor: number, barCount: number): void {
  const timeScale = chart.timeScale();
  const range = timeScale.getVisibleLogicalRange();
  if (!range) {
    timeScale.fitContent();
    return;
  }

  const span = range.to - range.from;
  const center = (range.from + range.to) / 2;
  const newSpan = Math.min(
    Math.max(span * factor, MIN_VISIBLE_BARS),
    Math.max(barCount, MIN_VISIBLE_BARS),
  );
  const half = newSpan / 2;

  timeScale.setVisibleLogicalRange({
    from: center - half,
    to: center + half,
  });
}

export function resetTimeScale(chart: IChartApi): void {
  chart.timeScale().fitContent();
}

export function getStyleColors(preset: CandleStylePreset): CandleStyleColors {
  const { upColor, downColor, wickUpColor, wickDownColor } = CANDLE_STYLE_PRESETS[preset];
  return { upColor, downColor, wickUpColor, wickDownColor };
}
