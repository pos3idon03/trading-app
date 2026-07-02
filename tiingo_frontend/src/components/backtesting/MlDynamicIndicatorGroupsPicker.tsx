import {
  DEFAULT_INDICATOR_GROUPS,
  ML_INDICATOR_GROUPS,
  type MlIndicatorGroupId,
} from '../../utils/mlIndicatorGroups';

interface MlDynamicIndicatorGroupsPickerProps {
  enabled: boolean;
  selectedGroups: string[];
  onEnabledChange: (enabled: boolean) => void;
  onToggleGroup: (groupId: MlIndicatorGroupId) => void;
  disabled?: boolean;
  validationError?: string | null;
}

export default function MlDynamicIndicatorGroupsPicker({
  enabled,
  selectedGroups,
  onEnabledChange,
  onToggleGroup,
  disabled = false,
  validationError = null,
}: MlDynamicIndicatorGroupsPickerProps) {
  const selected = new Set(selectedGroups);

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
        <input
          type="checkbox"
          checked={enabled}
          disabled={disabled}
          onChange={(e) => onEnabledChange(e.target.checked)}
        />
        <span className="font-medium">Dynamic indicator selection</span>
      </label>
      <p className="text-xs text-slate-500">
        Per walk-forward fold, vol regime picks one enabled price-indicator group (momentum,
        mean reversion, or volatility). Does not mask algo strat_* columns.
      </p>
      {enabled && (
        <div className="space-y-3 pl-1 border-l border-slate-800 ml-1">
          {ML_INDICATOR_GROUPS.map((group) => (
            <label
              key={group.id}
              className="flex items-start gap-2 text-sm text-slate-300 cursor-pointer"
            >
              <input
                type="checkbox"
                className="mt-1"
                checked={selected.has(group.id)}
                disabled={disabled}
                onChange={() => onToggleGroup(group.id)}
              />
              <span>
                <span className="font-medium text-slate-200">{group.label}</span>
                <span className="block text-xs text-slate-500">
                  {group.features.join(', ')}
                </span>
              </span>
            </label>
          ))}
        </div>
      )}
      {validationError && (
        <p className="text-xs text-amber-200/90">{validationError}</p>
      )}
      {enabled && selectedGroups.length === 0 && !validationError && (
        <p className="text-xs text-amber-200/90">
          Select at least one group (defaults: {DEFAULT_INDICATOR_GROUPS.join(', ')}).
        </p>
      )}
    </div>
  );
}
