import { describe, it, expect } from 'vitest';
import { resolveLivePollMs } from '../hooks/useExecutionMonitor';

describe('resolveLivePollMs', () => {
  it('uses timeframe interval when no cap', () => {
    expect(resolveLivePollMs('5m')).toBe(300_000);
  });

  it('caps 5m timeframe to 60s on live terminal page', () => {
    expect(resolveLivePollMs('5m', 60_000)).toBe(60_000);
  });

  it('never polls faster than 60s', () => {
    expect(resolveLivePollMs('1m', 30_000)).toBe(60_000);
  });
});
