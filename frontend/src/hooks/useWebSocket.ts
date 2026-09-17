import { useEffect, useRef, useState } from 'react';

interface WebSocketMessage {
  type: string;
  [key: string]: any;
}

export const useWebSocket = (guildId: string | null, onMessage?: (message: WebSocketMessage) => void) => {
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (!guildId) return;

    const wsUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000/ws/${guildId}`;
    const connect = () => {
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);

        // Ping каждые 30 секунд для keep-alive
        const pingInterval = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send('ping');
          }
        }, 30000);

        const currentWs = ws.current;
        if (currentWs) {
          currentWs.addEventListener('close', () => {
            clearInterval(pingInterval);
          });
        }
      };

      ws.current.onmessage = (event) => {
        if (event.data === 'pong') return;

        try {
          const message = JSON.parse(event.data);
          onMessage?.(message);
        } catch (error) {
          console.error('Failed to parse WebSocket message', error);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error', error);
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);

        // Переподключение через 5 секунд
        reconnectTimeout.current = setTimeout(() => {
          console.log('Reconnecting WebSocket...');
          connect();
        }, 5000);
      };
    };

    connect();

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      ws.current?.close();
    };
  }, [guildId]);

  return { isConnected };
};
