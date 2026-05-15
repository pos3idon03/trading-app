import type { UTCTimestamp } from 'lightweight-charts';
import type { ChartOverlayResponse, ChartOverlayTradeEntry } from '../api/types';

export interface OverlayLineSeries {
  key: string;
  color: string;
  data: { time: string | UTCTimestamp; value: number }[];
}

export interface OverlayMarker {
  time: string | UTCTimestamp;
  position: 'belowBar' | 'aboveBar';
  color: string;
  shape: 'arrowUp' | 'arrowDown';
  text: string;
}

const INDICATOR_COLORS = [
  '#f59e0b', '#06b6d4', '#a78bfa', '#34d399', '#f87171', '#fb923c',
];

function parseTime(raw: string, isIntraday: boolean): string | UTCTimestamp {
  // Normalise Python's "YYYY-MM-DD HH:MM:SS+00:00" → "YYYY-MM-DDTHH:MM:SS+00:00"
  const normalized = raw.replace(' ', 'T');
  if (isIntraday) {
    return Math.floor(new Date(normalized).getTime() / 1000) as UTCTimestamp;
  }
  return normalized.split('T')[0];
}

export function buildLineSeriesData(
  overlay: ChartOverlayResponse,
  isIntraday: boolean,
): OverlayLineSeries[] {
  if (!overlay.indicator_series.length) return [];

  const sample = overlay.indicator_series[0];
  const keys = Object.keys(sample).filter((k) => k !== 'time');

  return keys.map((key, idx) => ({
    key,
    color: INDICATOR_COLORS[idx % INDICATOR_COLORS.length],
    data: overlay.indicator_series
      .filter((row) => row[key] != null && typeof row[key] === 'number')
      .map((row) => ({
        time: parseTime(String(row.time), isIntraday),
        value: row[key] as number,
      }))
      .sort((a, b) => (a.time > b.time ? 1 : -1)),
  }));
}

function buildEntryMarker(trade: ChartOverlayTradeEntry, isIntraday: boolean): OverlayMarker {
  return {
    time: parseTime(trade.entry_time, isIntraday),
    position: 'belowBar',
    color: '#22c55e',
    shape: 'arrowUp',
    text: 'B',
  };
}

function buildExitMarker(trade: ChartOverlayTradeEntry, isIntraday: boolean): OverlayMarker {
  const exitTime = trade.exit_time ?? trade.entry_time;
  return {
    time: parseTime(exitTime, isIntraday),
    position: 'aboveBar',
    color: '#ef4444',
    shape: 'arrowDown',
    text: 'S',
  };
}

export function buildTradeMarkers(
  overlay: ChartOverlayResponse,
  isIntraday: boolean,
): OverlayMarker[] {
  const markers: OverlayMarker[] = [];
  for (const trade of overlay.trade_log) {
    markers.push(buildEntryMarker(trade, isIntraday));
    if (trade.exit_time) {
      markers.push(buildExitMarker(trade, isIntraday));
    }
  }
  return markers.sort((a, b) => (a.time > b.time ? 1 : -1));
}
