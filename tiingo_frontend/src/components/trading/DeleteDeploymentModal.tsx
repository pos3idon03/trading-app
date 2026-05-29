import { useEffect, useState } from 'react';

import type { DeploymentRow } from '../../utils/tradingDeployments';

type DeleteDeploymentModalProps = {
  deployment: DeploymentRow | null;
  busy?: boolean;
  onConfirm: (closePositions: boolean) => void;
  onCancel: () => void;
};

export default function DeleteDeploymentModal({
  deployment,
  busy = false,
  onConfirm,
  onCancel,
}: DeleteDeploymentModalProps) {
  const [closePositions, setClosePositions] = useState(false);
  const positionQty = deployment?.deployment.position_qty ?? 0;
  const hasPosition = positionQty > 0;

  useEffect(() => {
    setClosePositions(false);
  }, [deployment?.id]);

  if (!deployment) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-deployment-modal-title"
    >
      <div className="w-full max-w-md rounded-xl border border-slate-700 bg-surface-900 p-6 shadow-xl">
        <h2 id="delete-deployment-modal-title" className="text-lg font-medium text-white">
          Delete deployment?
        </h2>
        <p className="mt-2 text-sm text-slate-400">
          Permanently remove the deployment for{' '}
          <span className="text-slate-200">{deployment.symbol}</span>
          {deployment.modelName !== '—' ? ` (${deployment.modelName})` : ''}. Order and activity
          history for this deployment will be deleted.
        </p>
        {hasPosition ? (
          <div className="mt-4 space-y-2">
            <label className="flex items-start gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={closePositions}
                onChange={(event) => setClosePositions(event.target.checked)}
                disabled={busy}
                className="mt-0.5 rounded border-slate-600 bg-surface-800"
              />
              <span>
                Close deployment position ({positionQty.toFixed(4)} {deployment.symbol}) before
                deleting
              </span>
            </label>
            {!closePositions && (
              <p className="text-xs text-amber-400/90">
                If unchecked, these shares remain in Alpaca as untracked holdings.
              </p>
            )}
          </div>
        ) : null}
        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="px-4 py-2 rounded-lg text-sm border border-slate-700 text-slate-300 hover:bg-surface-800 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => onConfirm(closePositions)}
            disabled={busy}
            className="px-4 py-2 rounded-lg text-sm bg-red-700 hover:bg-red-600 text-white disabled:opacity-50"
          >
            {busy ? 'Deleting…' : 'Delete deployment'}
          </button>
        </div>
      </div>
    </div>
  );
}
