/**
 * Accumulates terminal-style activity lines from execution monitor snapshots.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { liveApi } from '../api/endpoints';
import type { ExecutionAssetMonitor, StreamStatusResponse } from '../api/types';
import type { ExecutionLogLine } from '../utils/executionActivityLog';
import {
  buildBarSourceMap,
  diffMonitors,
  snapshotMonitors,
} from '../utils/executionActivityLog';

const MAX_LINES = 1500;
const STREAM_STATUS_INTERVAL_MS = 8_000;

export interface ExecutionActivityLogOptions {
  logPollHeartbeat?: boolean;
  logPollEvaluations?: boolean;
  /** When set, skips internal status polling (e.g. useLiveStreamSync owns status). */
  streamStatus?: StreamStatusResponse | null;
}

export function useExecutionActivityLog(
  monitors: ExecutionAssetMonitor[],
  options: ExecutionActivityLogOptions = {},
) {
  const {
    logPollHeartbeat = false,
    logPollEvaluations = false,
    streamStatus: externalStreamStatus,
  } = options;
  const [lines, setLines] = useState<ExecutionLogLine[]>([]);
  const [paused, setPaused] = useState(false);
  const [internalStreamStatus, setInternalStreamStatus] = useState<StreamStatusResponse | null>(null);
  const streamStatus = externalStreamStatus !== undefined
    ? externalStreamStatus
    : internalStreamStatus;

  const prevRef = useRef<Map<number, ExecutionAssetMonitor>>(new Map());
  const lineCounterRef = useRef(0);
  const pausedRef = useRef(paused);

  useEffect(() => {
    pausedRef.current = paused;
  }, [paused]);

  useEffect(() => {
    if (externalStreamStatus !== undefined) return;
    const fetchStatus = () => {
      liveApi.getStatus().then(setInternalStreamStatus).catch(() => {});
    };
    fetchStatus();
    const interval = setInterval(fetchStatus, STREAM_STATUS_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [externalStreamStatus]);

  const appendLines = useCallback((incoming: ExecutionLogLine[]) => {
    if (incoming.length === 0 || pausedRef.current) return;
    setLines((prev) => {
      const merged = [...prev, ...incoming];
      return merged.length > MAX_LINES ? merged.slice(-MAX_LINES) : merged;
    });
  }, []);

  useEffect(() => {
    const symbols = monitors.map((m) => m.symbol);
    const barSourceBySymbol = buildBarSourceMap(symbols, streamStatus);
    const nowISO = new Date().toISOString();
    const ctx = {
      barSourceBySymbol,
      nowISO,
      nextLineId: () => {
        lineCounterRef.current += 1;
        return `${nowISO}-${lineCounterRef.current}`;
      },
    };

    const prev = prevRef.current;
    const hasBaseline = prev.size > 0;
    if (hasBaseline) {
      const newLines = diffMonitors(prev, monitors, ctx, {
        logPollHeartbeat,
        logPollEvaluations,
      });
      appendLines(newLines);
    }

    prevRef.current = snapshotMonitors(monitors);
  }, [monitors, streamStatus, appendLines, logPollHeartbeat, logPollEvaluations]);

  const appendSystemLine = useCallback((text: string, severity: 'info' | 'warn' | 'error' = 'info') => {
    const nowISO = new Date().toISOString();
    appendLines([{
      id: `system-${nowISO}-${lineCounterRef.current++}`,
      tsISO: nowISO,
      symbol: 'SYSTEM',
      severity,
      text,
    }]);
  }, [appendLines]);

  const clear = useCallback(() => {
    setLines([]);
    lineCounterRef.current = 0;
  }, []);

  const togglePaused = useCallback(() => {
    setPaused((p) => !p);
  }, []);

  return { lines, clear, paused, setPaused, togglePaused, streamStatus, appendSystemLine };
}
