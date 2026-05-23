import { describe, expect, it, vi, afterEach } from 'vitest';

import { ingestionApi } from '../api/endpoints';
import { pollIngestionJob } from '../hooks/useMlJob';

describe('pollIngestionJob', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns when job completes on first poll', async () => {
    vi.spyOn(ingestionApi, 'getJob').mockResolvedValueOnce({
      id: '1',
      job_type: 'ml_data_preview',
      status: 'completed',
      progress: 100,
      created_at: '2024-01-01T00:00:00Z',
      result: { bar_counts: { '1d': 10 } },
    });

    const job = await pollIngestionJob('1');

    expect(job.status).toBe('completed');
    expect(job.result).toEqual({ bar_counts: { '1d': 10 } });
  });

  it('throws when job fails', async () => {
    vi.spyOn(ingestionApi, 'getJob').mockResolvedValueOnce({
      id: '1',
      job_type: 'ml_data_preview',
      status: 'failed',
      progress: 100,
      created_at: '2024-01-01T00:00:00Z',
      error_message: 'boom',
    });

    await expect(pollIngestionJob('1')).rejects.toThrow('boom');
  });
});
