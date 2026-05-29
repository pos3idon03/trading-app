import type { UTCTimestamp } from 'lightweight-charts';
import type { OHLCVBar } from '../api/types';
import {
  TREND_COLORS,
  computeEMA,
  computeSMA,
  trendSeriesKey,
  type TrendOverlayConfig,
  type TrendType,
} from './technicalIndicators';
import { buildCandleData } from './ohlcvChartData';

export interface OhlcvOverlayLine {
  key: string;
  color: string;
  points: { time: string | UTCTimestamp; value: number }[];
}

export interface MaQuickPreset {
  type: TrendType;
  period: number;
  label: string;
}

export const MA_QUICK_PRESETS: MaQuickPreset[] = [
  { type: 'sma', period: 20, label: 'SMA 20' },
  { type: 'sma', period: 50, label: 'SMA 50' },
  { type: 'sma', period: 200, label: 'SMA 200' },
  { type: 'ema', period: 20, label: 'EMA 20' },
];

export function buildOhlcvOverlayLines(
  records: OHLCVBar[],
  timeframe: string,
  overlays: TrendOverlayConfig[],
): OhlcvOverlayLine[] {
  const candles = buildCandleData(records, timeframe);
  const closes = candles.map((c) => c.close);

  return overlays.map((overlay, idx) => {
    const computed =
      overlay.type === 'sma'
        ? computeSMA(closes, overlay.period)
        : computeEMA(closes, overlay.period);

    const points: { time: string | UTCTimestamp; value: number }[] = [];
    for (let i = 0; i < candles.length; i += 1) {
      const value = computed[i];
      if (value != null) {
        points.push({ time: candles[i].time, value });
      }
    }

    return {
      key: trendSeriesKey(overlay.type, overlay.period),
      color: TREND_COLORS[idx % TREND_COLORS.length],
      points,
    };
  });
}

export function createOverlayId(type: TrendType, period: number): string {
  return `${type}_${period}_${Date.now()}`;
}

export function hasOverlay(
  overlays: TrendOverlayConfig[],
  type: TrendType,
  period: number,
): boolean {
  return overlays.some((o) => o.type === type && o.period === period);
}
