import { describe, expect, it } from 'vitest';
import {
  instrumentToRef,
  macroToRef,
  observationsToPoints,
  ohlcvToPoints,
  pointsToObservations,
} from '../utils/seriesData';

describe('observationsToPoints', () => {
  it('maps macro observations to time series points', () => {
    const points = observationsToPoints([
      { obs_date: '2024-01-01', value: 1 },
      { obs_date: '2024-02-01', value: null },
    ]);
    expect(points).toEqual([
      { date: '2024-01-01', value: 1 },
      { date: '2024-02-01', value: null },
    ]);
  });
});

describe('ohlcvToPoints', () => {
  it('maps OHLCV close to daily points sorted by date', () => {
    const points = ohlcvToPoints([
      {
        time: '2024-02-01T00:00:00Z',
        open: 1,
        high: 2,
        low: 0.5,
        close: 1.5,
        volume: 10,
        source: 'tiingo_eod',
      },
      {
        time: '2024-01-01T00:00:00Z',
        open: 1,
        high: 2,
        low: 0.5,
        close: 1,
        volume: 10,
        source: 'tiingo_eod',
      },
    ]);
    expect(points).toEqual([
      { date: '2024-01-01', value: 1 },
      { date: '2024-02-01', value: 1.5 },
    ]);
  });
});

describe('pointsToObservations', () => {
  it('round-trips points to macro observations', () => {
    const obs = pointsToObservations([{ date: '2024-01-01', value: 42 }]);
    expect(obs).toEqual([{ obs_date: '2024-01-01', value: 42 }]);
  });
});

describe('series refs', () => {
  it('builds macro ref', () => {
    expect(
      macroToRef({
        series_id: 'GDP',
        title: 'Gross Domestic Product',
        category: 'gdp',
        is_enabled: true,
      }),
    ).toEqual({ source: 'macro', id: 'GDP', label: 'Gross Domestic Product' });
  });

  it('builds instrument ref with uppercase symbol', () => {
    expect(
      instrumentToRef({
        id: 1,
        symbol: 'msft',
        name: 'Microsoft',
        asset_type: 'stock',
        currency: 'USD',
        is_active: true,
      }),
    ).toEqual({
      source: 'instrument',
      id: 'MSFT',
      label: 'Microsoft',
      assetType: 'stock',
    });
  });
});
