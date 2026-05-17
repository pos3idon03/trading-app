/**
 * Auto-starts Alpaca stock + crypto streams for running auto-trading assets on the Live page.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { liveApi } from '../api/endpoints';
import type { ExecutionAssetMonitor, StreamStatusResponse } from '../api/types';
import { isSymbolSubscribed } from '../utils/streamSymbolMatch';

const STREAM_STATUS_INTERVAL_MS = 8_000;
const DEFAULT_TIMEFRAMES = ['5m', '30m', '1h', '4h', '1d'];

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

function symbolsMatchSubscribed(
  requested: string[],
  subscribed: string[],
): boolean {
  if (requested.length === 0) return true;
  return requested.every((s) => isSymbolSubscribed(s, subscribed));
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
  const [streamStarting, setStreamStarting] = useState(false);
  const startInFlightRef = useRef(false);
  const streamSymbols = streamSymbolsFromMonitors(monitors);
  const streamSymbolsKey = streamSymbols.join(',');

  const refreshStatus = useCallback(() => {
    return liveApi.getStatus().then(setStreamStatus).catch(() => {});
  }, []);

  useEffect(() => {
    refreshStatus();
    const interval = setInterval(refreshStatus, STREAM_STATUS_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refreshStatus]);

  const tryStartStream = useCallback(async () => {
    const symbols = streamSymbolsKey ? streamSymbolsKey.split(',') : [];
    if (symbols.length === 0) return;

    const status = await liveApi.getStatus().catch(() => null);
    if (status) setStreamStatus(status);

    if (
      status?.connected
      && symbolsMatchSubscribed(symbols, status.subscribed_symbols)
    ) {
      return;
    }

    if (startInFlightRef.current) return;
    startInFlightRef.current = true;
    setStreamStarting(true);

    try {
      const next = await liveApi.startStream({
        symbols,
        timeframes: DEFAULT_TIMEFRAMES,
      });
      setStreamStatus(next);
      if (next.connected) {
        onStreamEventRef.current?.(
          `Alpaca stream connected | ${next.subscribed_symbols.join(', ')}`,
          'info',
        );
      } else if (next.error) {
        onStreamEventRef.current?.(`Alpaca stream failed | ${next.error}`, 'error');
      }
    } catch (e) {
      const msg = (e as Error).message;
      onStreamEventRef.current?.(`Alpaca stream failed | ${msg}`, 'error');
    } finally {
      startInFlightRef.current = false;
      setStreamStarting(false);
    }
  }, [streamSymbolsKey]);

  useEffect(() => {
    tryStartStream();
  }, [tryStartStream]);

  return {
    streamStatus,
    streamStarting,
    streamSymbols,
    refreshStatus,
  };
}
