export type HolidaySource = 'us' | 'uk' | 'eu' | 'jp' | 'hk' | 'cn' | 'au';

export interface TradingSession {
  openHour: number;
  openMinute: number;
  closeHour: number;
  closeMinute: number;
}

export interface ExchangeConfig {
  id: string;
  label: string;
  fullName: string;
  timezone: string;
  sessions: TradingSession[];
  holidaySource: HolidaySource;
}

export const EXCHANGES: ExchangeConfig[] = [
  {
    id: 'nyse',
    label: 'NYSE',
    fullName: 'New York Stock Exchange',
    timezone: 'America/New_York',
    sessions: [{ openHour: 9, openMinute: 30, closeHour: 16, closeMinute: 0 }],
    holidaySource: 'us',
  },
  {
    id: 'lse',
    label: 'LSE',
    fullName: 'London Stock Exchange',
    timezone: 'Europe/London',
    sessions: [{ openHour: 8, openMinute: 0, closeHour: 16, closeMinute: 30 }],
    holidaySource: 'uk',
  },
  {
    id: 'euronext',
    label: 'Euronext',
    fullName: 'Euronext Paris/Amsterdam',
    timezone: 'Europe/Paris',
    sessions: [{ openHour: 9, openMinute: 0, closeHour: 17, closeMinute: 30 }],
    holidaySource: 'eu',
  },
  {
    id: 'xetra',
    label: 'XETRA',
    fullName: 'Frankfurt Stock Exchange',
    timezone: 'Europe/Berlin',
    sessions: [{ openHour: 9, openMinute: 0, closeHour: 17, closeMinute: 30 }],
    holidaySource: 'eu',
  },
  {
    id: 'tse',
    label: 'TSE',
    fullName: 'Tokyo Stock Exchange',
    timezone: 'Asia/Tokyo',
    sessions: [
      { openHour: 9, openMinute: 0, closeHour: 11, closeMinute: 30 },
      { openHour: 12, openMinute: 30, closeHour: 15, closeMinute: 30 },
    ],
    holidaySource: 'jp',
  },
  {
    id: 'hkex',
    label: 'HKEX',
    fullName: 'Hong Kong Stock Exchange',
    timezone: 'Asia/Hong_Kong',
    sessions: [
      { openHour: 9, openMinute: 30, closeHour: 12, closeMinute: 0 },
      { openHour: 13, openMinute: 0, closeHour: 16, closeMinute: 0 },
    ],
    holidaySource: 'hk',
  },
  {
    id: 'sse',
    label: 'SSE',
    fullName: 'Shanghai Stock Exchange',
    timezone: 'Asia/Shanghai',
    sessions: [
      { openHour: 9, openMinute: 30, closeHour: 11, closeMinute: 30 },
      { openHour: 13, openMinute: 0, closeHour: 15, closeMinute: 0 },
    ],
    holidaySource: 'cn',
  },
  {
    id: 'asx',
    label: 'ASX',
    fullName: 'Australian Securities Exchange',
    timezone: 'Australia/Sydney',
    sessions: [{ openHour: 10, openMinute: 0, closeHour: 16, closeMinute: 0 }],
    holidaySource: 'au',
  },
];
