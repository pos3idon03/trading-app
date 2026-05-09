import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, type IChartApi, type ISeriesApi } from 'lightweight-charts';
import { dataApi } from '../api/endpoints';
import type { AssetItem, OHLCVRecord } from '../api/types';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import MetricCard from '../components/MetricCard';

const TIMEFRAMES = ['1d', '1h', '4h', '30m'];
const DATALIST_ID = 'asset-symbols';

function formatPrice(v: number) {
  return v.toFixed(2);
}

function computeStats(records: OHLCVRecord[]) {
  if (!records.length) return null;
  const closes = records.map((r) => r.close);
  const latest = closes[closes.length - 1];
  const first = closes[0];
  const changePct = ((latest - first) / first) * 100;
  const high = Math.max(...records.map((r) => r.high));
  const low = Math.min(...records.map((r) => r.low));
  return { latest, changePct, high, low };
}

export default function OHLCVChart() {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartApi = useRef<IChartApi | null>(null);
  const candleSeries = useRef<ISeriesApi<'Candlestick'> | null>(null);

  const [symbol, setSymbol] = useState('');
  const [timeframe, setTimeframe] = useState('1d');
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [records, setRecords] = useState<OHLCVRecord[]>([]);
  const [resolvedSymbol, setResolvedSymbol] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const stats = computeStats(records);

  useEffect(() => {
    dataApi.getAssets().then((res: { assets: AssetItem[]; count: number }) => {
      setAssets(res.assets);
      if (res.assets.length > 0 && !symbol) {
        setSymbol(res.assets[0].symbol);
      }
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!chartRef.current) return;
    chartApi.current = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#1e293b' }, textColor: '#94a3b8' },
      grid: { vertLines: { color: '#334155' }, horzLines: { color: '#334155' } },
      crosshair: { mode: 1 },
      width: chartRef.current.clientWidth,
      height: 400,
    });
    candleSeries.current = chartApi.current.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    const observer = new ResizeObserver(() => {
      chartApi.current?.applyOptions({ width: chartRef.current!.clientWidth });
    });
    observer.observe(chartRef.current);

    return () => {
      observer.disconnect();
      chartApi.current?.remove();
    };
  }, []);

  useEffect(() => {
    if (!candleSeries.current || !records.length) return;
    type ChartBar = { time: string; open: number; high: number; low: number; close: number };
    const data: ChartBar[] = records.map((r: OHLCVRecord) => ({
      time: r.time.split('T')[0],
      open: r.open,
      high: r.high,
      low: r.low,
      close: r.close,
    })).sort((a: ChartBar, b: ChartBar) => (a.time > b.time ? 1 : -1));
    candleSeries.current.setData(data as never[]);
    chartApi.current?.timeScale().fitContent();
  }, [records]);

  const loadData = async () => {
    const ticker = symbol.trim().toUpperCase();
    if (!ticker) return;
    setLoading(true);
    setError(null);
    setRecords([]);
    setResolvedSymbol(null);
    try {
      const resp = await dataApi.getOHLCVBySymbol(ticker, timeframe);
      setRecords(resp.records);
      setResolvedSymbol(resp.symbol);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Price Data</h1>
        <p className="text-slate-400 text-sm mt-1">OHLCV candlestick chart viewer</p>
      </div>

      {error && <ErrorAlert message={error} />}

      <div className="card">
        <div className="flex flex-wrap gap-3 mb-4">
          <div>
            <label className="metric-label block mb-1">Ticker Symbol</label>
            <input
              type="text"
              list={DATALIST_ID}
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm w-32 text-slate-100 focus:outline-none focus:border-brand-500 uppercase"
              value={symbol}
              autoComplete="off"
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSymbol(e.target.value.toUpperCase())}
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && loadData()}
              placeholder="e.g. MSFT"
            />
            <datalist id={DATALIST_ID}>
              {assets.map((a: AssetItem) => (
                <option key={a.id} value={a.symbol}>
                  {a.name ?? a.symbol}
                </option>
              ))}
            </datalist>
          </div>
          <div>
            <label className="metric-label block mb-1">Timeframe</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={timeframe}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setTimeframe(e.target.value)}
            >
              {TIMEFRAMES.map((tf) => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </div>
          <div className="flex items-end">
            <button onClick={loadData} disabled={loading || !symbol.trim()} className="btn-primary disabled:opacity-50">
              {loading ? 'Loading…' : 'Load Chart'}
            </button>
          </div>
        </div>

        {stats && resolvedSymbol && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <MetricCard label="Last Close" value={formatPrice(stats.latest)} />
            <MetricCard
              label="Period Change"
              value={`${stats.changePct > 0 ? '+' : ''}${stats.changePct.toFixed(2)}%`}
              positive={stats.changePct > 0}
              negative={stats.changePct < 0}
            />
            <MetricCard label="Period High" value={formatPrice(stats.high)} positive />
            <MetricCard label="Period Low" value={formatPrice(stats.low)} negative />
          </div>
        )}

        {loading && <Spinner label="Loading chart data…" />}
        <div ref={chartRef} className="w-full" />

        {records.length > 0 && resolvedSymbol && (
          <p className="text-slate-500 text-xs mt-2">
            {resolvedSymbol} · {records.length} bars · source: {records[0]?.source}
          </p>
        )}
      </div>
    </div>
  );
}
