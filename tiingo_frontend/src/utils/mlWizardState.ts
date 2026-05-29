import type { DateRangeValue } from '../constants/timeframes';
import type {
  MlDataPreviewResponse,
  MlLabelSearchResult,
  MlModelCatalogItem,
  MlParams,
  MlThresholdSearchResult,
  MlWizardStep,
} from '../api/mlBacktestTypes';
import {
  pickWalkForwardParams,
  validateMlParams,
  validateWalkForwardParams,
} from './mlBacktestConfig';

export const WIZARD_STEP_ORDER: MlWizardStep[] = [
  'universe',
  'data_prep',
  'labeling',
  'model',
  'signals',
  'run',
  'results',
];

export interface MlWizardArtifacts {
  hasDataPreview: boolean;
  hasLabelSearch: boolean;
  hasLabelApplied: boolean;
  hasThresholdSearch: boolean;
  hasThresholdApplied: boolean;
  hasRunResults: boolean;
}

export interface MlLockedConfig {
  symbol?: string;
  decisionTimeframe?: string;
  dateRange?: DateRangeValue;
  mlParams?: MlParams;
  modelType?: string;
  modelLabel?: string;
  initialCash?: number;
  commissionBps?: number;
  runMode?: string;
  /** Bar count from Universe step when walk-forward settings were locked. */
  availableBarCountAtLock?: number | null;
}

export const EMPTY_WIZARD_ARTIFACTS: MlWizardArtifacts = {
  hasDataPreview: false,
  hasLabelSearch: false,
  hasLabelApplied: false,
  hasThresholdSearch: false,
  hasThresholdApplied: false,
  hasRunResults: false,
};

export function mergeWizardArtifacts(
  artifacts: MlWizardArtifacts,
  patch: Partial<MlWizardArtifacts> = {},
): MlWizardArtifacts {
  return { ...artifacts, ...patch };
}

export interface CompleteStepConfigOverride {
  mlParams?: MlParams;
  modelType?: string;
  modelLabel?: string;
}

export interface CompleteStepInput {
  step: MlWizardStep;
  artifacts: MlWizardArtifacts;
  artifactPatch?: Partial<MlWizardArtifacts>;
  symbol: string;
  decisionTimeframe: string;
  dateRange: DateRangeValue;
  mlParams: MlParams;
  modelType: string;
  modelLabel?: string;
  selectedModel?: MlModelCatalogItem;
  runMode: string;
  initialCash: number;
  commissionBps: number;
  configOverride?: CompleteStepConfigOverride;
  availableBarCount?: number | null;
}

export function buildWizardStepSnapshot(
  step: MlWizardStep,
  config: {
    symbol: string;
    decisionTimeframe: string;
    dateRange: DateRangeValue;
    mlParams: MlParams;
    modelType: string;
    modelLabel?: string;
    runMode: string;
    initialCash: number;
    commissionBps: number;
    availableBarCount?: number | null;
  },
): MlLockedConfig {
  switch (step) {
    case 'universe':
      return {
        symbol: config.symbol,
        decisionTimeframe: config.decisionTimeframe,
        dateRange: config.dateRange,
        mlParams: pickWalkForwardParams(config.mlParams),
        availableBarCountAtLock: config.availableBarCount ?? null,
      };
    case 'data_prep':
      return { mlParams: { ...config.mlParams } };
    case 'labeling':
      return {
        mlParams: { ...config.mlParams },
        modelType: config.modelType,
        modelLabel: config.modelLabel,
      };
    case 'model':
      return {
        mlParams: { ...config.mlParams },
        modelType: config.modelType,
        modelLabel: config.modelLabel,
        runMode: config.runMode,
      };
    case 'signals':
      return { mlParams: { ...config.mlParams } };
    case 'run':
      return { initialCash: config.initialCash, commissionBps: config.commissionBps };
    default:
      return {};
  }
}

