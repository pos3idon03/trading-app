import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { backtestApi, ingestionApi, mlBacktestApi } from '../../../api/endpoints';
import type { Instrument } from '../../../api/types';
import type { MacroSeries } from '../../../api/types';
import type { DateRangeValue } from '../../../constants/timeframes';
import { useMlBacktestJob } from '../../../hooks/useMlBacktestJob';
import { useMlTestingSession } from '../../../hooks/useMlTestingSession';
import { useMlUniverseBarCount } from '../../../hooks/useMlUniverseBarCount';
import {
  getCryptoMlPreset,
  validateMlParams,
  validateWalkForwardParams,
  pickWalkForwardParams,
} from '../../../utils/mlBacktestConfig';
import { buildMlRunRequest } from '../../../utils/mlRunRequest';
import {
  eligibleStrategyFeatureOptions,
  metaLabelBaseStrategyOptions,
} from '../../../utils/mlStrategyFeatures';
import type { StrategyFeatureOption } from '../../../utils/mlStrategyFeatures';
import type { MlTestingConfigSnapshot } from '../../../utils/mlTestingSession';
import ErrorAlert from '../../ErrorAlert';
import Spinner from '../../Spinner';
import MlTestingCompareTable from './MlTestingCompareTable';
import MlTestingConfigPanel from './MlTestingConfigPanel';
import MlTestingRunDetail from './MlTestingRunDetail';
import MlTestingRunsTable from './MlTestingRunsTable';

import { ML_TESTING_HYDRATE_KEY } from '../../../utils/mlTestingSession';

interface MlTestingWorkspaceProps {
  symbol: string;
  instrument: Instrument | null;
  timeframe: string;
  dateRange: DateRangeValue;
}

