import type { HolidaySource } from './exchangeConfig';

export interface Holiday {
  date: string; // YYYY-MM-DD
  name: string;
}

// Easter Sunday calculation (anonymous Gregorian algorithm)
function easterSunday(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const day = ((h + l - 7 * m + 114) % 31) + 1;
  return new Date(year, month - 1, day);
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function fmt(date: Date): string {
  return date.toISOString().slice(0, 10);
}

// Nth weekday of a month: e.g. nthWeekday(2026, 1, 1, 3) = 3rd Monday of January 2026
// weekday: 0=Sun, 1=Mon, ..., 6=Sat
function nthWeekday(year: number, month: number, weekday: number, n: number): Date {
  const first = new Date(year, month - 1, 1);
  let day = first.getDay();
  const offset = (weekday - day + 7) % 7;
  return new Date(year, month - 1, 1 + offset + (n - 1) * 7);
}

// Last weekday of a month
function lastWeekday(year: number, month: number, weekday: number): Date {
  const last = new Date(year, month, 0); // last day of month
  let day = last.getDay();
  const offset = (day - weekday + 7) % 7;
  return new Date(year, month - 1, last.getDate() - offset);
}

// Observable holiday: if date falls on Saturday -> Friday, Sunday -> Monday
function observedDate(date: Date): Date {
  const dow = date.getDay();
  if (dow === 6) return addDays(date, -1);
  if (dow === 0) return addDays(date, 1);
  return date;
}

// US NYSE/NASDAQ holidays
function usHolidays(year: number): Holiday[] {
  const easter = easterSunday(year);
  const goodFriday = addDays(easter, -2);
  return [
    { date: fmt(observedDate(new Date(year, 0, 1))), name: "New Year's Day" },
    { date: fmt(nthWeekday(year, 1, 1, 3)), name: 'Martin Luther King Jr. Day' },
    { date: fmt(nthWeekday(year, 2, 1, 3)), name: "Presidents' Day" },
    { date: fmt(goodFriday), name: 'Good Friday' },
    { date: fmt(lastWeekday(year, 5, 1)), name: 'Memorial Day' },
    { date: fmt(observedDate(new Date(year, 5, 19))), name: 'Juneteenth' },
    { date: fmt(observedDate(new Date(year, 6, 4))), name: 'Independence Day' },
    { date: fmt(nthWeekday(year, 9, 1, 1)), name: 'Labor Day' },
    { date: fmt(addDays(nthWeekday(year, 11, 4, 4), 1)), name: 'Thanksgiving (Friday)' },
    { date: fmt(observedDate(new Date(year, 11, 25))), name: 'Christmas Day' },
  ];
}

// UK LSE holidays
function ukHolidays(year: number): Holiday[] {
  const easter = easterSunday(year);
  const goodFriday = addDays(easter, -2);
  const easterMonday = addDays(easter, 1);
  const mayDay = nthWeekday(year, 5, 1, 1);
  const springBankHoliday = lastWeekday(year, 5, 1);
  const summerBankHoliday = lastWeekday(year, 8, 1);
  return [
    { date: fmt(new Date(year, 0, 1)), name: "New Year's Day" },
    { date: fmt(goodFriday), name: 'Good Friday' },
    { date: fmt(easterMonday), name: 'Easter Monday' },
    { date: fmt(mayDay), name: 'Early May Bank Holiday' },
    { date: fmt(springBankHoliday), name: 'Spring Bank Holiday' },
    { date: fmt(summerBankHoliday), name: 'Summer Bank Holiday' },
    { date: fmt(new Date(year, 11, 25)), name: 'Christmas Day' },
    { date: fmt(new Date(year, 11, 26)), name: 'Boxing Day' },
  ];
}

// EU (Euronext/XETRA) holidays — common Euronext exchange holidays
function euHolidays(year: number): Holiday[] {
  const easter = easterSunday(year);
  const goodFriday = addDays(easter, -2);
  const easterMonday = addDays(easter, 1);
  return [
    { date: fmt(new Date(year, 0, 1)), name: "New Year's Day" },
    { date: fmt(goodFriday), name: 'Good Friday' },
    { date: fmt(easterMonday), name: 'Easter Monday' },
    { date: fmt(new Date(year, 4, 1)), name: 'Labour Day' },
    { date: fmt(new Date(year, 11, 25)), name: 'Christmas Day' },
    { date: fmt(new Date(year, 11, 26)), name: 'Christmas Holiday' },
  ];
}

// Japan TSE holidays (static 2025-2027 — includes national holidays + Golden Week)
const JP_HOLIDAYS: Holiday[] = [
  // 2025
  { date: '2025-01-01', name: "New Year's Day" },
  { date: '2025-01-02', name: 'Bank Holiday' },
  { date: '2025-01-03', name: 'Bank Holiday' },
  { date: '2025-01-13', name: 'Coming of Age Day' },
  { date: '2025-02-11', name: 'National Foundation Day' },
  { date: '2025-02-23', name: "Emperor's Birthday" },
  { date: '2025-02-24', name: "Emperor's Birthday (observed)" },
  { date: '2025-03-20', name: 'Vernal Equinox Day' },
  { date: '2025-04-29', name: 'Showa Day' },
  { date: '2025-05-03', name: 'Constitution Memorial Day' },
  { date: '2025-05-04', name: 'Greenery Day' },
  { date: '2025-05-05', name: "Children's Day" },
  { date: '2025-05-06', name: "Children's Day (observed)" },
  { date: '2025-07-21', name: 'Marine Day' },
  { date: '2025-08-11', name: 'Mountain Day' },
  { date: '2025-09-15', name: 'Respect for the Aged Day' },
  { date: '2025-09-23', name: 'Autumnal Equinox Day' },
  { date: '2025-10-13', name: 'Sports Day' },
  { date: '2025-11-03', name: 'Culture Day' },
  { date: '2025-11-23', name: 'Labour Thanksgiving Day' },
  { date: '2025-11-24', name: 'Labour Thanksgiving Day (observed)' },
  { date: '2025-12-31', name: 'Year-end closure' },
  // 2026
  { date: '2026-01-01', name: "New Year's Day" },
  { date: '2026-01-02', name: 'Bank Holiday' },
  { date: '2026-01-12', name: 'Coming of Age Day' },
  { date: '2026-02-11', name: 'National Foundation Day' },
  { date: '2026-02-23', name: "Emperor's Birthday" },
  { date: '2026-03-20', name: 'Vernal Equinox Day' },
  { date: '2026-04-29', name: 'Showa Day' },
  { date: '2026-05-03', name: 'Constitution Memorial Day' },
  { date: '2026-05-04', name: 'Greenery Day' },
  { date: '2026-05-05', name: "Children's Day" },
  { date: '2026-05-06', name: "Children's Day (observed)" },
  { date: '2026-07-20', name: 'Marine Day' },
  { date: '2026-08-11', name: 'Mountain Day' },
  { date: '2026-09-21', name: 'Respect for the Aged Day' },
  { date: '2026-09-23', name: 'Autumnal Equinox Day' },
  { date: '2026-10-12', name: 'Sports Day' },
  { date: '2026-11-03', name: 'Culture Day' },
  { date: '2026-11-23', name: 'Labour Thanksgiving Day' },
  { date: '2026-12-31', name: 'Year-end closure' },
  // 2027
  { date: '2027-01-01', name: "New Year's Day" },
  { date: '2027-01-02', name: 'Bank Holiday' },
  { date: '2027-01-11', name: 'Coming of Age Day' },
  { date: '2027-02-11', name: 'National Foundation Day' },
  { date: '2027-02-23', name: "Emperor's Birthday" },
  { date: '2027-03-20', name: 'Vernal Equinox Day' },
  { date: '2027-04-29', name: 'Showa Day' },
  { date: '2027-05-03', name: 'Constitution Memorial Day' },
  { date: '2027-05-04', name: 'Greenery Day' },
  { date: '2027-05-05', name: "Children's Day" },
  { date: '2027-07-19', name: 'Marine Day' },
  { date: '2027-08-11', name: 'Mountain Day' },
  { date: '2027-09-20', name: 'Respect for the Aged Day' },
  { date: '2027-09-23', name: 'Autumnal Equinox Day' },
  { date: '2027-10-11', name: 'Sports Day' },
  { date: '2027-11-03', name: 'Culture Day' },
  { date: '2027-11-23', name: 'Labour Thanksgiving Day' },
  { date: '2027-12-31', name: 'Year-end closure' },
];

// Hong Kong HKEX holidays (static 2025-2027)
const HK_HOLIDAYS: Holiday[] = [
  // 2025
  { date: '2025-01-01', name: "New Year's Day" },
  { date: '2025-01-29', name: 'Lunar New Year' },
  { date: '2025-01-30', name: 'Lunar New Year' },
  { date: '2025-01-31', name: 'Lunar New Year' },
  { date: '2025-04-04', name: 'Ching Ming Festival' },
  { date: '2025-04-18', name: 'Good Friday' },
  { date: '2025-04-19', name: 'Good Friday (day after)' },
  { date: '2025-04-21', name: 'Easter Monday' },
  { date: '2025-05-01', name: 'Labour Day' },
  { date: '2025-05-05', name: 'Buddha\'s Birthday' },
  { date: '2025-05-31', name: 'Tuen Ng Festival' },
  { date: '2025-07-01', name: 'HKSAR Establishment Day' },
  { date: '2025-10-01', name: 'National Day' },
  { date: '2025-10-02', name: 'National Day (day after)' },
  { date: '2025-10-07', name: 'Chung Yeung Festival' },
  { date: '2025-12-25', name: 'Christmas Day' },
  { date: '2025-12-26', name: 'Christmas Holiday' },
  // 2026
  { date: '2026-01-01', name: "New Year's Day" },
  { date: '2026-02-17', name: 'Lunar New Year' },
  { date: '2026-02-18', name: 'Lunar New Year' },
  { date: '2026-02-19', name: 'Lunar New Year' },
  { date: '2026-04-05', name: 'Ching Ming Festival' },
  { date: '2026-04-03', name: 'Good Friday' },
  { date: '2026-04-04', name: 'Good Friday (day after)' },
  { date: '2026-04-06', name: 'Easter Monday' },
  { date: '2026-05-01', name: 'Labour Day' },
  { date: '2026-05-24', name: "Buddha's Birthday" },
  { date: '2026-06-19', name: 'Tuen Ng Festival' },
  { date: '2026-07-01', name: 'HKSAR Establishment Day' },
  { date: '2026-10-01', name: 'National Day' },
  { date: '2026-10-26', name: 'Chung Yeung Festival' },
  { date: '2026-12-25', name: 'Christmas Day' },
  // 2027
  { date: '2027-01-01', name: "New Year's Day" },
  { date: '2027-02-06', name: 'Lunar New Year' },
  { date: '2027-02-07', name: 'Lunar New Year' },
  { date: '2027-02-08', name: 'Lunar New Year' },
  { date: '2027-04-05', name: 'Ching Ming Festival' },
  { date: '2027-03-26', name: 'Good Friday' },
  { date: '2027-03-27', name: 'Good Friday (day after)' },
  { date: '2027-03-29', name: 'Easter Monday' },
  { date: '2027-05-01', name: 'Labour Day' },
  { date: '2027-05-13', name: "Buddha's Birthday" },
  { date: '2027-06-09', name: 'Tuen Ng Festival' },
  { date: '2027-07-01', name: 'HKSAR Establishment Day' },
  { date: '2027-10-01', name: 'National Day' },
  { date: '2027-10-15', name: 'Chung Yeung Festival' },
  { date: '2027-12-25', name: 'Christmas Day' },
  { date: '2027-12-27', name: 'Christmas (observed)' },
];

// China SSE holidays (static 2025-2027 — Chinese national holidays)
const CN_HOLIDAYS: Holiday[] = [
  // 2025
  { date: '2025-01-01', name: "New Year's Day" },
  { date: '2025-01-28', name: 'Spring Festival' },
  { date: '2025-01-29', name: 'Spring Festival' },
  { date: '2025-01-30', name: 'Spring Festival' },
  { date: '2025-01-31', name: 'Spring Festival' },
  { date: '2025-02-03', name: 'Spring Festival' },
  { date: '2025-02-04', name: 'Spring Festival' },
  { date: '2025-04-04', name: 'Qingming Festival' },
  { date: '2025-05-01', name: 'Labour Day' },
  { date: '2025-05-02', name: 'Labour Day' },
  { date: '2025-05-05', name: 'Labour Day' },
  { date: '2025-05-31', name: 'Dragon Boat Festival' },
  { date: '2025-06-02', name: 'Dragon Boat Festival' },
  { date: '2025-10-01', name: 'National Day' },
  { date: '2025-10-02', name: 'National Day' },
  { date: '2025-10-03', name: 'National Day' },
  { date: '2025-10-06', name: 'National Day' },
  { date: '2025-10-07', name: 'National Day' },
  { date: '2025-10-08', name: 'National Day' },
  // 2026
  { date: '2026-01-01', name: "New Year's Day" },
  { date: '2026-02-17', name: 'Spring Festival' },
  { date: '2026-02-18', name: 'Spring Festival' },
  { date: '2026-02-19', name: 'Spring Festival' },
  { date: '2026-02-20', name: 'Spring Festival' },
  { date: '2026-02-23', name: 'Spring Festival' },
  { date: '2026-02-24', name: 'Spring Festival' },
  { date: '2026-04-05', name: 'Qingming Festival' },
  { date: '2026-05-01', name: 'Labour Day' },
  { date: '2026-05-04', name: 'Labour Day' },
  { date: '2026-05-05', name: 'Labour Day' },
  { date: '2026-06-19', name: 'Dragon Boat Festival' },
  { date: '2026-10-01', name: 'National Day' },
  { date: '2026-10-02', name: 'National Day' },
  { date: '2026-10-05', name: 'National Day' },
  { date: '2026-10-06', name: 'National Day' },
  { date: '2026-10-07', name: 'National Day' },
  { date: '2026-10-08', name: 'National Day' },
  // 2027
  { date: '2027-01-01', name: "New Year's Day" },
  { date: '2027-02-06', name: 'Spring Festival' },
  { date: '2027-02-07', name: 'Spring Festival' },
  { date: '2027-02-08', name: 'Spring Festival' },
  { date: '2027-02-09', name: 'Spring Festival' },
  { date: '2027-02-12', name: 'Spring Festival' },
  { date: '2027-02-13', name: 'Spring Festival' },
  { date: '2027-04-05', name: 'Qingming Festival' },
  { date: '2027-05-01', name: 'Labour Day' },
  { date: '2027-06-09', name: 'Dragon Boat Festival' },
  { date: '2027-10-01', name: 'National Day' },
  { date: '2027-10-04', name: 'National Day' },
  { date: '2027-10-05', name: 'National Day' },
  { date: '2027-10-06', name: 'National Day' },
  { date: '2027-10-07', name: 'National Day' },
];

// Australia ASX holidays (static 2025-2027)
const AU_HOLIDAYS: Holiday[] = [
  // 2025
  { date: '2025-01-01', name: "New Year's Day" },
  { date: '2025-01-27', name: 'Australia Day (observed)' },
  { date: '2025-04-18', name: 'Good Friday' },
  { date: '2025-04-19', name: 'Easter Saturday' },
  { date: '2025-04-21', name: 'Easter Monday' },
  { date: '2025-04-25', name: 'ANZAC Day' },
  { date: '2025-06-09', name: "King's Birthday" },
  { date: '2025-12-25', name: 'Christmas Day' },
  { date: '2025-12-26', name: 'Boxing Day' },
  // 2026
  { date: '2026-01-01', name: "New Year's Day" },
  { date: '2026-01-26', name: 'Australia Day' },
  { date: '2026-04-03', name: 'Good Friday' },
  { date: '2026-04-04', name: 'Easter Saturday' },
  { date: '2026-04-06', name: 'Easter Monday' },
  { date: '2026-04-25', name: 'ANZAC Day' },
  { date: '2026-06-08', name: "King's Birthday" },
  { date: '2026-12-25', name: 'Christmas Day' },
  { date: '2026-12-26', name: 'Boxing Day' },
  { date: '2026-12-28', name: 'Boxing Day (observed)' },
  // 2027
  { date: '2027-01-01', name: "New Year's Day" },
  { date: '2027-01-26', name: 'Australia Day' },
  { date: '2027-03-26', name: 'Good Friday' },
  { date: '2027-03-27', name: 'Easter Saturday' },
  { date: '2027-03-29', name: 'Easter Monday' },
  { date: '2027-04-26', name: 'ANZAC Day (observed)' },
  { date: '2027-06-14', name: "King's Birthday" },
  { date: '2027-12-25', name: 'Christmas Day' },
  { date: '2027-12-27', name: 'Boxing Day (observed)' },
  { date: '2027-12-28', name: 'Christmas Day (observed)' },
];

const COMPUTED_YEARS = [2025, 2026, 2027];

function buildComputedHolidays(
  generator: (year: number) => Holiday[],
): Holiday[] {
  return COMPUTED_YEARS.flatMap(generator);
}

const HOLIDAY_MAP: Record<HolidaySource, Holiday[]> = {
  us: buildComputedHolidays(usHolidays),
  uk: buildComputedHolidays(ukHolidays),
  eu: buildComputedHolidays(euHolidays),
  jp: JP_HOLIDAYS,
  hk: HK_HOLIDAYS,
  cn: CN_HOLIDAYS,
  au: AU_HOLIDAYS,
};

export function getHoliday(
  source: HolidaySource,
  dateStr: string,
): Holiday | null {
  const holidays = HOLIDAY_MAP[source];
  return holidays.find((h) => h.date === dateStr) ?? null;
}
