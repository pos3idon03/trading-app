import { useEffect, useState } from 'react';
import { EXCHANGES, type ExchangeConfig, type TradingSession } from '../constants/exchangeConfig';
import { getHoliday, type Holiday } from '../constants/holidayData';

export type MarketStatus = 'open' | 'lunch' | 'closed' | 'holiday' | 'weekend';

export interface MarketCountdown {
  id: string;
  label: string;
  fullName: string;
  status: MarketStatus;
  countdown: string;
  holidayName?: string;
}

interface ExchangeLocalTime {
  dateStr: string; // YYYY-MM-DD
  totalMinutes: number; // minutes since midnight in exchange timezone
  dayOfWeek: number; // 0=Sun, 6=Sat
}

function getExchangeLocalTime(timezone: string): ExchangeLocalTime {
  const now = new Date();
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: timezone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(now);

  const get = (type: string) =>
    parseInt(parts.find((p) => p.type === type)?.value ?? '0', 10);

  const year = get('year');
  const month = get('month');
  const day = get('day');
  const hour = get('hour') % 24; // guard against 24:00 edge case
  const minute = get('minute');

  const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
  const totalMinutes = hour * 60 + minute;

  const dateForDow = new Date(year, month - 1, day);
  const dayOfWeek = dateForDow.getDay();

  return { dateStr, totalMinutes, dayOfWeek };
}

function sessionStartMinutes(session: TradingSession): number {
  return session.openHour * 60 + session.openMinute;
}

function sessionEndMinutes(session: TradingSession): number {
  return session.closeHour * 60 + session.closeMinute;
}

function formatDuration(minutes: number): string {
  if (minutes <= 0) return '0m';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

function computeStatus(
  localTime: ExchangeLocalTime,
  exchange: ExchangeConfig,
  holiday: Holiday | null,
): { status: MarketStatus; countdown: string; holidayName?: string } {
  if (localTime.dayOfWeek === 0 || localTime.dayOfWeek === 6) {
    const minutesUntilOpen = computeMinutesUntilNextOpen(localTime, exchange);
    return {
      status: 'weekend',
      countdown: `Opens in ${formatDuration(minutesUntilOpen)}`,
    };
  }

  if (holiday) {
    return {
      status: 'holiday',
      countdown: 'Closed',
      holidayName: holiday.name,
    };
  }

  const { totalMinutes, sessions } = {
    totalMinutes: localTime.totalMinutes,
    sessions: exchange.sessions,
  };

  // Check if inside any session
  for (const session of sessions) {
    const start = sessionStartMinutes(session);
    const end = sessionEndMinutes(session);
    if (totalMinutes >= start && totalMinutes < end) {
      const remaining = end - totalMinutes;
      return { status: 'open', countdown: `Closes in ${formatDuration(remaining)}` };
    }
  }

  // Check if in lunch break (between sessions)
  if (sessions.length > 1) {
    const morningEnd = sessionEndMinutes(sessions[0]);
    const afternoonStart = sessionStartMinutes(sessions[1]);
    if (totalMinutes >= morningEnd && totalMinutes < afternoonStart) {
      const remaining = afternoonStart - totalMinutes;
      return { status: 'lunch', countdown: `Opens in ${formatDuration(remaining)}` };
    }
  }

  // Before first session
  const firstStart = sessionStartMinutes(sessions[0]);
  if (totalMinutes < firstStart) {
    const remaining = firstStart - totalMinutes;
    return { status: 'closed', countdown: `Opens in ${formatDuration(remaining)}` };
  }

  // After last session — closed for the day, opens next business day
  const nextOpenMinutes = computeMinutesUntilNextOpen(localTime, exchange);
  return { status: 'closed', countdown: `Opens in ${formatDuration(nextOpenMinutes)}` };
}

function computeMinutesUntilNextOpen(
  localTime: ExchangeLocalTime,
  exchange: ExchangeConfig,
): number {
  const minutesLeftToday = 24 * 60 - localTime.totalMinutes;
  const firstSessionStart = sessionStartMinutes(exchange.sessions[0]);
  let daysAhead = 1;

  while (daysAhead <= 7) {
    const [year, month, day] = localTime.dateStr.split('-').map(Number);
    const nextDate = new Date(year, month - 1, day + daysAhead);
    const dow = nextDate.getDay();
    if (dow !== 0 && dow !== 6) {
      const nextDateStr = nextDate.toISOString().slice(0, 10);
      if (!getHoliday(exchange.holidaySource, nextDateStr)) {
        return minutesLeftToday + (daysAhead - 1) * 24 * 60 + firstSessionStart;
      }
    }
    daysAhead++;
  }

  return minutesLeftToday + firstSessionStart;
}

function buildCountdown(exchange: ExchangeConfig): MarketCountdown {
  const localTime = getExchangeLocalTime(exchange.timezone);
  const holiday = getHoliday(exchange.holidaySource, localTime.dateStr);
  const { status, countdown, holidayName } = computeStatus(
    localTime,
    exchange,
    holiday,
  );
  return {
    id: exchange.id,
    label: exchange.label,
    fullName: exchange.fullName,
    status,
    countdown,
    holidayName,
  };
}

export function useMarketCountdowns(): MarketCountdown[] {
  const [countdowns, setCountdowns] = useState<MarketCountdown[]>(() =>
    EXCHANGES.map(buildCountdown),
  );

  useEffect(() => {
    const tick = () => setCountdowns(EXCHANGES.map(buildCountdown));
    const id = setInterval(tick, 60_000); // refresh every minute (minute-precision is sufficient)
    return () => clearInterval(id);
  }, []);

  return countdowns;
}