export function resolveCompleteStepAdvance(
  input: CompleteStepInput,
):
  | { error: string }
  | {
      error: null;
      nextStep: MlWizardStep | null;
      mergedArtifacts: MlWizardArtifacts;
      snapshot: MlLockedConfig;
    } {
  const mergedArtifacts = mergeWizardArtifacts(input.artifacts, input.artifactPatch);
  const mergedParams = input.configOverride?.mlParams ?? input.mlParams;
  const mergedModelType = input.configOverride?.modelType ?? input.modelType;
  const mergedModelLabel = input.configOverride?.modelLabel ?? input.modelLabel;

  const error = validateWizardStepGate(
    input.step,
    mergedParams,
    input.selectedModel,
    input.symbol,
    mergedArtifacts,
    input.availableBarCount,
  );
  if (error) {
    return { error };
  }

  const snapshot = buildWizardStepSnapshot(input.step, {
    symbol: input.symbol,
    decisionTimeframe: input.decisionTimeframe,
    dateRange: input.dateRange,
    mlParams: mergedParams,
    modelType: mergedModelType,
    modelLabel: mergedModelLabel,
    runMode: input.runMode,
    initialCash: input.initialCash,
    commissionBps: input.commissionBps,
    availableBarCount: input.availableBarCount,
  });

  return {
    error: null,
    nextStep: nextWizardStep(input.step),
    mergedArtifacts,
    snapshot,
  };
}

export function wizardStepIndex(step: MlWizardStep): number {
  return WIZARD_STEP_ORDER.indexOf(step);
}

export function nextWizardStep(step: MlWizardStep): MlWizardStep | null {
  const index = wizardStepIndex(step);
  return index >= 0 && index < WIZARD_STEP_ORDER.length - 1
    ? WIZARD_STEP_ORDER[index + 1]
    : null;
}

export function prevWizardStep(step: MlWizardStep): MlWizardStep | null {
  const index = wizardStepIndex(step);
  return index > 0 ? WIZARD_STEP_ORDER[index - 1] : null;
}

export function downstreamSteps(fromStep: MlWizardStep): MlWizardStep[] {
  const index = wizardStepIndex(fromStep);
  if (index < 0) {
    return [];
  }
  return WIZARD_STEP_ORDER.slice(index + 1);
}

export function validateWizardStepGate(
  step: MlWizardStep,
  params: MlParams,
  model: MlModelCatalogItem | undefined,
  symbol: string,
  artifacts: MlWizardArtifacts,
  availableBarCount?: number | null,
): string | null {
  if (!symbol) {
    return 'Select a symbol first.';
  }

  switch (step) {
    case 'universe':
      return validateWalkForwardParams(pickWalkForwardParams(params), availableBarCount);
    case 'data_prep':
      if (params.feature_mode !== 'prices_only' && !params.macro_series_ids?.length) {
        return 'Select macro series or switch to prices-only mode.';
      }
      if (!artifacts.hasDataPreview) {
        return 'Run data preview before continuing.';
      }
      return validateMlParams(params, model);
    case 'labeling':
      if (params.label_mode === 'ternary' && (params.label_threshold ?? 0) <= 0) {
        return 'Ternary labels require a positive threshold.';
      }
      if (!artifacts.hasLabelSearch) {
        return 'Run label grid search before continuing.';
      }
      if (!artifacts.hasLabelApplied) {
        return 'Apply a label search result before continuing.';
      }
      return null;
    case 'model':
      return validateMlParams(params, model);
    case 'signals':
      if (!artifacts.hasThresholdApplied) {
        return 'Apply a threshold result or confirm current thresholds.';
      }
      return validateMlParams(params, model);
    case 'run':
      return validateMlParams(params, model);
    case 'results':
      if (!artifacts.hasRunResults) {
        return 'Run a backtest before viewing results.';
      }
      return null;
    default:
      return null;
  }
}

export function canNavigateToWizardStep(
  target: MlWizardStep,
  current: MlWizardStep,
  completedSteps: Set<MlWizardStep>,
  gateError: string | null,
): boolean {
  const targetIndex = wizardStepIndex(target);
  const currentIndex = wizardStepIndex(current);
  if (targetIndex <= currentIndex) {
    return true;
  }
  if (targetIndex === currentIndex + 1 && !gateError) {
    return true;
  }
  return completedSteps.has(target);
}

export function isStepFieldLocked(
  step: MlWizardStep,
  fieldGroup: 'universe' | 'data_prep' | 'labeling' | 'model' | 'signals' | 'run',
): boolean {
  const currentIndex = wizardStepIndex(step);
  const groupIndex = wizardStepIndex(
    fieldGroup === 'universe'
      ? 'universe'
      : fieldGroup === 'data_prep'
        ? 'data_prep'
        : fieldGroup === 'labeling'
          ? 'labeling'
          : fieldGroup === 'model'
            ? 'model'
            : fieldGroup === 'signals'
              ? 'signals'
              : 'run',
  );
  return currentIndex > groupIndex;
}

export type MlWizardCachedResults = {
  dataPreview?: MlDataPreviewResponse | null;
  labelSearch?: MlLabelSearchResult[];
  thresholdSearch?: MlThresholdSearchResult[];
};
