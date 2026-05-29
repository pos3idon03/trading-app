import { useCallback, useEffect, useState } from 'react';
import { executionApi } from '../api/endpoints';
import type { DeploymentOverview } from '../api/executionTypes';
import { mergeOverviewWithActivity } from '../utils/tradingOverview';
import { useExecutionActivityStream } from './useExecutionActivityStream';

const POLL_MS = 30_000;

export function useTradingOverview() {
  const [deployments, setDeployments] = useState<DeploymentOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { events, connectionState } = useExecutionActivityStream();

  const load = useCallback(async () => {
    try {
      const response = await executionApi.getOverview();
      setDeployments(response.deployments);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load overview');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => {
      void load();
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  const rows = mergeOverviewWithActivity(deployments, events);

  return {
    deployments: rows,
    loading,
    error,
    connectionState,
    reload: load,
  };
}
