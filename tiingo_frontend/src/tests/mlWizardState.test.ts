import { describe, expect, it } from 'vitest';
import { DEFAULT_ML_PARAMS } from '../utils/mlBacktestConfig';
import {
  EMPTY_WIZARD_ARTIFACTS,
  canNavigateToWizardStep,
  mergeWizardArtifacts,
  resolveCompleteStepAdvance,
  validateWizardStepGate,
} from '../utils/mlWizardState';

const BASE_COMPLETE_INPUT = {
  symbol: 'AAPL',
  decisionTimeframe: '1d',
  dateRange: { preset: '1Y' as const },
  mlParams: DEFAULT_ML_PARAMS,
  modelType: 'ml_logistic',
  modelLabel: 'Logistic Regression',
  runMode: 'walk_forward',
  initialCash: 10_000,
  commissionBps: 0,
};

describe('validateWizardStepGate', () => {
  it('requires data preview before leaving data prep', () => {
    const error = validateWizardStepGate(
      'data_prep',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      EMPTY_WIZARD_ARTIFACTS,
    );
    expect(error).toMatch(/data preview/i);
  });

  it('requires label apply before leaving labeling', () => {
    const error = validateWizardStepGate(
      'labeling',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      { ...EMPTY_WIZARD_ARTIFACTS, hasLabelSearch: true },
    );
    expect(error).toMatch(/apply/i);
  });

  it('allows leaving labeling when apply patch is merged', () => {
    const merged = mergeWizardArtifacts(EMPTY_WIZARD_ARTIFACTS, {
      hasLabelSearch: true,
      hasLabelApplied: true,
    });
    const error = validateWizardStepGate(
      'labeling',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      merged,
    );
    expect(error).toBeNull();
  });

  it('requires threshold confirmation on signals step', () => {
    const error = validateWizardStepGate(
      'signals',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      { ...EMPTY_WIZARD_ARTIFACTS, hasThresholdSearch: true },
    );
    expect(error).toMatch(/threshold/i);
  });
});

describe('resolveCompleteStepAdvance', () => {
  it('advances labeling to model when apply patch is provided', () => {
    const result = resolveCompleteStepAdvance({
      step: 'labeling',
      artifacts: { ...EMPTY_WIZARD_ARTIFACTS, hasLabelSearch: true },
      artifactPatch: { hasLabelApplied: true },
      configOverride: {
        modelType: 'ml_random_forest',
        modelLabel: 'Random Forest',
        mlParams: { ...DEFAULT_ML_PARAMS, label_horizon: 2 },
      },
      ...BASE_COMPLETE_INPUT,
    });

    expect(result.error).toBeNull();
    if (result.error !== null) {
      return;
    }
    expect(result.nextStep).toBe('model');
    expect(result.mergedArtifacts.hasLabelApplied).toBe(true);
    expect(result.snapshot.modelType).toBe('ml_random_forest');
    expect(result.snapshot.mlParams?.label_horizon).toBe(2);
  });

  it('blocks labeling advance without apply patch', () => {
    const result = resolveCompleteStepAdvance({
      step: 'labeling',
      artifacts: { ...EMPTY_WIZARD_ARTIFACTS, hasLabelSearch: true },
      ...BASE_COMPLETE_INPUT,
    });

    expect(result.error).toMatch(/apply/i);
  });

  it('advances signals to run when threshold patch is provided', () => {
    const result = resolveCompleteStepAdvance({
      step: 'signals',
      artifacts: { ...EMPTY_WIZARD_ARTIFACTS, hasThresholdSearch: true },
      artifactPatch: { hasThresholdApplied: true },
      configOverride: {
        mlParams: { ...DEFAULT_ML_PARAMS, buy_threshold: 0.55 },
      },
      ...BASE_COMPLETE_INPUT,
    });

    expect(result.error).toBeNull();
    if (result.error !== null) {
      return;
    }
    expect(result.nextStep).toBe('run');
    expect(result.snapshot.mlParams?.buy_threshold).toBe(0.55);
  });
});

describe('canNavigateToWizardStep', () => {
  it('allows jumping back to completed steps', () => {
    const completed = new Set<'data_prep' | 'universe'>(['universe', 'data_prep']);
    expect(
      canNavigateToWizardStep('universe', 'labeling', completed, null),
    ).toBe(true);
  });

  it('blocks jumping ahead when gate fails', () => {
    expect(
      canNavigateToWizardStep(
        'results',
        'data_prep',
        new Set(),
        'Run data preview before continuing.',
      ),
    ).toBe(false);
  });
});
