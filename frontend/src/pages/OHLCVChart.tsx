import React, { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, type IChartApi, type ISeriesApi } from 'lightweight-charts';
import { dataApi } from '../api/endpoints';
import type { AssetItem, IngestRequest, OHLCVRecord } from '../api/types';
import Spinner from '../components/Spinner';
import ErrorAlert from '../components/ErrorAlert';
import MetricCard from '../components/MetricCard';

const TIMEFRAMES = ['1d', '1h', '4h', '30m'];

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
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [records, setRecords] = useState<OHLCVRecord[]>([]);
  const [resolvedSymbol, setResolvedSymbol] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const stats = computeStats(records);

  useEffect(() => {
    dataApi.getAssets()
      .then((res: { assets: AssetItem[]; count: number }) => {
        const active = res.assets.filter((a) => a.is_active);
        setAssets(active);
        if (active.length > 0) setSymbol(active[0].symbol);
      })
      .catch(() => setError('Failed to load available tickers.'));
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

  const reloadAssets = async (preferSymbol?: string) => {
    try {
      const res = await dataApi.getAssets();
      const active = res.assets.filter((a) => a.is_active);
      setAssets(active);
      if (preferSymbol && active.find((a) => a.symbol === preferSymbol)) {
        setSymbol(preferSymbol);
      } else if (active.length > 0) {
        setSymbol(active[0].symbol);
      } else {
        setSymbol('');
      }
    } catch {
      // non-fatal; keep current list
    }
  };

  const handleDelete = async () => {
    if (!symbol) return;
    setDeleteLoading(true);
    setError(null);
    setActionMessage(null);
    try {
      const resp = await dataApi.deleteAsset(symbol);
      setRecords([]);
      setResolvedSymbol(null);
      setConfirmDelete(false);
      setActionMessage(resp.message);
      await reloadAssets();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleReIngest = async () => {
    if (!symbol) return;
    setIngestLoading(true);
    setError(null);
    setActionMessage(null);
    const req: IngestRequest = { symbols: [symbol], timeframes: [timeframe] };
    try {
      const resp = await dataApi.triggerIngestion(req);
      setActionMessage(`Re-ingestion ${resp.status} for ${symbol}. Reload the chart to see fresh data.`);
      await reloadAssets(symbol);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIngestLoading(false);
    }
  };

  const loadData = async () => {
    const ticker = symbol.trim().toUpperCase();
    if (!ticker) return;
    setLoading(true);
    setError(null);
    setRecords([]);
    setResolvedSymbol(null);
    try {
      const resp = await dataApi.getOHLCVBySymbol(
        ticker,
        timeframe,
        startDate || undefined,
        endDate || undefined,
      );
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
      {actionMessage && (
        <div className="rounded-lg border border-brand-500/30 bg-brand-500/10 px-4 py-3 text-sm text-brand-300">
          {actionMessage}
        </div>
      )}

      <div className="card">
        <div className="flex flex-wrap gap-3 mb-4">
          <div>
            <label className="metric-label block mb-1">Ticker</label>
            <select
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={symbol}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSymbol(e.target.value)}
              disabled={assets.length === 0}
            >
              {assets.length === 0 && <option value="">Loading…</option>}
              {assets.map((a: AssetItem) => (
                <option key={a.id} value={a.symbol}>
                  {a.symbol}{a.name ? ` — ${a.name}` : ''}
                </option>
              ))}
            </select>
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
          <div>
            <label className="metric-label block mb-1">From</label>
            <input
              type="date"
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={startDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setStartDate(e.target.value)}
            />
          </div>
          <div>
            <label className="metric-label block mb-1">To</label>
            <input
              type="date"
              className="bg-surface-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-brand-500"
              value={endDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEndDate(e.target.value)}
            />
          </div>
          <div className="flex items-end gap-2">
            <button onClick={loadData} disabled={loading || !symbol.trim()} className="btn-primary disabled:opacity-50">
              {loading ? 'Loading…' : 'Load Chart'}
            </button>
            <button
              onClick={handleReIngest}
              disabled={ingestLoading || !symbol.trim()}
              className="rounded-lg border border-slate-600 bg-surface-800 px-3 py-2 text-sm text-slate-300 hover:border-brand-500 hover:text-brand-300 disabled:opacity-50 transition-colors"
            >
              {ingestLoading ? 'Ingesting…' : 'Re-ingest'}
            </button>
            {!confirmDelete ? (
              <button
                onClick={() => { setConfirmDelete(true); setActionMessage(null); }}
                disabled={!symbol.trim() || deleteLoading}
                className="rounded-lg border border-red-700/50 bg-surface-800 px-3 py-2 text-sm text-red-400 hover:border-red-500 hover:text-red-300 disabled:opacity-50 transition-colors"
              >
                Delete Ticker
              </button>
            ) : (
              <div className="flex items-center gap-2 rounded-lg border border-red-500/50 bg-red-900/20 px-3 py-2">
                <span className="text-xs text-red-300">Delete all data for {symbol}?</span>
                <button
                  onClick={handleDelete}
                  disabled={deleteLoading}
                  className="rounded px-2 py-0.5 text-xs font-semibold bg-red-600 text-white hover:bg-red-500 disabled:opacity-50"
                >
                  {deleteLoading ? 'Deleting…' : 'Confirm'}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="rounded px-2 py-0.5 text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
              </div>
            )}
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
