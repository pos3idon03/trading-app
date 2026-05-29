import type { MacroBriefResponse, MacroCyclePhase } from '../api/types';

export function isMacroBriefAvailable(brief: MacroBriefResponse | null | undefined): boolean {
  return Boolean(brief?.available && (brief.situation || brief.outlook));
}

export function macroBriefUnavailableMessage(
  brief: MacroBriefResponse | null | undefined,
): string {
  return brief?.message ?? 'Macro brief is unavailable.';
}

export interface MacroBriefSection {
  title: string;
  body: string;
  phase?: MacroCyclePhase | null;
}

export function macroBriefSections(brief: MacroBriefResponse): MacroBriefSection[] {
  const sections: MacroBriefSection[] = [];
  if (brief.situation?.trim()) {
    sections.push({
      title: 'Current situation',
      body: brief.situation.trim(),
      phase: brief.situation_phase ?? null,
    });
  }
  if (brief.outlook?.trim()) {
    sections.push({
      title: 'Outlook',
      body: brief.outlook.trim(),
      phase: brief.outlook_phase ?? null,
    });
  }
  return sections;
}

export function macroCyclePhaseStyles(phase: MacroCyclePhase): {
  badge: string;
  badgeText: string;
} {
  switch (phase) {
    case 'Expansion':
      return { badge: 'bg-emerald-900/50', badgeText: 'text-emerald-200' };
    case 'Peak':
      return { badge: 'bg-amber-900/50', badgeText: 'text-amber-200' };
    case 'Slowdown':
      return { badge: 'bg-orange-900/50', badgeText: 'text-orange-200' };
    case 'Recession':
      return { badge: 'bg-red-900/50', badgeText: 'text-red-200' };
    case 'Trough':
      return { badge: 'bg-violet-900/50', badgeText: 'text-violet-200' };
    case 'Stagnation':
      return { badge: 'bg-slate-800', badgeText: 'text-slate-300' };
    default:
      return { badge: 'bg-slate-800', badgeText: 'text-slate-300' };
  }
}

export function formatMacroBriefGeneratedAt(iso: string | null | undefined): string | null {
  if (!iso) {
    return null;
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(date);
}
