/**
 * useWebSocket hook.
 *
 * Re-exports from WebSocketContext for convenient imports.
 */

export {
  useWebSocket,
  useJobProgress,
  type WebSocketMessage,
  type JobProgressMessage,
  type JobCompleteMessage,
  type JobFailedMessage,
} from '@/contexts/WebSocketContext';
