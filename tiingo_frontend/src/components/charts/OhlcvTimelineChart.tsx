import { useEffect, useRef } from 'react';
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts';
import type { OHLCVBar } from '../../api/types';

const INTRADAY_TIMEFRAMES = new Set(['5m', '1m', '1h']);

type ChartBar = {
  time: string | UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

function buildCandleData(records: OHLCVBar[], timeframe: string): ChartBar[] {
  const isIntraday = INTRADAY_TIMEFRAMES.has(timeframe);
  return records
    .map((r) => ({
      time: isIntraday
        ? (Math.floor(new Date(r.time).getTime() / 1000) as UTCTimestamp)
        : r.time.split('T')[0],
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
    }))
    .sort((a, b) => (a.time > b.time ? 1 : -1));
}

interface OhlcvTimelineChartProps {
  records: OHLCVBar[];
  timeframe: string;
  height?: number;
}

export default function OhlcvTimelineChart({
  records,
  timeframe,
  height = 420,
}: OhlcvTimelineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      width: containerRef.current.clientWidth,
      height,
    });

    const series = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (!seriesRef.current) return;
    const data = buildCandleData(records, timeframe);
    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [records, timeframe]);

  if (!records.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        No chart data available.
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="w-full border border-slate-800 rounded-lg overflow-hidden bg-surface-900"
    />
  );
}
