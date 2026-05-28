import { describe, expect, it } from 'vitest';

import { formatOutcome, mergeActivityEvents } from '../utils/tradingDeployments';

describe('trading activity utils', () => {
  it('formats outcome labels', () => {
    expect(formatOutcome('order_submitted')).toBe('order submitted');
  });

  it('merges activity events by id newest first', () => {
    const merged = mergeActivityEvents(
      [{ id: '1', created_at: '2026-05-28T09:00:00Z' }],
      [{ id: '2', created_at: '2026-05-28T10:00:00Z' }, { id: '1', created_at: '2026-05-28T11:00:00Z' }],
    );
    expect(merged.map((item) => item.id)).toEqual(['1', '2']);
  });
});
