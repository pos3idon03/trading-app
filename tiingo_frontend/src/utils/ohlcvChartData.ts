import type { SeriesMarker, Time, UTCTimestamp } from 'lightweight-charts';
import type { BacktestTrade } from '../api/backtestTypes';
import type { OHLCVBar } from '../api/types';
import { DAILY_PLUS_TIMEFRAMES, INTRADAY_TIMEFRAMES } from '../constants/timeframes';
import { getStyleColors, type CandleStylePreset } from './ohlcvChartConfig';

export type ChartBar = {
  time: string | UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

export type VolumeBar = {
  time: string | UTCTimestamp;
  value: number;
  color: string;
};

export type CloseLinePoint = {
  time: string | UTCTimestamp;
  value: number;
};

const UP_COLOR = '#22c55e';
const DOWN_COLOR = '#ef4444';
const DIVIDEND_COLOR = '#3b82f6';
const SPLIT_COLOR = '#a855f7';
const ENTRY_COLOR = '#22c55e';
const EXIT_COLOR = '#ef4444';

export function normalizeChartTime(raw: string, timeframe: string): string | UTCTimestamp {
  if (INTRADAY_TIMEFRAMES.has(timeframe)) {
    return Math.floor(new Date(raw).getTime() / 1000) as UTCTimestamp;
  }
  return new Date(raw).toISOString().slice(0, 10);
}

export function buildCandleData(records: OHLCVBar[], timeframe: string): ChartBar[] {
  const sorted = [...records].sort((a, b) => a.time.localeCompare(b.time));
  const byTime = new Map<string | number, ChartBar>();

  for (const r of sorted) {
    const time = normalizeChartTime(r.time, timeframe);
    byTime.set(time, {
      time,
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
    });
  }

  return [...byTime.values()].sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
}

export function buildCloseLineData(records: OHLCVBar[], timeframe: string): CloseLinePoint[] {
  return buildCandleData(records, timeframe).map((bar) => ({
    time: bar.time,
    value: bar.close,
  }));
}

export function buildVolumeData(
  records: OHLCVBar[],
  timeframe: string,
  stylePreset?: CandleStylePreset,
): VolumeBar[] {
  const colors = stylePreset ? getStyleColors(stylePreset) : null;
  const upColor = colors?.upColor ?? UP_COLOR;
  const downColor = colors?.downColor ?? DOWN_COLOR;
  const sorted = [...records].sort((a, b) => a.time.localeCompare(b.time));
  const byTime = new Map<string | number, VolumeBar>();

  for (const r of sorted) {
    const time = normalizeChartTime(r.time, timeframe);
    const up = r.close >= r.open;
    byTime.set(time, {
      time,
      value: r.volume,
      color: up ? `${upColor}99` : `${downColor}99`,
    });
  }

  return [...byTime.values()].sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
}

function splitLabel(factor: number): string {
  if (factor >= 1) {
    const whole = Number.isInteger(factor) ? factor.toFixed(0) : factor.toFixed(2);
    return `${whole}:1`;
  }
  const inverse = 1 / factor;
  const whole = Number.isInteger(inverse) ? inverse.toFixed(0) : inverse.toFixed(2);
  return `1:${whole}`;
}

export function buildCorporateActionMarkers(
  records: OHLCVBar[],
  timeframe: string,
): SeriesMarker<Time>[] {
  if (timeframe !== '1d') {
    return [];
  }

  const markers: SeriesMarker<Time>[] = [];

  for (const r of records) {
    const time = normalizeChartTime(r.time, timeframe) as Time;
    const divCash = r.div_cash ?? 0;
    const splitFactor = r.split_factor ?? 1;

    if (divCash > 0) {
      markers.push({
        time,
        position: 'belowBar',
        color: DIVIDEND_COLOR,
        shape: 'circle',
        text: 'D',
      });
    }
    if (splitFactor !== 1) {
      markers.push({
        time,
        position: 'belowBar',
        color: SPLIT_COLOR,
        shape: 'square',
        text: 'S',
      });
    }
  }

  return markers.sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
}

export function buildTradeMarkers(trades: BacktestTrade[], timeframe: string): SeriesMarker<Time>[] {
  if (!trades.length) {
    return [];
  }

  const markers: SeriesMarker<Time>[] = [];
  for (const trade of trades) {
    markers.push({
      time: normalizeChartTime(trade.entry_date, timeframe) as Time,
      position: 'belowBar',
      color: ENTRY_COLOR,
      shape: 'arrowUp',
      text: 'B',
    });
    markers.push({
      time: normalizeChartTime(trade.exit_date, timeframe) as Time,
      position: 'aboveBar',
      color: EXIT_COLOR,
      shape: 'arrowDown',
      text: 'S',
    });
  }

  return markers.sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
}

export function mergeChartMarkers(
  corporate: SeriesMarker<Time>[],
  trades: SeriesMarker<Time>[],
): SeriesMarker<Time>[] {
  return [...corporate, ...trades].sort((a, b) => (a.time > b.time ? 1 : a.time < b.time ? -1 : 0));
}

export function formatSplitTooltip(factor: number): string {
  return `Split ${splitLabel(factor)}`;
}

export function isDailyPlusChartTimeframe(timeframe: string): boolean {
  return DAILY_PLUS_TIMEFRAMES.has(timeframe);
}
