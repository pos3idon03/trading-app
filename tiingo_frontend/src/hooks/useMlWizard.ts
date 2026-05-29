import { useCallback, useMemo, useState } from 'react';
import type { DateRangeValue } from '../constants/timeframes';
import type {
  MlLabelSearchResult,
  MlModelCatalogItem,
  MlParams,
  MlThresholdSearchResult,
  MlWizardStep,
} from '../api/mlBacktestTypes';
import {
  EMPTY_WIZARD_ARTIFACTS,
  downstreamSteps,
  type CompleteStepConfigOverride,
  type MlLockedConfig,
  type MlWizardArtifacts,
  nextWizardStep,
  prevWizardStep,
  resolveCompleteStepAdvance,
  validateWizardStepGate,
  canNavigateToWizardStep,
  wizardStepIndex,
} from '../utils/mlWizardState';
import { pickWalkForwardParams } from '../utils/mlBacktestConfig';

interface UseMlWizardOptions {
  symbol: string;
  decisionTimeframe: string;
  dateRange: DateRangeValue;
  mlParams: MlParams;
  modelType: string;
  modelLabel?: string;
  selectedModel?: MlModelCatalogItem;
  initialCash: number;
  commissionBps: number;
  runMode: string;
  availableBarCount?: number | null;
}

