import { useCallback, useEffect, useState } from 'react';
import { marketDataApi } from '../api/endpoints';
import type { PerformancePeriod } from '../api/types';
import ErrorAlert from './ErrorAlert';
import Spinner from './Spinner';
import {
  PERFORMANCE_PERIOD_LABELS,
  formatExampleOutcome,
  formatPerformancePct,
  performanceCardClass,
  performanceSublineClass,
} from '../utils/stockPerformance';

interface PerformanceCardsProps {
  symbol: string;
}

const EMPTY_PERIOD = (period: string): PerformancePeriod => ({
  period,
  change_pct: null,
  price_change_pct: null,
  dividend_return_pct: null,
  total_return_pct: null,
  example_investment: 100,
  example_outcome: null,
  example_dividend_income: null,
});

const DEFAULT_PERIODS: PerformancePeriod[] = [
  EMPTY_PERIOD('1W'),
  EMPTY_PERIOD('1M'),
  EMPTY_PERIOD('3M'),
  EMPTY_PERIOD('6M'),
  EMPTY_PERIOD('YTD'),
  EMPTY_PERIOD('1Y'),
  EMPTY_PERIOD('2Y'),
  EMPTY_PERIOD('5Y'),
];

export default function PerformanceCards({ symbol }: PerformanceCardsProps) {
  const [periods, setPeriods] = useState<PerformancePeriod[]>(DEFAULT_PERIODS);
  const [currency, setCurrency] = useState('USD');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (sym: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await marketDataApi.getPerformance(sym);
      setPeriods(data.periods);
      setCurrency(data.currency || 'USD');
    } catch {
      setPeriods(DEFAULT_PERIODS);
      setCurrency('USD');
      setError('Failed to load performance data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(symbol);
  }, [symbol, load]);

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-semibold text-slate-200">Performance</h2>
      {error && <ErrorAlert message={error} />}
      {loading ? (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {periods.map((row) => {
            const total = row.total_return_pct ?? row.change_pct;
            return (
              <div
                key={row.period}
                className={`rounded-xl border p-4 ${performanceCardClass(total)}`}
              >
                <p className="text-lg font-bold text-center">{formatPerformancePct(total)}</p>
                <p className="text-xs mt-1 opacity-80 text-center">
                  {PERFORMANCE_PERIOD_LABELS[row.period] ?? row.period}
                </p>
                <div className="mt-3 space-y-1 text-xs">
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500">Price</span>
                    <span className={performanceSublineClass(row.price_change_pct)}>
                      {formatPerformancePct(row.price_change_pct)}
                    </span>
                  </div>
                  <div className="flex justify-between gap-2">
                    <span className="text-slate-500">Dividend</span>
                    <span className={performanceSublineClass(row.dividend_return_pct)}>
                      {formatPerformancePct(row.dividend_return_pct)}
                    </span>
                  </div>
                </div>
                <p className="text-[10px] mt-3 text-center text-slate-500 border-t border-slate-700/50 pt-2">
                  {formatExampleOutcome(currency, row.example_investment, row.example_outcome)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
