import { describe, expect, it } from 'vitest';
import { DEFAULT_ML_PARAMS } from '../utils/mlBacktestConfig';
import {
  EMPTY_WIZARD_ARTIFACTS,
  canNavigateToWizardStep,
  mergeWizardArtifacts,
  resolveCompleteStepAdvance,
  validateWizardStepGate,
} from '../utils/mlWizardState';
import { buildLabelSearchGate } from '../utils/mlLabelSearchMatrix';
const FULL_COVERAGE_GATE = buildLabelSearchGate(
  { ml_logistic: { enabled: true, labelMode: 'binary' }, ml_lstm: { enabled: true, labelMode: 'meta_label' } },
  [
    {
      label_key: 'a',
      model_type: 'ml_logistic',
      label_mode: 'binary',
      label_horizon: 5,
      oos_window_count: 1,
      class_distribution: {},
    },
    {
      label_key: 'b',
      model_type: 'ml_lstm',
      label_mode: 'meta_label',
      label_horizon: 5,
      oos_window_count: 1,
      class_distribution: {},
    },
  ],
);

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
  it('validates walk-forward params on universe step', () => {
    const error = validateWizardStepGate(
      'universe',
      { ...DEFAULT_ML_PARAMS, train_bars: 9 },
      undefined,
      'AAPL',
      EMPTY_WIZARD_ARTIFACTS,
    );
    expect(error).toMatch(/train bars/i);
  });

  it('blocks universe when date range has insufficient bars', () => {
    const error = validateWizardStepGate(
      'universe',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      EMPTY_WIZARD_ARTIFACTS,
      100,
    );
    expect(error).toMatch(/bars/i);
  });

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

  it('requires at least one enabled model for labeling', () => {
    const error = validateWizardStepGate(
      'labeling',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      EMPTY_WIZARD_ARTIFACTS,
      undefined,
      { enabledModelIds: [], coverageComplete: false },
    );
    expect(error).toMatch(/at least one model/i);
  });

  it('requires grid search coverage for all selected models', () => {
    const error = validateWizardStepGate(
      'labeling',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      { ...EMPTY_WIZARD_ARTIFACTS, hasLabelSearch: true },
      undefined,
      buildLabelSearchGate(
        { ml_logistic: { enabled: true, labelMode: 'binary' } },
        [],
      ),
    );
    expect(error).toMatch(/all selected models/i);
  });

  it('requires label apply before leaving labeling', () => {
    const error = validateWizardStepGate(
      'labeling',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      { ...EMPTY_WIZARD_ARTIFACTS, hasLabelSearch: true },
      undefined,
      FULL_COVERAGE_GATE,
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
      undefined,
      FULL_COVERAGE_GATE,
    );
    expect(error).toBeNull();
  });

  it('requires threshold confirmation on signals step', () => {
    const error = validateWizardStepGate(
      'signals',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      EMPTY_WIZARD_ARTIFACTS,
    );
    expect(error).toMatch(/threshold/i);
  });

  it('allows leaving signals without threshold sweep when applied', () => {
    const error = validateWizardStepGate(
      'signals',
      DEFAULT_ML_PARAMS,
      undefined,
      'AAPL',
      { ...EMPTY_WIZARD_ARTIFACTS, hasThresholdApplied: true },
    );
    expect(error).toBeNull();
  });
});

describe('resolveCompleteStepAdvance', () => {
  it('snapshots walk-forward params when completing universe', () => {
    const result = resolveCompleteStepAdvance({
      step: 'universe',
      artifacts: EMPTY_WIZARD_ARTIFACTS,
      ...BASE_COMPLETE_INPUT,
      mlParams: {
        ...DEFAULT_ML_PARAMS,
        train_bars: 10,
        test_bars: 20,
        step_bars: 20,
        label_horizon: 2,
      },
      availableBarCount: 200,
    });

    expect(result.error).toBeNull();
    if (result.error !== null) {
      return;
    }
    expect(result.snapshot.mlParams?.train_bars).toBe(10);
    expect(result.snapshot.mlParams?.test_bars).toBe(20);
    expect(result.snapshot.mlParams?.label_horizon).toBe(2);
    expect(result.snapshot.availableBarCountAtLock).toBe(200);
  });

  it('advances labeling to model when apply patch is provided', () => {
    const result = resolveCompleteStepAdvance({
      step: 'labeling',
      artifacts: {
        ...EMPTY_WIZARD_ARTIFACTS,
        hasLabelSearch: true,
        hasLabelApplied: true,
      },
      artifactPatch: { hasLabelApplied: true },
      labelSearchGate: FULL_COVERAGE_GATE,
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
      labelSearchGate: FULL_COVERAGE_GATE,
      ...BASE_COMPLETE_INPUT,
    });

    expect(result.error).toMatch(/apply/i);
  });

  it('blocks labeling advance when labelSearchGate is omitted', () => {
    const result = resolveCompleteStepAdvance({
      step: 'labeling',
      artifacts: {
        ...EMPTY_WIZARD_ARTIFACTS,
        hasLabelSearch: true,
        hasLabelApplied: true,
      },
      artifactPatch: { hasLabelApplied: true },
      ...BASE_COMPLETE_INPUT,
    });

    expect(result.error).toMatch(/model/i);
  });

  it('advances signals to run when threshold patch is provided', () => {
    const result = resolveCompleteStepAdvance({
      step: 'signals',
      artifacts: EMPTY_WIZARD_ARTIFACTS,
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
