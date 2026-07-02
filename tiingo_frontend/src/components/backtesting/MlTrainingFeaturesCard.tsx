import type { MlWalkForwardReadiness } from '../../api/mlBacktestTypes';
import {
  featureGroupLabel,
  orderedFeatureGroupKeys,
} from '../../utils/mlFeatureGroups';

type MlTrainingFeaturesCardProps = {
  featureNames: string[];
  featureGroups: Record<string, string[]>;
  alwaysIncluded: string[];
  featureCount: number;
  walkForwardReadiness?: MlWalkForwardReadiness | null;
};

export default function MlTrainingFeaturesCard({
  featureNames,
  featureGroups,
  alwaysIncluded,
  featureCount,
  walkForwardReadiness,
}: MlTrainingFeaturesCardProps) {
  const alwaysSet = new Set(alwaysIncluded);
  const groupKeys = orderedFeatureGroupKeys(featureGroups);

  if (featureCount === 0) {
    return (
      <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-4">
        <h4 className="text-sm font-medium text-amber-100">Model training columns</h4>
        <p className="text-xs text-amber-200/90 mt-2">
          No feature columns were built. Adjust feature mode, macro series, or optional context /
          strategy features on Data Prep, then run preview again.
        </p>
      </div>
    );
  }

  const validRows = walkForwardReadiness?.valid_feature_rows;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/50 p-4 space-y-3">
      <div>
        <h4 className="text-sm font-medium text-slate-200">
          Model training columns ({featureCount})
        </h4>
        <p className="text-xs text-slate-500 mt-1">
          Same columns used for walk-forward training after warmup.
          {validRows != null && (
            <> {validRows.toLocaleString()} bars have a complete feature vector.</>
          )}
        </p>
      </div>
      <div className="space-y-3">
        {groupKeys.map((groupKey) => (
          <div key={groupKey}>
            <p className="text-xs text-slate-400 mb-1.5">{featureGroupLabel(groupKey)}</p>
            <div className="flex flex-wrap gap-1.5">
              {(featureGroups[groupKey] ?? []).map((name) => (
                <span
                  key={name}
                  className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2 py-0.5 text-xs text-slate-200 font-mono"
                >
                  {name}
                  {alwaysSet.has(name) && (
                    <span className="text-[10px] uppercase tracking-wide text-brand-400 font-sans">
                      Always
                    </span>
                  )}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
