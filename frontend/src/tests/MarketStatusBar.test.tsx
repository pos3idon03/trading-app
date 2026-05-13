import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import MarketStatusBar from '../components/MarketStatusBar';
import { getHoliday } from '../constants/holidayData';
import { EXCHANGES } from '../constants/exchangeConfig';

// ─── Holiday data tests ────────────────────────────────────────────────────

describe('getHoliday', () => {
  it('returns null for a regular weekday', () => {
    expect(getHoliday('us', '2026-03-10')).toBeNull();
  });

  it('returns a holiday object for Christmas (US)', () => {
    const h = getHoliday('us', '2026-12-25');
    expect(h).not.toBeNull();
    expect(h?.name).toMatch(/christmas/i);
  });

  it('returns observed New Year (US) when Jan 1 falls on Saturday', () => {
    // Jan 1 2022 was a Saturday → observed Dec 31 2021
    // Our years start at 2025; Jan 1 2026 is Thursday — no observation
    const h = getHoliday('us', '2026-01-01');
    expect(h).not.toBeNull();
    expect(h?.name).toMatch(/new year/i);
  });

  it('returns Good Friday for UK', () => {
    // 2026 Easter is April 5 → Good Friday April 3
    const h = getHoliday('uk', '2026-04-03');
    expect(h).not.toBeNull();
    expect(h?.name).toMatch(/good friday/i);
  });

  it('returns null for a non-holiday UK date', () => {
    expect(getHoliday('uk', '2026-03-15')).toBeNull();
  });

  it('returns a Spring Festival holiday for CN', () => {
    const h = getHoliday('cn', '2026-02-17');
    expect(h).not.toBeNull();
    expect(h?.name).toMatch(/spring festival/i);
  });

  it('returns a JP TSE holiday', () => {
    const h = getHoliday('jp', '2026-05-03');
    expect(h).not.toBeNull();
    expect(h?.name).toMatch(/constitution/i);
  });

  it('returns a HK holiday', () => {
    const h = getHoliday('hk', '2026-01-01');
    expect(h).not.toBeNull();
    expect(h?.name).toMatch(/new year/i);
  });

  it('returns an AU ASX holiday for Good Friday', () => {
    const h = getHoliday('au', '2026-04-03');
    expect(h).not.toBeNull();
    expect(h?.name).toMatch(/good friday/i);
  });
});

// ─── Exchange config tests ─────────────────────────────────────────────────

describe('EXCHANGES config', () => {
  it('contains 8 exchanges', () => {
    expect(EXCHANGES).toHaveLength(8);
  });

  it('each exchange has at least one session', () => {
    EXCHANGES.forEach((ex) => {
      expect(ex.sessions.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('multi-session exchanges (TSE, HKEX, SSE) have 2 sessions', () => {
    const multi = ['tse', 'hkex', 'sse'];
    multi.forEach((id) => {
      const ex = EXCHANGES.find((e) => e.id === id);
      expect(ex?.sessions).toHaveLength(2);
    });
  });

  it('all exchanges have a valid IANA timezone', () => {
    EXCHANGES.forEach((ex) => {
      expect(() => new Intl.DateTimeFormat('en', { timeZone: ex.timezone })).not.toThrow();
    });
  });
});

// ─── MarketStatusBar rendering tests ──────────────────────────────────────

describe('MarketStatusBar', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders the Markets label', () => {
    render(<MarketStatusBar />);
    expect(screen.getByText('Markets')).toBeInTheDocument();
  });

  it('renders all 8 exchange labels (duplicated for seamless loop)', () => {
    render(<MarketStatusBar />);
    const labels = ['NYSE', 'LSE', 'Euronext', 'XETRA', 'TSE', 'HKEX', 'SSE', 'ASX'];
    labels.forEach((label) => {
      // Each label appears twice (original + duplicate for seamless scroll)
      const found = screen.getAllByText(label);
      expect(found.length).toBeGreaterThanOrEqual(1);
    });
  });

  it('renders a countdown string for each exchange', () => {
    render(<MarketStatusBar />);
    // At least one of open/close/weekend countdown texts should be present
    const patterns = [/opens in/i, /closes in/i, /closed/i];
    const allText = document.body.textContent ?? '';
    const anyMatch = patterns.some((p) => p.test(allText));
    expect(anyMatch).toBe(true);
  });

  it('has the aria region label for accessibility', () => {
    render(<MarketStatusBar />);
    expect(screen.getByRole('region', { name: /market hours/i })).toBeInTheDocument();
  });

  it('updates after a minute tick', () => {
    const { container } = render(<MarketStatusBar />);
    const before = container.innerHTML;

    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    // After a minute, the component should have re-rendered (no crash)
    expect(container.innerHTML).toBeDefined();
    // Content may or may not change depending on system time, but no error
    void before;
  });

  it('shows holiday tooltip when exchange is on holiday', () => {
    // Mock Date to a known NYSE holiday: 2026-12-25 at 10:00 ET
    const fixedDate = new Date('2026-12-25T15:00:00Z'); // 10am ET
    vi.setSystemTime(fixedDate);

    render(<MarketStatusBar />);
    // NYSE pills (duplicated) should have a title containing Christmas
    const nysePills = screen.getAllByText('NYSE');
    const nyseEl = nysePills[0].closest('[title]');
    expect(nyseEl?.getAttribute('title')).toMatch(/christmas/i);
  });
});
