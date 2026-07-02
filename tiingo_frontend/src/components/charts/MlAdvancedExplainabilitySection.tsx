import type { MlSummary } from '../../api/mlBacktestTypes';
import MlPartialDependenceChart from './MlPartialDependenceChart';

interface MlAdvancedExplainabilitySectionProps {
  summary: MlSummary;
}

export default function MlAdvancedExplainabilitySection({
  summary,
}: MlAdvancedExplainabilitySectionProps) {
  const interactions = summary.shap_interactions ?? [];
  const slices = summary.shap_slices;
  const treeRules = summary.tree_rules;
  const pdp = summary.partial_dependence ?? [];

  const hasContent =
    interactions.length > 0 || pdp.length > 0 || Boolean(slices) || Boolean(treeRules);
  if (!hasContent) {
    return null;
  }

  return (
    <div className="space-y-4 border-t border-slate-800 pt-4">
      <h3 className="text-sm font-medium text-slate-300">Advanced explainability</h3>

      {interactions.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-slate-400">Top feature interactions</h4>
          <ul className="space-y-1 text-xs text-slate-300">
            {interactions.map((row) => (
              <li key={`${row.feature_a}-${row.feature_b}`}>
                <span className="font-mono">{row.feature_a}</span>
                {' × '}
                <span className="font-mono">{row.feature_b}</span>
                {' — strength '}
                {row.strength.toFixed(4)}
              </li>
            ))}
          </ul>
        </div>
      )}

      {pdp.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-slate-400">Partial dependence (P up)</h4>
          <MlPartialDependenceChart curves={pdp} />
        </div>
      )}

      {slices && (
        <div className="grid gap-3 sm:grid-cols-2">
          <SliceList title="Winners (top 10% P&amp;L)" items={slices.winners_top_decile} />
          <SliceList title="Losers (bottom 10% P&amp;L)" items={slices.losers_bottom_decile} />
        </div>
      )}

      {treeRules?.content && (
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-slate-400">Representative tree rules</h4>
          <pre className="max-h-64 overflow-auto rounded bg-slate-900/80 p-3 text-[11px] leading-relaxed text-slate-300">
            {treeRules.content}
          </pre>
        </div>
      )}
    </div>
  );
}

function SliceList({
  title,
  items,
}: {
  title: string;
  items: Array<{ feature: string; mean_abs_shap: number }>;
}) {
  if (!items.length) {
    return null;
  }
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-medium text-slate-400">{title}</h4>
      <ul className="space-y-0.5 text-xs text-slate-300">
        {items.map((row) => (
          <li key={row.feature} className="flex justify-between gap-2">
            <span className="font-mono">{row.feature}</span>
            <span>{row.mean_abs_shap.toFixed(4)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
