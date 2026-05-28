import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ingestionApi, mlBacktestApi } from '../../api/endpoints';
import type { Instrument } from '../../api/types';
import type { MlWizardStep } from '../../api/mlBacktestTypes';
import { ML_WIZARD_STEPS } from '../../api/mlBacktestTypes';
import MLBacktestPanel, { type MlWizardBridge } from '../../components/backtesting/MLBacktestPanel';
import FieldLabel from '../../components/FieldLabel';
import InstrumentSearch from '../../components/InstrumentSearch';
import {
  OHLCV_TIMEFRAMES,
  type DateRangeValue,
  defaultDateRangeForTimeframe,
} from '../../constants/timeframes';
import { mlFieldHelp, mlFieldLabel } from '../../utils/mlBacktestHelp';
import { nextWizardStep, prevWizardStep } from '../../utils/mlWizardState';
import { dateRangeFromTrainMetrics } from '../../utils/tradingModels';

const BASE_PATH = '/backtesting/ml';
const ASSET_TYPE_FILTER = ['stock', 'etf'];

export default function MLPage() {
  const { symbol } = useParams<{ symbol?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialEditModelIdRef = useRef(searchParams.get('editModelId') ?? undefined);
  const navigate = useNavigate();
  const [selected, setSelected] = useState<Instrument | null>(null);
  const [decisionTimeframe, setDecisionTimeframe] = useState('1d');
  const [dateRange, setDateRange] = useState<DateRangeValue>(() =>
    defaultDateRangeForTimeframe('1d'),
  );
  const [wizardBridge, setWizardBridge] = useState<MlWizardBridge | null>(null);
  const [navError, setNavError] = useState<string | null>(null);
  const appliedEditContextRef = useRef<string | null>(null);
  const editUrlCleanedRef = useRef(false);

  const wizardStep = wizardBridge?.wizardStep ?? 'universe';

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

  useEffect(() => {
    const editModelId = initialEditModelIdRef.current;
    if (!editModelId || !symbol) return;

    const contextKey = `${symbol}:${editModelId}`;
    if (appliedEditContextRef.current === contextKey) return;

    let cancelled = false;
    mlBacktestApi
      .getSavedModel(editModelId)
      .then((model) => {
        if (cancelled) return;
        if (model.timeframe) {
          setDecisionTimeframe(model.timeframe);
        }
        const range = dateRangeFromTrainMetrics(model.train_metrics);
        if (range) {
          setDateRange(range);
        } else if (model.timeframe) {
          setDateRange(defaultDateRangeForTimeframe(model.timeframe));
        }
        appliedEditContextRef.current = contextKey;
      })
      .catch(() => {
        if (!cancelled) {
          setNavError('Failed to load saved model settings.');
        }
      });

    if (!editUrlCleanedRef.current && searchParams.has('editModelId')) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete('editModelId');
      setSearchParams(nextParams, { replace: true });
      editUrlCleanedRef.current = true;
    }

    return () => {
      cancelled = true;
    };
  }, [symbol, searchParams, setSearchParams]);

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

  const handleNext = () => {
    if (!wizardBridge) {
      return;
    }
    const error = wizardBridge.goNext();
    setNavError(error);
  };

  const handleBack = () => {
    setNavError(null);
    wizardBridge?.goBack();
  };

  const handleStepClick = (step: MlWizardStep) => {
    setNavError(null);
    if (!wizardBridge?.goToStep(step)) {
      setNavError('Complete the current step before jumping ahead.');
    }
  };

  const universeLocked = wizardBridge?.isUniverseLocked ?? false;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-100">ML</h1>
        <p className="text-slate-400 text-sm mt-1">
          Step-by-step ML modeling: data preparation with ALFRED macro timing, label grid search,
          model training, and explainability (ROC, SHAP).
        </p>
      </div>

      <nav className="flex flex-wrap gap-2">
        {ML_WIZARD_STEPS.map((step, index) => {
          const active = wizardStep === step.id;
          const reachable = wizardBridge?.canNavigateToStep(step.id) ?? step.id === 'universe';
          return (
            <button
              key={step.id}
              type="button"
              disabled={!reachable}
              onClick={() => handleStepClick(step.id)}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border disabled:opacity-40 disabled:cursor-not-allowed ${
                active
                  ? 'bg-brand-600 border-brand-500 text-white'
                  : 'bg-surface-900 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {index + 1}. {step.label}
            </button>
          );
        })}
      </nav>

      {!universeLocked && (
        <div className="flex flex-wrap items-end gap-4">
          <InstrumentSearch
            selected={selected}
            onSelect={handleSelect}
            assetTypeFilter={ASSET_TYPE_FILTER}
            placeholder="Search ingested stocks and ETFs"
          />
          <label className="space-y-1 text-sm">
            <FieldLabel
              label={mlFieldLabel('decision_timeframe')}
              help={mlFieldHelp('decision_timeframe')}
              htmlFor="ml-decision-timeframe"
            />
            <select
              id="ml-decision-timeframe"
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
      )}

      {universeLocked && (
        <p className="text-xs text-slate-500">
          Universe controls are locked. Go back to Step 1 to change symbol, timeframe, date range,
          or walk-forward window settings.
        </p>
      )}

      {symbol ? (
        <>
          <MLBacktestPanel
            symbol={symbol}
            dateRange={dateRange}
            onDateRangeChange={setDateRange}
            decisionTimeframe={decisionTimeframe}
            onWizardBridge={setWizardBridge}
            initialEditModelId={initialEditModelIdRef.current}
          />
          <div className="flex justify-between items-center gap-4">
            <button
              type="button"
              disabled={!prevWizardStep(wizardStep)}
              onClick={handleBack}
              className="px-4 py-2 rounded-lg border border-slate-700 text-slate-300 disabled:opacity-40 text-sm"
            >
              Back
            </button>
            <div className="text-right space-y-1">
              {(navError || wizardBridge?.gateError) && (
                <p className="text-xs text-amber-200/80">{navError ?? wizardBridge?.gateError}</p>
              )}
              <button
                type="button"
                disabled={!nextWizardStep(wizardStep)}
                onClick={handleNext}
                className="px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white text-sm"
              >
                Next
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="text-center py-16 text-slate-500 text-sm border border-dashed border-slate-800 rounded-lg">
          Search ingested stocks or ETFs to configure and run an ML backtest.
        </div>
      )}
    </div>
  );
}
