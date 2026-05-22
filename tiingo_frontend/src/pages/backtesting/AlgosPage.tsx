import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ingestionApi } from '../../api/endpoints';
import type { Instrument } from '../../api/types';
import AlgosBacktestPanel from '../../components/backtesting/AlgosBacktestPanel';
import DateRangeControls from '../../components/DateRangeControls';
import InstrumentSearch from '../../components/InstrumentSearch';
import {
  OHLCV_TIMEFRAMES,
  type DateRangeValue,
  dateRangeModeForTimeframe,
  defaultDateRangeForTimeframe,
} from '../../constants/timeframes';

const BASE_PATH = '/backtesting/algos';
const ASSET_TYPE_FILTER = ['stock', 'etf'];

export default function AlgosPage() {
  const { symbol } = useParams<{ symbol?: string }>();
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Instrument | null>(null);
  const [decisionTimeframe, setDecisionTimeframe] = useState('1d');
  const [dateRange, setDateRange] = useState<DateRangeValue>(() =>
    defaultDateRangeForTimeframe('1d'),
  );

  useEffect(() => {
    if (!symbol) {
      setSelected(null);
      return;
    }

    let cancelled = false;
    ingestionApi
      .searchDbInstruments(symbol, ASSET_TYPE_FILTER, 1)
      .then((items) => {
        if (cancelled) return;
        const match = items.find((i) => i.symbol.toUpperCase() === symbol.toUpperCase());
        setSelected(
          match ?? {
            id: 0,
            symbol: symbol.toUpperCase(),
            name: symbol.toUpperCase(),
            asset_type: 'stock',
            currency: 'USD',
            is_active: true,
          },
        );
      })
      .catch(() => {
        if (!cancelled) {
          setSelected({
            id: 0,
            symbol: symbol.toUpperCase(),
            name: symbol.toUpperCase(),
            asset_type: 'stock',
            currency: 'USD',
            is_active: true,
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [symbol]);

  const handleSelect = (instrument: Instrument | null) => {
    setSelected(instrument);
    if (instrument) {
      navigate(`${BASE_PATH}/${instrument.symbol}`);
    } else {
      navigate(BASE_PATH);
    }
  };

  const handleDecisionTimeframeChange = (timeframe: string) => {
    setDecisionTimeframe(timeframe);
    setDateRange(defaultDateRangeForTimeframe(timeframe));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">Algos</h1>
        <p className="text-slate-400 text-sm mt-1">
          Run parametric strategies on ingested OHLCV data across multiple timeframes. Choose a
          decision aggregate for trade execution and optional signal aggregates per strategy leg.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <InstrumentSearch
          selected={selected}
          onSelect={handleSelect}
          assetTypeFilter={ASSET_TYPE_FILTER}
          placeholder="Search ingested stocks and ETFs"
        />
        <label className="space-y-1 text-sm">
          <span className="text-slate-400">Decision timeframe</span>
          <select
            value={decisionTimeframe}
            onChange={(e) => handleDecisionTimeframeChange(e.target.value)}
            className="bg-surface-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100"
          >
            {OHLCV_TIMEFRAMES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <DateRangeControls
        value={dateRange}
        onChange={setDateRange}
        mode={dateRangeModeForTimeframe(decisionTimeframe)}
      />

      {symbol ? (
        <AlgosBacktestPanel
          symbol={symbol}
          dateRange={dateRange}
          decisionTimeframe={decisionTimeframe}
        />
      ) : (
        <div className="text-center py-16 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          Search ingested stocks or ETFs to configure and run an algo backtest.
        </div>
      )}
    </div>
  );
}