export default function MlTestingWorkspace({
  symbol,
  instrument,
  timeframe,
  dateRange,
}: MlTestingWorkspaceProps) {
  const navigate = useNavigate();
  const [models, setModels] = useState<Awaited<ReturnType<typeof mlBacktestApi.listModels>>['models']>([]);
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [detailResults, setDetailResults] = useState<Awaited<
    ReturnType<typeof mlBacktestApi.getResults>
  > | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [training, setTraining] = useState(false);
  const [trainMessage, setTrainMessage] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [macroSeries, setMacroSeries] = useState<MacroSeries[]>([]);
  const [ingestedMacroIds, setIngestedMacroIds] = useState<Set<string>>(new Set());
  const [strategyOptions, setStrategyOptions] = useState<StrategyFeatureOption[]>([]);
  const [baseStrategyOptions, setBaseStrategyOptions] = useState<StrategyFeatureOption[]>([]);
  const [loadingStrategies, setLoadingStrategies] = useState(true);
  const [strategyCatalogError, setStrategyCatalogError] = useState<string | null>(null);

  const assetType = instrument?.asset_type ?? 'stock';
  const isCrypto = assetType === 'crypto';

  const defaultModelType = isCrypto ? 'ml_xgboost' : 'ml_gradient_boosting';

  const {
    draftConfig,
    runs,
    setDraftConfig,
    addPendingRun,
    completeRun,
    failRun,
    removeRun,
    starRun,
    loadConfigFromRun,
  } = useMlTestingSession({
    symbol,
    timeframe,
    dateRange,
    modelType: defaultModelType,
    assetType,
  });

  const { running, progress, error, runBacktest, clearError } = useMlBacktestJob();

  const {
    barCount,
    loading: barCountLoading,
    error: barCountError,
  } = useMlUniverseBarCount(symbol, timeframe, dateRange);

  useEffect(() => {
    let cancelled = false;
    ingestionApi
      .listMacroSeries({ ingestedOnly: true, limit: 100 })
      .then((items) => {
        if (!cancelled) setIngestedMacroIds(new Set(items.map((item) => item.series_id)));
      })
      .catch(() => {
        if (!cancelled) setIngestedMacroIds(new Set());
      });
    ingestionApi
      .listMacroSeries()
      .then((items) => {
        if (!cancelled) setMacroSeries(items);
      })
      .catch(() => {
        if (!cancelled) setMacroSeries([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadingStrategies(true);
    backtestApi
      .listStrategies()
      .then((data) => {
        if (!cancelled) {
          setStrategyCatalogError(null);
          setStrategyOptions(eligibleStrategyFeatureOptions(data.strategies));
          setBaseStrategyOptions(metaLabelBaseStrategyOptions(data.strategies));
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setStrategyCatalogError(
            err instanceof Error ? err.message : 'Failed to load strategy catalog.',
          );
          setStrategyOptions([]);
          setBaseStrategyOptions(metaLabelBaseStrategyOptions([]));
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingStrategies(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoadingCatalog(true);
    mlBacktestApi
      .listModels()
      .then((res) => {
        if (!cancelled) setModels(res.models);
      })
      .finally(() => {
        if (!cancelled) setLoadingCatalog(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const cryptoPresetKeyRef = useRef<string | null>(null);
  useEffect(() => {
    if (!draftConfig || !isCrypto) return;
    const key = `${symbol}:${timeframe}`;
    if (cryptoPresetKeyRef.current === key) return;
    cryptoPresetKeyRef.current = key;
    const preset = getCryptoMlPreset(timeframe);
    setDraftConfig({
      ...draftConfig,
      modelType: 'ml_xgboost',
      mlParams: {
        ...preset,
        warmup_bars: draftConfig.mlParams.warmup_bars ?? preset.warmup_bars,
      },
    });
  }, [symbol, isCrypto, timeframe, draftConfig, setDraftConfig]); // draftConfig: apply when session loads

  const draft = useMemo(() => {
    if (!draftConfig) return null;
    return {
      ...draftConfig,
      timeframe,
      dateRange,
    };
  }, [draftConfig, timeframe, dateRange]);

  const validationError = useMemo(() => {
    if (!draft) return 'Loading session…';
    const model = models.find((m) => m.id === draft.modelType);
    const wf = validateWalkForwardParams(pickWalkForwardParams(draft.mlParams), barCount);
    if (wf) return wf;
    return validateMlParams(draft.mlParams, model);
  }, [draft, models, barCount]);

  const handleDraftChange = useCallback(
    (next: MlTestingConfigSnapshot) => {
      setDraftConfig(next);
    },
    [setDraftConfig],
  );

  const handleRun = useCallback(async () => {
    if (!draft || validationError) return;
    clearError();
    const snapshot: MlTestingConfigSnapshot = { ...draft };
    const clientId = addPendingRun(snapshot);
    try {
      const results = await runBacktest({
        symbol,
        modelType: draft.modelType,
        params: draft.mlParams,
        timeframe: draft.timeframe,
        dateRange: draft.dateRange,
        initialCash: draft.initialCash,
        commissionBps: draft.commissionBps,
      });
      completeRun(clientId, results);
      setSelectedClientId(clientId);
      setDetailResults(results);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Backtest failed.';
      failRun(clientId, message);
    }
  }, [
    draft,
    validationError,
    clearError,
    addPendingRun,
    runBacktest,
    symbol,
    completeRun,
    failRun,
  ]);

  const handleSelectRun = useCallback(async (clientId: string) => {
    setSelectedClientId(clientId);
    const run = runs.find((row) => row.clientId === clientId);
    if (!run?.backendRunId) {
      setDetailResults(null);
      return;
    }
    setDetailLoading(true);
    try {
      const full = await mlBacktestApi.getResults(run.backendRunId);
      setDetailResults(full);
    } catch {
      setDetailResults(null);
    } finally {
      setDetailLoading(false);
    }
  }, [runs]);

  const handleTrainAndSave = useCallback(async () => {
    if (!draft || validationError) return;
    setTraining(true);
    setTrainMessage(null);
    try {
      const request = buildMlRunRequest({
        symbol,
        modelType: draft.modelType,
        params: draft.mlParams,
        timeframe: draft.timeframe,
        dateRange: draft.dateRange,
      });
      await mlBacktestApi.train({
        symbol: request.symbol,
        model_type: request.model_type,
        params: request.params,
        timeframe: request.timeframe,
        start: request.start,
        end: request.end,
      });
      setTrainMessage('Model trained and saved. See Backtesting → Trading Models.');
    } catch (err: unknown) {
      setTrainMessage(err instanceof Error ? err.message : 'Training failed.');
    } finally {
      setTraining(false);
    }
  }, [draft, validationError, symbol]);

  const handleOpenInMlWizard = useCallback(() => {
    if (!draft) return;
    sessionStorage.setItem(ML_TESTING_HYDRATE_KEY, JSON.stringify(draft));
    navigate(`/backtesting/ml/${symbol}?fromTesting=1`);
  }, [draft, navigate, symbol]);

  if (loadingCatalog || !draft) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  const selectedRun = runs.find((row) => row.clientId === selectedClientId);

  return (
    <div className="space-y-6">
      {(error || barCountError || strategyCatalogError) && (
        <ErrorAlert message={error ?? barCountError ?? strategyCatalogError ?? ''} />
      )}
      {trainMessage && (
        <p
          className={`text-sm ${trainMessage.includes('failed') ? 'text-red-300' : 'text-emerald-300'}`}
        >
          {trainMessage}
        </p>
      )}

      <MlTestingConfigPanel
        draft={draft}
        models={models}
        assetType={assetType}
        barCount={barCount}
        barCountLoading={barCountLoading}
        validationError={validationError}
        running={running}
        jobProgress={progress}
        onDraftChange={handleDraftChange}
        onRun={() => void handleRun()}
        macroSeries={macroSeries}
        ingestedMacroIds={ingestedMacroIds}
        strategyOptions={strategyOptions}
        baseStrategyOptions={baseStrategyOptions}
        loadingStrategies={loadingStrategies}
        previewLoading={previewLoading}
        onPreview={async () => {
          setPreviewLoading(true);
          try {
            const req = buildMlRunRequest({
              symbol,
              modelType: draft.modelType,
              params: draft.mlParams,
              timeframe,
              dateRange,
            });
            await mlBacktestApi.dataPreview({
              symbol: req.symbol,
              params: req.params,
              timeframe: req.timeframe,
              start: req.start,
              end: req.end,
            });
          } finally {
            setPreviewLoading(false);
          }
        }}
      />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-3">
          <h2 className="text-lg font-semibold text-slate-200">Trial runs</h2>
          <MlTestingRunsTable
            runs={runs}
            selectedClientId={selectedClientId}
            onSelect={(id) => void handleSelectRun(id)}
            onLoadConfig={loadConfigFromRun}
            onDelete={removeRun}
            onToggleStar={starRun}
          />
        </section>

        <section className="rounded-xl border border-slate-800 bg-surface-900 p-4 space-y-3">
          <h2 className="text-lg font-semibold text-slate-200">Compare</h2>
          <MlTestingCompareTable
            runs={runs}
            selectedClientId={selectedClientId}
            onSelect={(id) => void handleSelectRun(id)}
          />
          {selectedRun?.status === 'completed' && (
            <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                disabled={training || !!validationError}
                onClick={() => void handleTrainAndSave()}
                className="text-sm px-3 py-1.5 rounded-lg bg-brand-600 text-white hover:bg-brand-500 disabled:opacity-40"
              >
                {training ? 'Training…' : 'Train & save'}
              </button>
              <button
                type="button"
                onClick={handleOpenInMlWizard}
                className="text-sm px-3 py-1.5 rounded-lg border border-slate-700 text-slate-200 hover:bg-surface-800"
              >
                Open in ML wizard
              </button>
            </div>
          )}
        </section>
      </div>

      <section className="rounded-xl border border-slate-800 bg-surface-900 p-4">
        <h2 className="text-lg font-semibold text-slate-200 mb-3">Run detail</h2>
        <MlTestingRunDetail results={detailResults} loading={detailLoading} />
      </section>
    </div>
  );
}
