import type {
  MlLabelMode,
  MlLabelSearchResult,
  MlModelCatalogItem,
  MlModelLabelSearchConfig,
} from '../api/mlBacktestTypes';
import { DEFAULT_LABEL_MODE_BY_MODEL } from './mlBacktestConfig';

export interface LabelSearchMatrixRow {
  enabled: boolean;
  labelMode: MlLabelMode;
}

export type LabelSearchMatrixState = Record<string, LabelSearchMatrixRow>;

export const LABEL_MODE_DEFAULT_HINTS: Record<MlLabelMode, string> = {
  binary: 'Directional sign targets (Gu, Kelly & Xiu, 2020)',
  ternary: 'Neutral band reduces noise (López de Prado, AFML Ch. 3)',
  meta_label: 'ML gate on strategy events (López de Prado, AFML Ch. 3)',
};

export function defaultLabelModeForModel(modelId: string): MlLabelMode {
  const mode = DEFAULT_LABEL_MODE_BY_MODEL[modelId];
  if (mode === 'meta_label' || mode === 'ternary') {
    return mode;
  }
  return 'binary';
}

export function buildDefaultLabelSearchMatrix(
  models: MlModelCatalogItem[],
): LabelSearchMatrixState {
  const state: LabelSearchMatrixState = {};
  for (const model of models) {
    state[model.id] = {
      enabled: true,
      labelMode: defaultLabelModeForModel(model.id),
    };
  }
  return state;
}

export function enabledLabelSearchConfigs(
  matrix: LabelSearchMatrixState,
): MlModelLabelSearchConfig[] {
  return Object.entries(matrix)
    .filter(([, row]) => row.enabled)
    .map(([modelType, row]) => ({
      model_type: modelType,
      label_mode: row.labelMode,
    }));
}

export function enabledLabelSearchModelIds(matrix: LabelSearchMatrixState): string[] {
  return Object.entries(matrix)
    .filter(([, row]) => row.enabled)
    .map(([modelId]) => modelId);
}

export function isLabelSearchCoverageComplete(
  matrix: LabelSearchMatrixState,
  results: MlLabelSearchResult[],
): boolean {
  const enabled = enabledLabelSearchModelIds(matrix);
  if (enabled.length === 0) {
    return false;
  }
  return enabled.every((modelId) => {
    const row = matrix[modelId];
    if (!row?.enabled) {
      return true;
    }
    return results.some(
      (entry) =>
        entry.model_type === modelId && entry.label_mode === row.labelMode,
    );
  });
}

export interface LabelSearchGateContext {
  enabledModelIds: string[];
  coverageComplete: boolean;
}

export function buildLabelSearchGate(
  matrix: LabelSearchMatrixState,
  results: MlLabelSearchResult[],
): LabelSearchGateContext {
  return {
    enabledModelIds: enabledLabelSearchModelIds(matrix),
    coverageComplete: isLabelSearchCoverageComplete(matrix, results),
  };
}

export function maxLabelTailBars(
  matrix: LabelSearchMatrixState,
  labelHorizon: number,
  maxHorizonBars: number,
): { labelMode: MlLabelMode; tailBars: number } {
  let tailBars = labelHorizon;
  let dominantMode: MlLabelMode = 'binary';
  for (const row of Object.values(matrix)) {
    if (!row.enabled) {
      continue;
    }
    const tail = row.labelMode === 'meta_label' ? maxHorizonBars : labelHorizon;
    if (tail > tailBars) {
      tailBars = tail;
      dominantMode = row.labelMode;
    }
  }
  return { labelMode: dominantMode, tailBars };
}
