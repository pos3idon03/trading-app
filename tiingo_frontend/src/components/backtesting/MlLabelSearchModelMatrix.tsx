import type { MlLabelMode, MlModelCatalogItem } from '../../api/mlBacktestTypes';
import {
  LABEL_MODE_DEFAULT_HINTS,
  type LabelSearchMatrixRow,
  type LabelSearchMatrixState,
} from '../../utils/mlLabelSearchMatrix';

interface MlLabelSearchModelMatrixProps {
  models: MlModelCatalogItem[];
  matrix: LabelSearchMatrixState;
  onChange: (next: LabelSearchMatrixState) => void;
  disabled?: boolean;
}

const LABEL_MODE_OPTIONS: { value: MlLabelMode; label: string }[] = [
  { value: 'binary', label: 'Binary (up / down)' },
  { value: 'ternary', label: 'Ternary (ranging / sell / buy)' },
  { value: 'meta_label', label: 'Meta-label (gatekeeper)' },
];

export default function MlLabelSearchModelMatrix({
  models,
  matrix,
  onChange,
  disabled = false,
}: MlLabelSearchModelMatrixProps) {
  const updateRow = (modelId: string, patch: Partial<LabelSearchMatrixRow>) => {
    const current = matrix[modelId];
    if (!current) {
      return;
    }
    onChange({
      ...matrix,
      [modelId]: { ...current, ...patch },
    });
  };

  if (models.length === 0) {
    return (
      <p className="text-xs text-slate-500">Loading model catalog…</p>
    );
  }

  return (
    <div className="overflow-x-auto border border-slate-800 rounded-lg">
      <table className="min-w-full text-sm">
        <thead className="bg-surface-900 text-slate-400">
          <tr>
            <th className="px-3 py-2 text-left w-12">Include</th>
            <th className="px-3 py-2 text-left">Model</th>
            <th className="px-3 py-2 text-left">Label mode</th>
            <th className="px-3 py-2 text-left">Default rationale</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => {
            const row = matrix[model.id];
            if (!row) {
              return null;
            }
            return (
              <tr key={model.id} className="border-t border-slate-800">
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={row.enabled}
                    disabled={disabled}
                    onChange={(e) => updateRow(model.id, { enabled: e.target.checked })}
                    className="rounded border-slate-600"
                    aria-label={`Include ${model.label} in label grid search`}
                  />
                </td>
                <td className="px-3 py-2 text-slate-200 whitespace-nowrap">
                  {model.label}
                </td>
                <td className="px-3 py-2">
                  <select
                    value={row.labelMode}
                    disabled={disabled || !row.enabled}
                    onChange={(e) =>
                      updateRow(model.id, {
                        labelMode: e.target.value as MlLabelMode,
                      })
                    }
                    className="w-full min-w-[12rem] bg-surface-950 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-100 text-xs"
                  >
                    {LABEL_MODE_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2 text-xs text-slate-500 max-w-xs">
                  {LABEL_MODE_DEFAULT_HINTS[row.labelMode]}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
