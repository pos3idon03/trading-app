import { useCallback, useEffect, useRef, useState } from 'react';
import { createChart, type IChartApi, type ISeriesApi } from 'lightweight-charts';
import type { BacktestTrade } from '../../api/backtestTypes';
import type { OHLCVBar } from '../../api/types';
import {
  buildChartOptions,
  resetTimeScale,
  supportsOhlcMarkers,
  zoomTimeScaleIn,
  zoomTimeScaleOut,
  type CandleStylePreset,
  type OhlcvChartType,
} from '../../utils/ohlcvChartConfig';
import {
  applyPriceSeriesStyle,
  createPriceSeries,
  setPriceSeriesData,
  setPriceSeriesMarkers,
  syncOverlaySeries,
  type PriceSeries,
} from '../../utils/ohlcvChartSeries';
import {
  buildCandleData,
  buildCloseLineData,
  buildCorporateActionMarkers,
  buildTradeMarkers,
  buildVolumeData,
  mergeChartMarkers,
} from '../../utils/ohlcvChartData';
import {
  MAX_TREND_OVERLAYS,
  type TrendOverlayConfig,
  type TrendType,
} from '../../utils/technicalIndicators';
import {
  buildOhlcvOverlayLines,
  createOverlayId,
  hasOverlay,
} from '../../utils/ohlcvTrendOverlays';
import OhlcvChartToolbar from './OhlcvChartToolbar';

interface OhlcvTimelineChartProps {
  records: OHLCVBar[];
  timeframe: string;
  height?: number;
  trades?: BacktestTrade[];
  showToolbar?: boolean;
}

export default function OhlcvTimelineChart({
  records,
  timeframe,
  height = 520,
  trades = [],
  showToolbar = true,
}: OhlcvTimelineChartProps) {
  const [chartType, setChartType] = useState<OhlcvChartType>('candlestick');
  const [stylePreset, setStylePreset] = useState<CandleStylePreset>('classic');
  const [overlays, setOverlays] = useState<TrendOverlayConfig[]>([]);

  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const priceSeriesRef = useRef<PriceSeries | null>(null);
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const overlaySeriesRef = useRef<Map<string, ISeriesApi<'Line'>>>(new Map());
  const shouldFitRef = useRef(true);
  const prevTimeframeRef = useRef(timeframe);
  const prevRecordsLenRef = useRef(0);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(
      containerRef.current,
      buildChartOptions(containerRef.current.clientWidth, height),
    );

    chart.priceScale('right').applyOptions({
      scaleMargins: { top: 0.05, bottom: 0.28 },
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: '',
    });

    chart.priceScale('').applyOptions({
      scaleMargins: { top: 0.78, bottom: 0 },
    });

    chartRef.current = chart;
    volumeRef.current = volumeSeries;
    shouldFitRef.current = true;

    const observer = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      overlaySeriesRef.current.clear();
      chart.remove();
      chartRef.current = null;
      priceSeriesRef.current = null;
      volumeRef.current = null;
    };
  }, [height]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    if (priceSeriesRef.current) {
      chart.removeSeries(priceSeriesRef.current);
    }

    priceSeriesRef.current = createPriceSeries(chart, chartType, stylePreset);
    shouldFitRef.current = true;
  }, [chartType, stylePreset, height]);

  useEffect(() => {
    const chart = chartRef.current;
    const priceSeries = priceSeriesRef.current;
    const volumeSeries = volumeRef.current;
    if (!chart || !priceSeries || !volumeSeries || !records.length) return;

    if (timeframe !== prevTimeframeRef.current) {
      shouldFitRef.current = true;
      prevTimeframeRef.current = timeframe;
    }
    if (prevRecordsLenRef.current === 0 && records.length > 0) {
      shouldFitRef.current = true;
    }
    prevRecordsLenRef.current = records.length;

    const savedRange = shouldFitRef.current
      ? null
      : chart.timeScale().getVisibleLogicalRange();

    applyPriceSeriesStyle(priceSeries, chartType, stylePreset);

    const candles = buildCandleData(records, timeframe);
    const closeLine = buildCloseLineData(records, timeframe);
    const volume = buildVolumeData(records, timeframe, stylePreset);
    const markers = mergeChartMarkers(
      buildCorporateActionMarkers(records, timeframe),
      buildTradeMarkers(trades, timeframe),
    );

    setPriceSeriesData(priceSeries, chartType, candles, closeLine);
    if (supportsOhlcMarkers(chartType)) {
      setPriceSeriesMarkers(priceSeries, chartType, markers);
    }
    volumeSeries.setData(volume);

    const overlayLines = buildOhlcvOverlayLines(records, timeframe, overlays);
    syncOverlaySeries(chart, overlayLines, overlaySeriesRef.current);

    if (shouldFitRef.current) {
      chart.timeScale().fitContent();
      shouldFitRef.current = false;
    } else if (savedRange) {
      chart.timeScale().setVisibleLogicalRange(savedRange);
    }
  }, [records, timeframe, trades, chartType, stylePreset, overlays]);

  const handleResetView = useCallback(() => {
    if (!chartRef.current) return;
    shouldFitRef.current = true;
    resetTimeScale(chartRef.current);
  }, []);

  const handleZoomIn = useCallback(() => {
    if (!chartRef.current) return;
    zoomTimeScaleIn(chartRef.current, records.length);
  }, [records.length]);

  const handleZoomOut = useCallback(() => {
    if (!chartRef.current) return;
    zoomTimeScaleOut(chartRef.current, records.length);
  }, [records.length]);

  const handleAddOverlay = useCallback((type: TrendType, period: number) => {
    setOverlays((current) => {
      if (hasOverlay(current, type, period) || current.length >= MAX_TREND_OVERLAYS) {
        return current;
      }
      return [...current, { id: createOverlayId(type, period), type, period }];
    });
  }, []);

  const handleRemoveOverlay = useCallback((id: string) => {
    setOverlays((current) => current.filter((overlay) => overlay.id !== id));
  }, []);

  if (!records.length) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500 text-sm border border-slate-800 rounded-lg bg-surface-900">
        No chart data available.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {showToolbar && (
        <OhlcvChartToolbar
          chartType={chartType}
          stylePreset={stylePreset}
          overlays={overlays}
          showMarkerLegend={timeframe === '1d'}
          showTradeLegend={trades.length > 0}
          onChartTypeChange={setChartType}
          onStylePresetChange={setStylePreset}
          onAddOverlay={handleAddOverlay}
          onRemoveOverlay={handleRemoveOverlay}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onResetView={handleResetView}
        />
      )}
      <div
        ref={containerRef}
        className="w-full border border-slate-800 rounded-lg overflow-hidden bg-surface-900"
      />
    </div>
  );
}
