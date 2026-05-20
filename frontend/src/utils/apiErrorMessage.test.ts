import { describe, expect, it } from 'vitest';

import { formatApiErrorDetail, getApiErrorMessage } from './apiErrorMessage';

describe('formatApiErrorDetail', () => {
  it('returns string detail unchanged', () => {
    expect(formatApiErrorDetail('Asset not found')).toBe('Asset not found');
  });

  it('formats pydantic field validation errors', () => {
    const detail = [
      {
        loc: ['body', 'buy_threshold'],
        msg: 'Input should be less than or equal to 1',
        input: 52,
      },
      {
        loc: ['body', 'sell_threshold'],
        msg: 'Input should be less than or equal to 1',
        input: 49,
      },
    ];
    expect(formatApiErrorDetail(detail)).toBe(
      'buy_threshold: Input should be less than or equal to 1; sell_threshold: Input should be less than or equal to 1',
    );
  });

  it('strips Value error prefix from model validator messages', () => {
    const detail = [
      {
        loc: ['body'],
        msg: 'Value error, start_date must be before end_date',
      },
    ];
    expect(formatApiErrorDetail(detail)).toBe('start_date must be before end_date');
  });
});

describe('getApiErrorMessage', () => {
  it('reads detail from axios-style response bodies', () => {
    expect(
      getApiErrorMessage({
        detail: [{ loc: ['body', 'entry_confirmation_bars'], msg: 'Input should be greater than or equal to 1' }],
      }),
    ).toBe('entry_confirmation_bars: Input should be greater than or equal to 1');
  });

  it('falls back when detail is missing', () => {
    expect(getApiErrorMessage(undefined, 'Network Error')).toBe('Network Error');
  });
});
