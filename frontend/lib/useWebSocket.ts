"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { StreamFrame } from "./api";
import { fetchHistory, wsTelemetryUrl } from "./api";

const MAX_HISTORY = 1800;
const RECONNECT_DELAY_MS = 2000;

export function useTelemetryStream(enabled = true) {
  const [connected, setConnected] = useState(false);
  const [frame, setFrame] = useState<StreamFrame | null>(null);
  const [history, setHistory] = useState<StreamFrame[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!enabled) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(wsTelemetryUrl());
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as StreamFrame;
        setFrame(data);
        setHistory((prev) => {
          if (prev[prev.length - 1]?.telemetry.timestamp === data.telemetry.timestamp) {
            return prev;
          }
          const next = [...prev, data];
          return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
        });
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      setConnected(false);
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    ws.onerror = () => ws.close();
  }, [enabled]);

  useEffect(() => {
    if (!enabled) {
      setConnected(false);
      setFrame(null);
      setHistory([]);
      wsRef.current?.close();
      return;
    }

    let active = true;
    fetchHistory(MAX_HISTORY)
      .then((initialHistory) => {
        if (!active || initialHistory.length === 0) return;
        setHistory(initialHistory);
        setFrame(initialHistory[initialHistory.length - 1] ?? null);
      })
      .catch(() => {
        // keep websocket-only live mode when history bootstrap is unavailable
      });

    connect();
    return () => {
      active = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect, enabled]);

  const send = useCallback((action: string, value: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action, value }));
    }
  }, []);

  return { connected, frame, history, send };
}
