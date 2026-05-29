import { ingestionApi } from '../api/endpoints';
import type { Job } from '../api/types';

const POLL_MS = 3000;
const TERMINAL = new Set(['completed', 'failed', 'partial', 'cancelled']);

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export async function pollIngestionJob(
  jobId: string,
  onProgress?: (job: Job) => void,
): Promise<Job> {
  while (true) {
    const job = await ingestionApi.getJob(jobId);
    onProgress?.(job);
    if (TERMINAL.has(job.status)) {
      if (job.status === 'failed') {
        throw new Error(job.error_message ?? 'Background job failed.');
      }
      if (job.status === 'cancelled') {
        throw new Error(job.error_message ?? 'Job was cancelled.');
      }
      return job;
    }
    await sleep(POLL_MS);
  }
}

export async function waitForJobResult<T>(
  jobId: string,
  onProgress?: (job: Job) => void,
): Promise<T> {
  const job = await pollIngestionJob(jobId, onProgress);
  return (job.result ?? {}) as T;
}

export async function enqueueAndWait<T>(
  enqueue: () => Promise<{ job_id: string }>,
  onProgress?: (job: Job) => void,
): Promise<T> {
  const { job_id } = await enqueue();
  return waitForJobResult<T>(job_id, onProgress);
}
