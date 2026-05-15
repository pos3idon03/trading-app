import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import type { AssetItem, OHLCVRecord, OHLCVQueryResponse, ChartOverlayResponse } from '../api/types';

// ResizeObserver is not available in jsdom
(globalThis as unknown as Record<string, unknown>).ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

const mockSetMarkers = vi.fn();
const mockSetData = vi.fn();
const mockRemoveSeries = vi.fn();
const mockAddLineSeries = vi.fn(() => ({ setData: vi.fn() }));

// Mock lightweight-charts — it requires a real DOM canvas
vi.mock('lightweight-charts', () => ({
  createChart: vi.fn(() => ({
    addCandlestickSeries: vi.fn(() => ({
      setData: mockSetData,
      setMarkers: mockSetMarkers,
    })),
    addLineSeries: mockAddLineSeries,
    removeSeries: mockRemoveSeries,
    applyOptions: vi.fn(),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    remove: vi.fn(),
  })),
  ColorType: { Solid: 'solid' },
}));

vi.mock('../api/endpoints', () => ({
  dataApi: {
    getAssets: vi.fn(),
    getOHLCVBySymbol: vi.fn(),
    triggerIngestion: vi.fn(),
    deleteAsset: vi.fn(),
  },
  backtestApi: {
    getChartOverlay: vi.fn(),
  },
}));

vi.mock('../utils/assetDisplay', () => ({
  formatAssetOptionLabel: (a: AssetItem) => a.symbol,
}));

import OHLCVChart from '../pages/OHLCVChart';
import { dataApi, backtestApi } from '../api/endpoints';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function makeAsset(symbol: string, id = 1): AssetItem {
  return { id, symbol, name: `${symbol} Inc.`, asset_type: 'stock', exchange: 'NASDAQ', currency: 'USD', is_active: true };
}

function makeRecord(time: string, tf = '1d'): OHLCVRecord {
  return { time, asset_id: 1, timeframe: tf, open: 100, high: 105, low: 95, close: 102, volume: 50000, source: 'tiingo' };
}

function makeResponse(records: OHLCVRecord[], symbol = 'ADBE', tf = '1d'): OHLCVQueryResponse {
  return { asset_id: 1, symbol, timeframe: tf, records, count: records.length };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(dataApi.getAssets).mockResolvedValue({ assets: [makeAsset('ADBE')], count: 1 });
  vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse([]));
});

// ---------------------------------------------------------------------------
// TIMEFRAMES selector
// ---------------------------------------------------------------------------

describe('OHLCVChart – Timeframe selector', () => {
  it('renders all six supported timeframes', async () => {
    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    // Second combobox is the timeframe selector (first is the ticker selector)
    const selects = screen.getAllByRole('combobox');
    const tfSelect = selects[1] as HTMLSelectElement;
    const options = Array.from(tfSelect.options).map((o) => o.value);
    expect(options).toContain('5m');
    expect(options).toContain('15m');
    expect(options).toContain('30m');
    expect(options).toContain('1h');
    expect(options).toContain('4h');
    expect(options).toContain('1d');
  });

  it('defaults to 1d timeframe', async () => {
    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    const selects = screen.getAllByRole('combobox');
    expect((selects[1] as HTMLSelectElement).value).toBe('1d');
  });
});

// ---------------------------------------------------------------------------
// Load Chart button
// ---------------------------------------------------------------------------

describe('OHLCVChart – Load Chart', () => {
  it('calls getOHLCVBySymbol with selected symbol and timeframe', async () => {
    const records = [makeRecord('2026-05-01T00:00:00Z')];
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse(records));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));

    await waitFor(() => expect(dataApi.getOHLCVBySymbol).toHaveBeenCalledWith('ADBE', '1d', undefined, undefined));
  });

  it('calls getOHLCVBySymbol with 5m when timeframe is changed to 5m', async () => {
    const records = [makeRecord('2026-05-01T13:30:00Z', '5m')];
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse(records, 'ADBE', '5m'));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[1], { target: { value: '5m' } });
    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));

    await waitFor(() => expect(dataApi.getOHLCVBySymbol).toHaveBeenCalledWith('ADBE', '5m', undefined, undefined));
  });

  it('calls getOHLCVBySymbol with 15m when timeframe is changed to 15m', async () => {
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse([makeRecord('2026-05-01T13:30:00Z', '15m')], 'ADBE', '15m'));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[1], { target: { value: '15m' } });
    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));

    await waitFor(() => expect(dataApi.getOHLCVBySymbol).toHaveBeenCalledWith('ADBE', '15m', undefined, undefined));
  });

  it('displays bar count and source after successful load', async () => {
    const records = [makeRecord('2026-05-01T00:00:00Z'), makeRecord('2026-05-02T00:00:00Z')];
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse(records));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));

    await waitFor(() => screen.getByText(/2 bars/i));
    expect(screen.getByText(/tiingo/i)).toBeTruthy();
  });

  it('shows error alert when API returns an error', async () => {
    vi.mocked(dataApi.getOHLCVBySymbol).mockRejectedValue(new Error('No OHLCV data found for ADBE (1h)'));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[1], { target: { value: '1h' } });
    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));

    await waitFor(() => screen.getByText(/No OHLCV data found for ADBE/i));
  });
});