export function useMlWizard(options: UseMlWizardOptions) {
  const {
    symbol,
    decisionTimeframe,
    dateRange,
    mlParams,
    modelType,
    modelLabel,
    selectedModel,
    initialCash,
    commissionBps,
    runMode,
    availableBarCount,
  } = options;

  const [wizardStep, setWizardStep] = useState<MlWizardStep>('universe');
  const [completedSteps, setCompletedSteps] = useState<Set<MlWizardStep>>(new Set());
  const [artifacts, setArtifacts] = useState<MlWizardArtifacts>(EMPTY_WIZARD_ARTIFACTS);
  const [lockedConfig, setLockedConfig] = useState<MlLockedConfig>({});

  const gateError = useMemo(
    () =>
      validateWizardStepGate(
        wizardStep,
        mlParams,
        selectedModel,
        symbol,
        artifacts,
        availableBarCount,
      ),
    [wizardStep, mlParams, selectedModel, symbol, artifacts, availableBarCount],
  );

  const invalidateFromStep = useCallback((step: MlWizardStep) => {
    const downstream = downstreamSteps(step);
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      for (const downstreamStep of downstream) {
        next.delete(downstreamStep);
      }
      next.delete(step);
      return next;
    });
    setArtifacts((prev) => {
      const next = { ...prev };
      if (downstream.includes('data_prep')) {
        next.hasDataPreview = false;
      }
      if (downstream.includes('labeling')) {
        next.hasLabelSearch = false;
        next.hasLabelApplied = false;
      }
      if (downstream.includes('model')) {
        /* model step has no exclusive artifact */
      }
      if (downstream.includes('signals')) {
        next.hasThresholdSearch = false;
        next.hasThresholdApplied = false;
      }
      if (downstream.includes('results')) {
        next.hasRunResults = false;
      }
      return next;
    });
  }, []);

  const buildCompleteStepInput = useCallback(
    (
      artifactPatch?: Partial<MlWizardArtifacts>,
      configOverride?: CompleteStepConfigOverride,
    ) => ({
      step: wizardStep,
      artifacts,
      artifactPatch,
      symbol,
      decisionTimeframe,
      dateRange,
      mlParams,
      modelType,
      modelLabel,
      selectedModel,
      runMode,
      initialCash,
      commissionBps,
      configOverride,
      availableBarCount,
    }),
    [
      wizardStep,
      artifacts,
      symbol,
      decisionTimeframe,
      dateRange,
      mlParams,
      modelType,
      modelLabel,
      selectedModel,
      runMode,
      initialCash,
      commissionBps,
      availableBarCount,
    ],
  );

  const completeStepAndAdvance = useCallback(
    (
      artifactPatch?: Partial<MlWizardArtifacts>,
      configOverride?: CompleteStepConfigOverride,
    ): string | null => {
      const result = resolveCompleteStepAdvance(
        buildCompleteStepInput(artifactPatch, configOverride),
      );
      if (result.error) {
        return result.error;
      }
      setArtifacts(result.mergedArtifacts);
      setLockedConfig((prev) => ({ ...prev, ...result.snapshot }));
      setCompletedSteps((prev) => new Set(prev).add(wizardStep));
      if (result.nextStep) {
        setWizardStep(result.nextStep);
      }
      return null;
    },
    [buildCompleteStepInput, wizardStep],
  );

  const snapshotStep = useCallback(
    (step: MlWizardStep): MlLockedConfig => {
      switch (step) {
        case 'universe':
          return {
            symbol,
            decisionTimeframe,
            dateRange,
            mlParams: pickWalkForwardParams(mlParams),
            availableBarCountAtLock: availableBarCount ?? null,
          };
        case 'data_prep':
          return { mlParams: { ...mlParams } };
        case 'labeling':
          return {
            mlParams: { ...mlParams },
            modelType,
            modelLabel,
          };
        case 'model':
          return {
            mlParams: { ...mlParams },
            modelType,
            modelLabel,
            runMode,
          };
        case 'signals':
          return { mlParams: { ...mlParams } };
        case 'run':
          return { initialCash, commissionBps };
        default:
          return {};
      }
    },
    [
      symbol,
      decisionTimeframe,
      dateRange,
      mlParams,
      modelType,
      modelLabel,
      runMode,
      initialCash,
      commissionBps,
      availableBarCount,
    ],
  );

  const goNext = useCallback(() => {
    if (gateError) {
      return gateError;
    }
    const snapshot = snapshotStep(wizardStep);
    setLockedConfig((prev) => ({ ...prev, ...snapshot }));
    setCompletedSteps((prev) => new Set(prev).add(wizardStep));
    const next = nextWizardStep(wizardStep);
    if (next) {
      setWizardStep(next);
    }
    return null;
  }, [gateError, snapshotStep, wizardStep]);

  const goBack = useCallback(() => {
    const prev = prevWizardStep(wizardStep);
    if (!prev) {
      return;
    }
    invalidateFromStep(prev);
    setWizardStep(prev);
  }, [invalidateFromStep, wizardStep]);

  const goToStep = useCallback(
    (target: MlWizardStep) => {
      const allowed = canNavigateToWizardStep(target, wizardStep, completedSteps, gateError);
      if (!allowed) {
        return false;
      }
      if (wizardStepIndex(target) < wizardStepIndex(wizardStep)) {
        invalidateFromStep(target);
      }
      setWizardStep(target);
      return true;
    },
    [completedSteps, gateError, invalidateFromStep, wizardStep],
  );

  const setArtifact = useCallback(
    (patch: Partial<MlWizardArtifacts>) => {
      setArtifacts((prev) => ({ ...prev, ...patch }));
    },
    [],
  );

  const isUniverseLocked = wizardStepIndex(wizardStep) > wizardStepIndex('universe');
  const isDataPrepLocked = wizardStepIndex(wizardStep) > wizardStepIndex('data_prep');
  const isLabelingLocked = wizardStepIndex(wizardStep) > wizardStepIndex('labeling');
  const isModelLocked = wizardStepIndex(wizardStep) > wizardStepIndex('model');
  const isSignalsLocked = wizardStepIndex(wizardStep) > wizardStepIndex('signals');

  return {
    wizardStep,
    setWizardStep,
    completedSteps,
    artifacts,
    setArtifact,
    lockedConfig,
    gateError,
    goNext,
    goBack,
    goToStep,
    completeStepAndAdvance,
    invalidateFromStep,
    isUniverseLocked,
    isDataPrepLocked,
    isLabelingLocked,
    isModelLocked,
    isSignalsLocked,
  };
}

export type MlWizardControl = ReturnType<typeof useMlWizard>;

export type { MlLabelSearchResult, MlThresholdSearchResult };
