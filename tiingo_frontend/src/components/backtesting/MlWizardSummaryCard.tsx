import type { MlLockedConfig } from '../../utils/mlWizardState';
import { ML_FEATURE_MODES } from '../../utils/mlBacktestConfig';

interface MlWizardSummaryCardProps {
  symbol: string;
  decisionTimeframe: string;
  lockedConfig: MlLockedConfig;
  modelLabel?: string;
}

function featureModeLabel(value?: string): string {
  return ML_FEATURE_MODES.find((item) => item.value === value)?.label ?? value ?? '—';
}

export default function MlWizardSummaryCard({
  symbol,
  decisionTimeframe,
  lockedConfig,
  modelLabel,
}: MlWizardSummaryCardProps) {
  const params = lockedConfig.mlParams;
  const resolvedModel = modelLabel ?? lockedConfig.modelLabel ?? lockedConfig.modelType ?? '—';

  return (
    <section className="rounded-xl border border-slate-800 bg-surface-950/60 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-3">
        Locked configuration
      </h3>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <div>
          <dt className="text-slate-500 text-xs">Symbol</dt>
          <dd className="text-slate-100">{symbol || '—'}</dd>
        </div>
        <div>
          <dt className="text-slate-500 text-xs">Timeframe</dt>
          <dd className="text-slate-100">{decisionTimeframe}</dd>
        </div>
        {params?.feature_mode && (
          <div>
            <dt className="text-slate-500 text-xs">Feature mode</dt>
            <dd className="text-slate-100">{featureModeLabel(params.feature_mode)}</dd>
          </div>
        )}
        {lockedConfig.modelType && (
          <div>
            <dt className="text-slate-500 text-xs">Model</dt>
            <dd className="text-slate-100">{resolvedModel}</dd>
          </div>
        )}
        {params?.label_horizon != null && (
          <div>
            <dt className="text-slate-500 text-xs">Label horizon</dt>
            <dd className="text-slate-100">{params.label_horizon} bars</dd>
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
