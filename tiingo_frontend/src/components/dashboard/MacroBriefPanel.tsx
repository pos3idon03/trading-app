import { useCallback, useEffect, useState } from 'react';
import { marketDataApi } from '../../api/endpoints';
import type { MacroBriefResponse } from '../../api/types';
import ErrorAlert from '../ErrorAlert';
import Spinner from '../Spinner';
import {
  formatMacroBriefGeneratedAt,
  isMacroBriefAvailable,
  macroBriefSections,
  macroBriefUnavailableMessage,
  macroCyclePhaseStyles,
} from '../../utils/macroBrief';

export default function MacroBriefPanel() {
  const [brief, setBrief] = useState<MacroBriefResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await marketDataApi.getMacroBrief();
      setBrief(data);
    } catch (e) {
      setBrief(null);
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-5">
        <div className="flex items-center gap-3 text-sm text-slate-400">
          <Spinner />
          <span>Loading macro brief…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return <ErrorAlert message={error} />;
  }

  if (!isMacroBriefAvailable(brief)) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-4">
        <p className="text-sm text-slate-500">{macroBriefUnavailableMessage(brief)}</p>
      </div>
    );
  }

  const sections = macroBriefSections(brief!);
  const generatedLabel = formatMacroBriefGeneratedAt(brief!.generated_at);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-4 space-y-4">
      {sections.map((section) => {
        const phaseStyles = section.phase ? macroCyclePhaseStyles(section.phase) : null;
        return (
          <div key={section.title} className="space-y-1">
            {section.phase && phaseStyles ? (
              <span
                className={`inline-block text-xs font-semibold uppercase tracking-wide px-2.5 py-1 rounded ${phaseStyles.badge} ${phaseStyles.badgeText}`}
              >
                {section.phase}
              </span>
            ) : null}
            <h3 className="text-sm font-medium text-slate-300">{section.title}</h3>
            <p className="text-sm leading-relaxed text-slate-400 whitespace-pre-wrap">{section.body}</p>
          </div>
        );
      })}
      <p className="text-[11px] leading-relaxed text-slate-500">
        AI-generated summary based on stored macro data; not investment advice.
        {generatedLabel ? ` Generated ${generatedLabel} UTC.` : ''}
      </p>
    </div>
  );
}
