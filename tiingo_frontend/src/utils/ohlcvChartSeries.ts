import type {
  IChartApi,
  ISeriesApi,
  SeriesMarker,
  Time,
} from 'lightweight-charts';
import type { CandleStylePreset, OhlcvChartType } from './ohlcvChartConfig';
import { getStyleColors } from './ohlcvChartConfig';
import type { ChartBar, CloseLinePoint } from './ohlcvChartData';
import type { OhlcvOverlayLine } from './ohlcvTrendOverlays';

export type PriceSeries =
  | ISeriesApi<'Candlestick'>
  | ISeriesApi<'Bar'>
  | ISeriesApi<'Line'>
  | ISeriesApi<'Area'>;

export function createPriceSeries(
  chart: IChartApi,
  chartType: OhlcvChartType,
  preset: CandleStylePreset,
): PriceSeries {
  const colors = getStyleColors(preset);

  switch (chartType) {
    case 'bar':
      return chart.addBarSeries({
        upColor: colors.upColor,
        downColor: colors.downColor,
        thinBars: false,
      });
    case 'line':
      return chart.addLineSeries({
        color: colors.upColor,
        lineWidth: 2,
        priceLineVisible: false,
      });
    case 'area':
      return chart.addAreaSeries({
        topColor: `${colors.upColor}66`,
        bottomColor: `${colors.upColor}08`,
        lineColor: colors.upColor,
        lineWidth: 2,
        priceLineVisible: false,
      });
    case 'candlestick':
    default:
      return chart.addCandlestickSeries({
        upColor: colors.upColor,
        downColor: colors.downColor,
        borderVisible: false,
        wickUpColor: colors.wickUpColor,
        wickDownColor: colors.wickDownColor,
      });
  }
}

export function applyPriceSeriesStyle(
  series: PriceSeries,
  chartType: OhlcvChartType,
  preset: CandleStylePreset,
): void {
  const colors = getStyleColors(preset);

  if (chartType === 'candlestick') {
    (series as ISeriesApi<'Candlestick'>).applyOptions({
      upColor: colors.upColor,
      downColor: colors.downColor,
      wickUpColor: colors.wickUpColor,
      wickDownColor: colors.wickDownColor,
    });
    return;
  }

  if (chartType === 'bar') {
    (series as ISeriesApi<'Bar'>).applyOptions({
      upColor: colors.upColor,
      downColor: colors.downColor,
    });
    return;
  }

  if (chartType === 'line') {
    (series as ISeriesApi<'Line'>).applyOptions({ color: colors.upColor });
    return;
  }

  (series as ISeriesApi<'Area'>).applyOptions({
    topColor: `${colors.upColor}66`,
    bottomColor: `${colors.upColor}08`,
    lineColor: colors.upColor,
  });
}

export function setPriceSeriesData(
  series: PriceSeries,
  chartType: OhlcvChartType,
  candles: ChartBar[],
  closeLine: CloseLinePoint[],
): void {
  if (chartType === 'line' || chartType === 'area') {
    (series as ISeriesApi<'Line'> | ISeriesApi<'Area'>).setData(closeLine);
    return;
  }

  (series as ISeriesApi<'Candlestick'> | ISeriesApi<'Bar'>).setData(candles);
}

export function setPriceSeriesMarkers(
  series: PriceSeries,
  chartType: OhlcvChartType,
  markers: SeriesMarker<Time>[],
): void {
  if (chartType !== 'candlestick' && chartType !== 'bar') {
    return;
  }

  (series as ISeriesApi<'Candlestick'> | ISeriesApi<'Bar'>).setMarkers(markers);
}

export function syncOverlaySeries(
  chart: IChartApi,
  overlayLines: OhlcvOverlayLine[],
  seriesMap: Map<string, ISeriesApi<'Line'>>,
): void {
  const activeKeys = new Set(overlayLines.map((line) => line.key));

  for (const [key, lineSeries] of seriesMap) {
    if (!activeKeys.has(key)) {
      chart.removeSeries(lineSeries);
      seriesMap.delete(key);
    }
  }

  for (const line of overlayLines) {
    let lineSeries = seriesMap.get(line.key);
    if (!lineSeries) {
      lineSeries = chart.addLineSeries({
        color: line.color,
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      seriesMap.set(line.key, lineSeries);
    } else {
      lineSeries.applyOptions({ color: line.color });
    }
    lineSeries.setData(line.points);
  }
}
