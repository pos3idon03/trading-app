import { useEffect, useRef, useState } from 'react';
import { executionActivityWsUrl, executionApi } from '../api/endpoints';
import type { ExecutionActivityEvent } from '../api/executionTypes';
import { mergeActivityEvents } from '../utils/tradingDeployments';

type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export function useExecutionActivityStream(options?: {
  deploymentId?: string | null;
  symbol?: string | null;
}) {
  const [events, setEvents] = useState<ExecutionActivityEvent[]>([]);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const reconnectTimer = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    let socket: WebSocket | null = null;

    const loadHistory = async () => {
      const response = await executionApi.listEvaluations({
        deployment_id: options?.deploymentId ?? undefined,
        symbol: options?.symbol ?? undefined,
        limit: 50,
      });
      if (!cancelled) {
        setEvents(response.evaluations);
      }
    };

    const connect = () => {
      setConnectionState((state) => (state === 'connected' ? 'connected' : 'connecting'));
      socket = new WebSocket(executionActivityWsUrl());

      socket.onopen = () => {
        if (cancelled) return;
        setConnectionState('connected');
      };

      socket.onmessage = (message) => {
        if (cancelled) return;
        try {
          const payload = JSON.parse(message.data) as ExecutionActivityEvent;
          if (options?.deploymentId && payload.deployment_id !== options.deploymentId) return;
          if (options?.symbol && payload.symbol !== options.symbol.toUpperCase()) return;
          setEvents((current) => mergeActivityEvents(current, [payload]));
        } catch {
          // ignore malformed payloads
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        setConnectionState('reconnecting');
        reconnectTimer.current = window.setTimeout(connect, 3000);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    void loadHistory().finally(() => {
      if (!cancelled) connect();
    });

    return () => {
      cancelled = true;
      if (reconnectTimer.current) {
        window.clearTimeout(reconnectTimer.current);
      }
      socket?.close();
      setConnectionState('disconnected');
    };
  }, [options?.deploymentId, options?.symbol]);

  return { events, connectionState };
}
