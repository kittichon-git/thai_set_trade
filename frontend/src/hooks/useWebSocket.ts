// useWebSocket.ts — WebSocket connection hook with auto-reconnect
import { useRef, useState, useEffect, useCallback } from 'react';
import type { DashboardPayload, WSMessage } from '../types';

type Status = 'connecting' | 'connected' | 'disconnected';

interface UseWebSocketReturn {
  payload: DashboardPayload | null;
  status: Status;
  lastUpdate: string | null;
  forceReconnect: () => void;
}

export function useWebSocket(url: string): UseWebSocketReturn {
  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [status, setStatus] = useState<Status>('connecting');
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    setStatus('connecting');

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        // Reset backoff on successful connection
        backoffRef.current = 1000;
        setStatus('connected');
      };

      ws.onmessage = (e: MessageEvent) => {
        if (!mountedRef.current) return;
        try {
          const msg: WSMessage = JSON.parse(e.data as string);
          if (msg.type === 'snapshot' && msg.payload) {
            setPayload(msg.payload);
            setLastUpdate(new Date().toLocaleTimeString('th-TH'));
          }
          // ping messages: no state update, just keep-alive acknowledgment
        } catch {
          // Ignore malformed messages
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setStatus('disconnected');
        // Exponential backoff: 1s -> 2s -> 4s -> ... -> 30s max
        const delay = backoffRef.current;
        timerRef.current = setTimeout(() => {
          if (!mountedRef.current) return;
          backoffRef.current = Math.min(backoffRef.current * 2, 30000);
          connect();
        }, delay);
      };

      ws.onerror = () => {
        // onerror always precedes onclose, just close to trigger reconnect logic
        ws.close();
      };
    } catch {
      // WebSocket constructor error (e.g., invalid URL)
      timerRef.current = setTimeout(() => {
        if (!mountedRef.current) return;
        backoffRef.current = Math.min(backoffRef.current * 2, 30000);
        connect();
      }, backoffRef.current);
    }
  }, [url]);

  const forceReconnect = useCallback(() => {
    clearTimeout(timerRef.current);
    wsRef.current?.close();
    backoffRef.current = 1000;
    connect();
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(timerRef.current);
      wsRef.current?.close();
    };
  }, [connect]);

  return { payload, status, lastUpdate, forceReconnect };
}
