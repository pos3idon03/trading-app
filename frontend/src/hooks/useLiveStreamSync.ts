/**
 * Polls backend Alpaca stream status for running auto-trading assets.
 * Stream start/stop is managed by the backend when auto-trading runs.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { liveApi } from '../api/endpoints';
import type { ExecutionAssetMonitor, StreamStatusResponse } from '../api/types';

const STREAM_STATUS_INTERVAL_MS = 8_000;

function streamSymbolsFromMonitors(monitors: ExecutionAssetMonitor[]): string[] {
  const seen = new Set<string>();
  const symbols: string[] = [];
  for (const m of monitors) {
    const sym = m.symbol.toUpperCase();
    if (seen.has(sym)) continue;
    seen.add(sym);
    symbols.push(sym);
  }
  return symbols.sort();
}

export interface LiveStreamSyncOptions {
  onStreamEvent?: (message: string, severity?: 'info' | 'warn' | 'error') => void;
}

export function useLiveStreamSync(
  monitors: ExecutionAssetMonitor[],
  options: LiveStreamSyncOptions = {},
) {
  const onStreamEventRef = useRef(options.onStreamEvent);
  onStreamEventRef.current = options.onStreamEvent;

  const [streamStatus, setStreamStatus] = useState<StreamStatusResponse | null>(null);
  const streamSymbols = streamSymbolsFromMonitors(monitors);
  const prevConnectedRef = useRef<boolean | null>(null);

  const refreshStatus = useCallback(() => {
    return liveApi.getStatus().then(setStreamStatus).catch(() => {});
  }, []);

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, STREAM_STATUS_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refreshStatus]);

  useEffect(() => {
    if (!streamStatus) return;

    const wasConnected = prevConnectedRef.current;
    const isConnected = streamStatus.connected;
    prevConnectedRef.current = isConnected;

    if (wasConnected === null && isConnected && streamSymbols.length > 0) {
      onStreamEventRef.current?.(
        `Alpaca stream connected (backend) | ${streamStatus.subscribed_symbols.join(', ')}`,
        'info',
      );
    } else if (wasConnected === true && !isConnected && streamSymbols.length > 0) {
      const detail = streamStatus.error ? ` | ${streamStatus.error}` : '';
      onStreamEventRef.current?.(`Alpaca stream disconnected${detail}`, 'warn');
    }
  }, [streamStatus, streamSymbols.length]);

  return {
    streamStatus,
    streamStarting: false,
    streamSymbols,
    refreshStatus,
  };
}
