import type { MlSummary } from '../../api/mlBacktestTypes';
import {
  buildEvaluationScopeNotice,
  collectMlDataWarnings,
} from '../../utils/mlBacktestEvaluation';

interface MlEvaluationScopeBannerProps {
  summary?: MlSummary | null;
  commissionBps?: number | null;
}

export default function MlEvaluationScopeBanner({
  summary,
  commissionBps,
}: MlEvaluationScopeBannerProps) {
  const notice = buildEvaluationScopeNotice(summary);
  const dataWarnings = collectMlDataWarnings(summary);
  if (!notice && dataWarnings.length === 0) {
    return null;
  }

  const toneClass =
    notice?.tone === 'warning'
      ? 'border-amber-700/50 bg-amber-950/30 text-amber-100'
      : 'border-sky-700/50 bg-sky-950/30 text-sky-100';

  return (
    <div className="space-y-2">
      {notice && (
        <div className={`rounded-lg border px-3 py-2 text-sm ${toneClass}`}>
          <p className="font-medium">{notice.title}</p>
          <p className="mt-1 text-xs opacity-90">{notice.message}</p>
          {typeof commissionBps === 'number' && (
            <p className="mt-1 text-xs opacity-75">
              Commission: {commissionBps} bps per trade.
            </p>
          )}
        </div>
      )}
      {dataWarnings.length > 0 && (
        <div className="rounded-lg border border-amber-700/40 bg-amber-950/20 px-3 py-2 text-xs text-amber-100/90">
          {dataWarnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
        </div>
      )}
    </div>
  );
}
