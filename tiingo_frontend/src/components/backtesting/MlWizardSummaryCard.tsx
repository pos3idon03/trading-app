import type { MlDataPreviewResponse, MlWalkForwardReadiness } from '../../api/mlBacktestTypes';
import type { MlLockedConfig } from '../../utils/mlWizardState';
import { ML_FEATURE_MODES, minimumBarsRequired } from '../../utils/mlBacktestConfig';
import { formatMlDateRangeLabel } from '../../utils/mlUniverseBudget';

interface MlWizardSummaryCardProps {
  symbol: string;
  decisionTimeframe: string;
  lockedConfig: MlLockedConfig;
  modelLabel?: string;
  dataPreview?: MlDataPreviewResponse | null;
}

function featureModeLabel(value?: string): string {
  return ML_FEATURE_MODES.find((item) => item.value === value)?.label ?? value ?? '—';
}

function formatOptionalList(items: string[] | undefined): string | null {
  if (!items?.length) {
    return null;
  }
  return items.join(', ');
}

function readinessSummary(readiness: MlWalkForwardReadiness | undefined): string | null {
  if (!readiness || readiness.total_bars === 0) {
    return null;
  }
  return `${readiness.viable_folds} viable / ${readiness.structural_folds} structural folds`;
}

export default function MlWizardSummaryCard({
  symbol,
  decisionTimeframe,
  lockedConfig,
  modelLabel,
  dataPreview,
}: MlWizardSummaryCardProps) {
  const params = lockedConfig.mlParams;
  const lockedMinimum =
    params != null ? minimumBarsRequired(params) : null;
  const previewBars = dataPreview?.walk_forward_readiness?.total_bars;
  const lockedBars = lockedConfig.availableBarCountAtLock;
  const resolvedModel = modelLabel ?? lockedConfig.modelLabel ?? lockedConfig.modelType ?? '—';
  const contextTimeframes =
    formatOptionalList(params?.context_timeframes) ??
    formatOptionalList(dataPreview?.context_timeframes);
  const strategyFeatures =
    formatOptionalList(params?.strategy_feature_ids) ??
    formatOptionalList(dataPreview?.strategy_feature_ids);

  return (
    <section className="rounded-xl border border-slate-800 bg-surface-950/60 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
        Locked configuration
      </h3>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div>
          <dt className="text-slate-500 text-xs">Symbol</dt>
          <dd className="text-slate-100">
            {symbol || '—'}
            {params?.label_mode === 'meta_label' && (
              <span className="ml-2 text-[10px] uppercase text-emerald-400">Crypto meta-label</span>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 text-xs">Timeframe</dt>
          <dd className="text-slate-100">{decisionTimeframe}</dd>
        </div>
        {lockedConfig.dateRange && (
          <div>
            <dt className="text-slate-500 text-xs">Simulation period</dt>
            <dd className="text-slate-100">
              {formatMlDateRangeLabel(lockedConfig.dateRange)}
            </dd>
          </div>
        )}
        {(lockedBars != null || previewBars != null || lockedMinimum != null) && (
          <div>
            <dt className="text-slate-500 text-xs">Bars (Universe / preview)</dt>
            <dd className="text-slate-100">
              {lockedBars != null ? lockedBars.toLocaleString() : '—'}
              {previewBars != null && previewBars !== lockedBars
                ? ` → ${previewBars.toLocaleString()} in preview`
                : previewBars != null && lockedBars == null
                  ? previewBars.toLocaleString()
                  : ''}
              {lockedMinimum != null ? ` · min ${lockedMinimum}` : ''}
            </dd>
          </div>
        )}
        {params?.feature_mode && (
          <div>
            <dt className="text-slate-500 text-xs">Feature mode</dt>
            <dd className="text-slate-100">{featureModeLabel(params.feature_mode)}</dd>
          </div>
        )}
        {params?.include_news_sentiment && (
          <div>
            <dt className="text-slate-500 text-xs">News sentiment</dt>
            <dd className="text-slate-100">Enabled</dd>
          </div>
        )}
        {lockedConfig.modelType && (
          <div>
            <dt className="text-slate-500 text-xs">Model</dt>
            <dd className="text-slate-100">{resolvedModel}</dd>
          </div>
        )}
        {params?.train_bars != null && (
          <div>
            <dt className="text-slate-500 text-xs">Train bars</dt>
            <dd className="text-slate-100">{params.train_bars}</dd>
          </div>
        )}
        {params?.test_bars != null && (
          <div>
            <dt className="text-slate-500 text-xs">Test bars</dt>
            <dd className="text-slate-100">{params.test_bars}</dd>
          </div>
        )}
        {params?.step_bars != null && (
          <div>
            <dt className="text-slate-500 text-xs">Step bars</dt>
            <dd className="text-slate-100">{params.step_bars}</dd>
          </div>
        )}
        {params?.label_horizon != null && (
          <div>
            <dt className="text-slate-500 text-xs">Label horizon</dt>
            <dd className="text-slate-100">{params.label_horizon} bars</dd>
          </div>
        )}
        {contextTimeframes && (
          <div>
            <dt className="text-slate-500 text-xs">Context timeframes</dt>
            <dd className="text-slate-100">{contextTimeframes}</dd>
          </div>
        )}
        {strategyFeatures && (
          <div>
            <dt className="text-slate-500 text-xs">Strategy features</dt>
            <dd className="text-slate-100">{strategyFeatures}</dd>
          </div>
        )}
        {readinessSummary(dataPreview?.walk_forward_readiness) && (
          <div>
            <dt className="text-slate-500 text-xs">Walk-forward readiness</dt>
            <dd className="text-slate-100">
              {readinessSummary(dataPreview?.walk_forward_readiness)}
            </dd>
          </div>
        )}
        {params?.buy_threshold != null && params?.sell_threshold != null && (
          <div>
            <dt className="text-slate-500 text-xs">Thresholds</dt>
            <dd className="text-slate-100">
              buy {params.buy_threshold} / sell {params.sell_threshold}
            </dd>
          </div>
        )}
      </dl>
    </section>
  );
}
