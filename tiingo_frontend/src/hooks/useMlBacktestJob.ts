import { useCallback, useState } from 'react';
import { mlBacktestApi } from '../api/endpoints';
import type { Job } from '../api/types';
import type { MlBacktestResultsResponse } from '../api/mlBacktestTypes';
import { buildMlRunRequest, type BuildMlRunRequestInput } from '../utils/mlRunRequest';

function extractErrorMessage(err: unknown, fallback = 'ML backtest failed.'): string {
  if (err instanceof Error && err.message) {
    return err.message;
  }
  if (typeof err === 'object' && err !== null && 'response' in err) {
    const data = (err as { response?: { data?: { detail?: string } } }).response?.data;
    if (typeof data?.detail === 'string') {
      return data.detail;
    }
  }
  return fallback;
}

export function useMlBacktestJob() {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runBacktest = useCallback(
    async (
      input: BuildMlRunRequestInput,
      onProgress?: (job: Job) => void,
    ): Promise<MlBacktestResultsResponse> => {
      setRunning(true);
      setError(null);
      setProgress(null);
      try {
        const request = buildMlRunRequest(input);
        const run = await mlBacktestApi.run(request, (job) => {
          setProgress(job.progress ?? null);
          onProgress?.(job);
        });
        return await mlBacktestApi.getResults(run.id);
      } catch (err: unknown) {
        const message = extractErrorMessage(err);
        setError(message);
        throw err;
      } finally {
        setRunning(false);
        setProgress(null);
      }
    },
    [],
  );

  const clearError = useCallback(() => setError(null), []);

  return { running, progress, error, runBacktest, clearError, setError };
}
