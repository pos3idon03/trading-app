import { describe, expect, it } from 'vitest';
import type { MacroBriefResponse } from '../api/types';
import {
  formatMacroBriefGeneratedAt,
  isMacroBriefAvailable,
  macroBriefSections,
  macroBriefUnavailableMessage,
  macroCyclePhaseStyles,
} from '../utils/macroBrief';

const availableBrief: MacroBriefResponse = {
  as_of: '2024-06-01',
  situation: 'Growth is steady while inflation cools.',
  outlook: 'Rates may stay higher for longer.',
  situation_phase: 'Expansion',
  outlook_phase: 'Slowdown',
  generated_at: '2024-06-01T12:00:00Z',
  available: true,
  message: null,
};

describe('macroBrief utils', () => {
  it('detects available briefs with content', () => {
    expect(isMacroBriefAvailable(availableBrief)).toBe(true);
  });

  it('treats unavailable briefs as not available', () => {
    expect(
      isMacroBriefAvailable({
        ...availableBrief,
        available: false,
        situation: null,
        outlook: null,
        message: 'GEMINI_API_KEY is not configured',
      }),
    ).toBe(false);
  });

  it('builds section list from situation and outlook with phases', () => {
    expect(macroBriefSections(availableBrief)).toEqual([
      {
        title: 'Current situation',
        body: 'Growth is steady while inflation cools.',
        phase: 'Expansion',
      },
      {
        title: 'Outlook',
        body: 'Rates may stay higher for longer.',
        phase: 'Slowdown',
      },
    ]);
  });

  it('omits phase when not provided', () => {
    const brief: MacroBriefResponse = {
      ...availableBrief,
      situation_phase: null,
      outlook_phase: null,
    };
    expect(macroBriefSections(brief)).toEqual([
      { title: 'Current situation', body: brief.situation!, phase: null },
      { title: 'Outlook', body: brief.outlook!, phase: null },
    ]);
  });

  it('returns fallback unavailable message', () => {
    expect(macroBriefUnavailableMessage(null)).toBe('Macro brief is unavailable.');
    expect(
      macroBriefUnavailableMessage({
        ...availableBrief,
        available: false,
        message: 'Macro brief is disabled',
      }),
    ).toBe('Macro brief is disabled');
  });

  it('formats generated_at timestamp in UTC', () => {
    expect(formatMacroBriefGeneratedAt('2024-06-01T12:00:00Z')).toMatch(/Jun 1, 2024/);
    expect(formatMacroBriefGeneratedAt(null)).toBeNull();
  });

  it('maps cycle phases to distinct badge styles', () => {
    const expansion = macroCyclePhaseStyles('Expansion');
    const recession = macroCyclePhaseStyles('Recession');
    expect(expansion.badge).not.toBe(recession.badge);
    expect(expansion.badgeText).not.toBe(recession.badgeText);
  });
});
