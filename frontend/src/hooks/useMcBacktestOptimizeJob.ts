import { useCallback, useEffect, useRef, useState } from 'react';
import { simulationApi } from '../api/endpoints';
import type {
  McBacktestOptimizeJobStatusResponse,
  McBacktestOptimizeRequest,
  McBacktestOptimizeResponse,
} from '../api/types';

const POLL_INTERVAL_MS = 2000;

export function useMcBacktestOptimizeJob() {
  const [loading, setLoading] = useState(false);
  const [progressPct, setProgressPct] = useState(0);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [result, setResult] = useState<McBacktestOptimizeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    setLoading(false);
    setProgressPct(0);
    setProgressMessage(null);
    setResult(null);
    setError(null);
  }, [stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const applyStatus = useCallback(
    (status: McBacktestOptimizeJobStatusResponse) => {
      setProgressPct(status.progress_pct);
      setProgressMessage(status.progress_message ?? null);
      if (status.status === 'done') {
        stopPolling();
        setResult(status);
        setLoading(false);
      } else if (status.status === 'error') {
        stopPolling();
        setError(status.error_message ?? 'Optimization failed');
        setLoading(false);
      }
    },
    [stopPolling],
  );

  const start = useCallback(
    async (req: McBacktestOptimizeRequest) => {
      reset();
      setLoading(true);
      setError(null);
      try {
        const { job_id: jobId } = await simulationApi.optimizeBacktest(req);

        const pollOnce = async (): Promise<boolean> => {
          const status = await simulationApi.getOptimizeBacktestJob(jobId);
          applyStatus(status);
          return status.status === 'pending' || status.status === 'running';
        };

        const stillRunning = await pollOnce();
        if (stillRunning) {
          pollRef.current = setInterval(() => {
            pollOnce()
              .then((running) => {
                if (!running) stopPolling();
              })
              .catch((err: unknown) => {
                stopPolling();
                setError(err instanceof Error ? err.message : 'Polling failed');
                setLoading(false);
              });
          }, POLL_INTERVAL_MS);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start optimization');
        setLoading(false);
      }
    },
    [applyStatus, reset, stopPolling],
  );

  return {
    loading,
    progressPct,
    progressMessage,
    result,
    error,
    start,
    reset,
  };
}
