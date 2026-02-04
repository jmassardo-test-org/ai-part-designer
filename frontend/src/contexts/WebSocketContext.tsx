/**
 * WebSocket context for real-time updates.
 *
 * Provides WebSocket connection management and message handling
 * throughout the application.
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
  ReactNode,
} from 'react';
import { useAuth } from '@/contexts/AuthContext';

// =============================================================================
// Types
// =============================================================================

export interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

export interface JobProgressMessage extends WebSocketMessage {
  type: 'job_progress';
  job_id: string;
  progress: number;
  status: string;
  message?: string;
  timestamp: string;
}

export interface JobCompleteMessage extends WebSocketMessage {
  type: 'job_complete';
  job_id: string;
  result?: Record<string, unknown>;
  timestamp: string;
}

export interface JobFailedMessage extends WebSocketMessage {
  type: 'job_failed';
  job_id: string;
  error: string;
  timestamp: string;
}

export type MessageHandler = (message: WebSocketMessage) => void;

interface WebSocketContextType {
  /** Whether WebSocket is connected */
  connected: boolean;
  /** Whether WebSocket is connecting */
  connecting: boolean;
  /** Connection error message, if any */
  error: string | null;
  /** Whether WebSocket is in fallback mode (polling instead of real-time) */
  fallbackMode: boolean;
  /** Subscribe to messages of a specific type */
  subscribe: (type: string, handler: MessageHandler) => () => void;
  /** Subscribe to a room/topic */
  subscribeToRoom: (room: string) => void;
  /** Unsubscribe from a room/topic */
  unsubscribeFromRoom: (room: string) => void;
  /** Subscribe to job updates */
  subscribeToJob: (jobId: string) => void;
  /** Send a message through WebSocket */
  send: (message: WebSocketMessage) => void;
  /** Reconnect WebSocket */
  reconnect: () => void;
}

// =============================================================================
// Context
// =============================================================================

const WebSocketContext = createContext<WebSocketContextType | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface WebSocketProviderProps {
  children: ReactNode;
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const { token, user } = useAuth();
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallbackMode, setFallbackMode] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef<Map<string, Set<MessageHandler>>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const maxReconnectAttempts = 5; // Enter fallback mode after 5 failed attempts

  const getWsUrl = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // VITE_API_URL may include /api/v1, so we need to handle that
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    // Remove protocol and any trailing path for base host
    const hostWithPath = apiUrl.replace(/^https?:\/\//, '');
    // Extract just the host:port, removing any path
    const host = hostWithPath.split('/')[0] || 'localhost:8000';
    return `${protocol}//${host}/api/v1/ws?token=${token}`;
  }, [token]);

  const connect = useCallback(() => {
    if (!token || !user) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (fallbackMode) return; // Don't try to connect in fallback mode

    setConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(getWsUrl());

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setConnected(true);
        setConnecting(false);
        setError(null);
        setFallbackMode(false);
        reconnectAttemptRef.current = 0;

        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected', event.code, event.reason);
        setConnected(false);
        setConnecting(false);

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
        }

        // Check if we should enter fallback mode
        if (reconnectAttemptRef.current >= maxReconnectAttempts) {
          console.log('[WebSocket] Max reconnect attempts reached, entering fallback mode');
          setFallbackMode(true);
          setError('Real-time updates unavailable. Refreshing may be required for updates.');
          return;
        }

        // Reconnect with exponential backoff
        if (event.code !== 4001 && token) {
          const delay = Math.min(1000 * 2 ** reconnectAttemptRef.current, 30000);
          reconnectAttemptRef.current++;
          console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.onerror = () => {
        // Don't log the full error event as it doesn't contain useful info
        // The onclose handler will be called after this with more details
        console.log('[WebSocket] Connection error occurred');
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          
          // Handle pong silently
          if (message.type === 'pong') return;

          // Dispatch to handlers
          const handlers = handlersRef.current.get(message.type);
          if (handlers) {
            handlers.forEach((handler) => {
              try {
                handler(message);
              } catch (e) {
                console.error('[WebSocket] Handler error:', e);
              }
            });
          }

          // Also dispatch to wildcard handlers
          const wildcardHandlers = handlersRef.current.get('*');
          if (wildcardHandlers) {
            wildcardHandlers.forEach((handler) => {
              try {
                handler(message);
              } catch (e) {
                console.error('[WebSocket] Wildcard handler error:', e);
              }
            });
          }
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e);
        }
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('[WebSocket] Connection error:', e);
      setConnecting(false);
    }
  }, [token, user, getWsUrl]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  }, []);

  // Connect when authenticated
  useEffect(() => {
    if (token && user) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [token, user, connect, disconnect]);

  const subscribe = useCallback((type: string, handler: MessageHandler) => {
    if (!handlersRef.current.has(type)) {
      handlersRef.current.set(type, new Set());
    }
    handlersRef.current.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      handlersRef.current.get(type)?.delete(handler);
    };
  }, []);

  const subscribeToRoom = useCallback((room: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe', room }));
    }
  }, []);

  const unsubscribeFromRoom = useCallback((room: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'unsubscribe', room }));
    }
  }, []);

  const subscribeToJob = useCallback((jobId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'subscribe_job', job_id: jobId }));
    }
  }, []);

  const send = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send - not connected');
    }
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttemptRef.current = 0;
    setFallbackMode(false);
    setError(null);
    connect();
  }, [disconnect, connect]);

  const value: WebSocketContextType = {
    connected,
    connecting,
    error,
    fallbackMode,
    subscribe,
    subscribeToRoom,
    unsubscribeFromRoom,
    subscribeToJob,
    send,
    reconnect,
  };

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

export function useWebSocket(): WebSocketContextType {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}

// =============================================================================
// Specialized Hooks
// =============================================================================

/**
 * Hook to subscribe to job progress updates.
 */
export function useJobProgress(
  jobId: string | null,
  onProgress?: (progress: number, status: string, message?: string) => void,
  onComplete?: (result?: Record<string, unknown>) => void,
  onFailed?: (error: string) => void,
) {
  const { subscribe, subscribeToJob } = useWebSocket();

  useEffect(() => {
    if (!jobId) return;

    // Subscribe to job room
    subscribeToJob(jobId);

    // Set up message handlers
    const unsubProgress = subscribe('job_progress', (msg) => {
      const message = msg as JobProgressMessage;
      if (message.job_id === jobId && onProgress) {
        onProgress(message.progress, message.status, message.message);
      }
    });

    const unsubComplete = subscribe('job_complete', (msg) => {
      const message = msg as JobCompleteMessage;
      if (message.job_id === jobId && onComplete) {
        onComplete(message.result);
      }
    });

    const unsubFailed = subscribe('job_failed', (msg) => {
      const message = msg as JobFailedMessage;
      if (message.job_id === jobId && onFailed) {
        onFailed(message.error);
      }
    });

    return () => {
      unsubProgress();
      unsubComplete();
      unsubFailed();
    };
  }, [jobId, subscribe, subscribeToJob, onProgress, onComplete, onFailed]);
}

export default WebSocketProvider;