// ---------------------------------------------------------------------------
// Re-ingest always uses 1d timeframe
// ---------------------------------------------------------------------------

describe('OHLCVChart – Re-ingest', () => {
  it('always sends timeframes=["1d"] regardless of selected display timeframe', async () => {
    vi.mocked(dataApi.triggerIngestion).mockResolvedValue({
      status: 'completed', job_id: 'x', symbols: ['ADBE'], timeframes: ['1d'], message: 'ok',
    });

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    // Switch to an intraday timeframe
    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[1], { target: { value: '1h' } });

    fireEvent.click(screen.getByRole('button', { name: /re-ingest/i }));

    await waitFor(() => expect(dataApi.triggerIngestion).toHaveBeenCalledWith(
      expect.objectContaining({ symbols: ['ADBE'], timeframes: ['1d'] })
    ));
  });
});

// ---------------------------------------------------------------------------
// Delete + Re-ingest buttons
// ---------------------------------------------------------------------------

describe('OHLCVChart – Actions', () => {
  it('shows confirmation UI after clicking Delete Ticker', async () => {
    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /delete ticker/i }));
    expect(screen.getByText(/delete all data for/i)).toBeTruthy();
    expect(screen.getByRole('button', { name: /confirm/i })).toBeTruthy();
    expect(screen.getByRole('button', { name: /cancel/i })).toBeTruthy();
  });

  it('cancels delete confirmation on Cancel', async () => {
    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    fireEvent.click(screen.getByRole('button', { name: /delete ticker/i }));
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));

    expect(screen.queryByText(/delete all data for/i)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Strategy overlay
// ---------------------------------------------------------------------------

function makeOverlayResponse(strategy = 'rsi'): ChartOverlayResponse {
  return {
    strategy_name: strategy,
    trade_log: [
      {
        entry_time: '2026-01-02T00:00:00',
        exit_time: '2026-01-10T00:00:00',
        direction: 'long',
        entry_price: 100,
        exit_price: 110,
        pnl: 10,
        return_pct: 0.1,
      },
    ],
    indicator_series: [{ time: '2026-01-01', rsi: 55 }],
    duration_ms: 42,
  };
}

describe('OHLCVChart – Strategy overlay', () => {
  it('strategy dropdown is disabled before chart is loaded', async () => {
    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());

    const selects = screen.getAllByRole('combobox');
    const strategySelect = selects[selects.length - 1] as HTMLSelectElement;
    expect(strategySelect.disabled).toBe(true);
  });

  it('strategy dropdown is enabled after chart loads', async () => {
    const records = [makeRecord('2026-05-01T00:00:00Z'), makeRecord('2026-05-02T00:00:00Z')];
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse(records));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));

    await waitFor(() => screen.getByText(/2 bars/i));

    const selects = screen.getAllByRole('combobox');
    const strategySelect = selects[selects.length - 1] as HTMLSelectElement;
    expect(strategySelect.disabled).toBe(false);
  });

  it('calls getChartOverlay when a strategy is selected', async () => {
    const records = [makeRecord('2026-05-01T00:00:00Z'), makeRecord('2026-05-02T00:00:00Z')];
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse(records));
    vi.mocked(backtestApi.getChartOverlay).mockResolvedValue(makeOverlayResponse('rsi'));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));
    await waitFor(() => screen.getByText(/2 bars/i));

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[selects.length - 1], { target: { value: 'rsi' } });

    await waitFor(() => expect(backtestApi.getChartOverlay).toHaveBeenCalledWith(
      expect.objectContaining({ symbol: 'ADBE', strategy_name: 'rsi', timeframe: '1d' })
    ));
  });

  it('shows trade count and duration after overlay loads', async () => {
    const records = [makeRecord('2026-05-01T00:00:00Z'), makeRecord('2026-05-02T00:00:00Z')];
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse(records));
    vi.mocked(backtestApi.getChartOverlay).mockResolvedValue(makeOverlayResponse('rsi'));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));
    await waitFor(() => screen.getByText(/2 bars/i));

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[selects.length - 1], { target: { value: 'rsi' } });

    await waitFor(() => screen.getByText(/1 trade/i));
  });

  it('shows error message when overlay API fails', async () => {
    const records = [makeRecord('2026-05-01T00:00:00Z'), makeRecord('2026-05-02T00:00:00Z')];
    vi.mocked(dataApi.getOHLCVBySymbol).mockResolvedValue(makeResponse(records));
    vi.mocked(backtestApi.getChartOverlay).mockRejectedValue(new Error('Overlay failed'));

    render(<OHLCVChart />);
    await waitFor(() => expect(dataApi.getAssets).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /load chart/i }));
    await waitFor(() => screen.getByText(/2 bars/i));

    const selects = screen.getAllByRole('combobox');
    fireEvent.change(selects[selects.length - 1], { target: { value: 'rsi' } });

    await waitFor(() => screen.getByText(/Overlay failed/i));
  });
});
