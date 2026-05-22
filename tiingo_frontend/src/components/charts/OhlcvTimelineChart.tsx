import { useEffect, useRef } from 'react';
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
} from 'lightweight-charts';
import type { BacktestTrade } from '../../api/backtestTypes';
import type { OHLCVBar } from '../../api/types';
import {
  buildCandleData,
  buildCorporateActionMarkers,
  buildTradeMarkers,
  buildVolumeData,
  mergeChartMarkers,
} from '../../utils/ohlcvChartData';

interface OhlcvTimelineChartProps {
  records: OHLCVBar[];
  timeframe: string;
  height?: number;
  trades?: BacktestTrade[];
}

export default function OhlcvTimelineChart({
  records,
  timeframe,
  height = 520,
  trades = [],
}: OhlcvTimelineChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);

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

    chart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.05, bottom: 0.28 },
    });

    const series = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });

    chart.priceScale('').applyOptions({
      scaleMargins: { top: 0.78, bottom: 0 },
    });

    chartRef.current = chart;
    seriesRef.current = series;
    volumeRef.current = volumeSeries;

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
      volumeRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    if (!seriesRef.current || !volumeRef.current) return;
    const candles = buildCandleData(records, timeframe);
    const volume = buildVolumeData(records, timeframe);
    const corporateMarkers = buildCorporateActionMarkers(records, timeframe);
    const tradeMarkers = buildTradeMarkers(trades, timeframe);
    const markers = mergeChartMarkers(corporateMarkers, tradeMarkers);

    seriesRef.current.setData(candles);
    volumeRef.current.setData(volume);
    seriesRef.current.setMarkers(markers);
    chartRef.current?.timeScale().fitContent();
  }, [records, timeframe, trades]);

  if (!records.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        No chart data available.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {timeframe === '1d' && (
        <div className="flex flex-wrap gap-4 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
            Dividend (D)
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-2 h-2 rounded-sm bg-purple-500" />
            Split (S)
          </span>
          {trades.length > 0 && (
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
      <div
        ref={containerRef}
        className="w-full border border-slate-800 rounded-lg overflow-hidden bg-surface-900"
      />
    </div>
  );
}
