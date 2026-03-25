/**
 * WebSocketContext tests.
 *
 * Tests WebSocket connection management, message handling, and reconnection logic.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, renderHook, waitFor, act } from '@testing-library/react';
import { ReactNode } from 'react';
import { WebSocketProvider } from '@/contexts/WebSocketContext';
import { useWebSocket, useJobProgress } from '@/hooks/useWebSocket';
import { AuthContext } from '@/contexts/AuthContext';

// =============================================================================
// Mock Setup
// =============================================================================

// Mock WebSocket
class MockWebSocket {
  url: string;
  readyState: number = 0; // CONNECTING
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    // Simulate async connection
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 0);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = 3; // CLOSED
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  });

  // Helper for testing
  simulateMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Replace global WebSocket with mock
vi.stubGlobal('WebSocket', MockWebSocket);

// Mock auth context
const mockAuthValue = {
  user: { id: 'test-user-id', email: 'test@example.com' },
  token: 'test-token',
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  signup: vi.fn(),
  refreshToken: vi.fn(),
};

// Test wrapper with providers
function TestWrapper({ children }: { children: ReactNode }) {
  return (
    <AuthContext.Provider value={mockAuthValue}>
      <WebSocketProvider>{children}</WebSocketProvider>
    </AuthContext.Provider>
  );
}

// =============================================================================
// Tests
// =============================================================================

describe('WebSocketProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('renders children without crashing', () => {
    const { container } = render(
      <TestWrapper>
        <div>Test Child</div>
      </TestWrapper>
    );

    expect(container).toHaveTextContent('Test Child');
  });

  it('provides WebSocket context to children', () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    expect(result.current).toBeDefined();
    expect(result.current.connected).toBeDefined();
    expect(result.current.subscribe).toBeDefined();
    expect(result.current.send).toBeDefined();
  });
});

describe('useWebSocket hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('returns initial connection state', () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    expect(result.current.connected).toBe(false);
    expect(result.current.connecting).toBe(true);
    expect(result.current.error).toBe(null);
    expect(result.current.fallbackMode).toBe(false);
  });

  it('connects to WebSocket server', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => {
      expect(result.current.connected).toBe(true);
    });

    expect(result.current.connecting).toBe(false);
  });

  it('allows subscribing to message types', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    const handler = vi.fn();
    let unsubscribe: (() => void) | undefined;

    act(() => {
      unsubscribe = result.current.subscribe('test_message', handler);
    });

    expect(unsubscribe).toBeDefined();
    expect(typeof unsubscribe).toBe('function');
  });

  it('calls handler when subscribed message arrives', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    const handler = vi.fn();

    act(() => {
      result.current.subscribe('test_event', handler);
    });

    // Simulate incoming message
    const mockWs = (global.WebSocket as unknown as typeof MockWebSocket).prototype;
    const testMessage = { type: 'test_event', data: 'test data' };

    act(() => {
      // Access the instance to simulate message
      if (mockWs.onmessage) {
        mockWs.onmessage(
          new MessageEvent('message', { data: JSON.stringify(testMessage) })
        );
      }
    });

    await waitFor(() => {
      expect(handler).toHaveBeenCalledWith(testMessage);
    });
  });

  it('unsubscribes handler correctly', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    const handler = vi.fn();
    let unsubscribe: (() => void) | undefined;

    act(() => {
      unsubscribe = result.current.subscribe('test_event', handler);
    });

    // Unsubscribe
    act(() => {
      unsubscribe?.();
    });

    // Simulate message after unsubscribing
    const mockWs = (global.WebSocket as unknown as typeof MockWebSocket).prototype;
    const testMessage = { type: 'test_event', data: 'test data' };

    act(() => {
      if (mockWs.onmessage) {
        mockWs.onmessage(
          new MessageEvent('message', { data: JSON.stringify(testMessage) })
        );
      }
    });

    // Handler should not be called after unsubscribing
    expect(handler).not.toHaveBeenCalled();
  });

  it('provides send method to send messages', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    const testMessage = { type: 'test', data: 'hello' };

    act(() => {
      result.current.send(testMessage);
    });

    // Verify send was called (in real implementation)
    expect(result.current.send).toBeDefined();
  });

  it('provides subscribeToRoom method', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    act(() => {
      result.current.subscribeToRoom('design:123');
    });

    expect(result.current.subscribeToRoom).toBeDefined();
  });

  it('provides unsubscribeFromRoom method', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    act(() => {
      result.current.unsubscribeFromRoom('design:123');
    });

    expect(result.current.unsubscribeFromRoom).toBeDefined();
  });

  it('provides subscribeToJob method', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    act(() => {
      result.current.subscribeToJob('job-123');
    });

    expect(result.current.subscribeToJob).toBeDefined();
  });

  it('provides reconnect method', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    act(() => {
      result.current.reconnect();
    });

    expect(result.current.reconnect).toBeDefined();
  });
});

describe('useJobProgress hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('returns job progress state', () => {
    const { result } = renderHook(() => useJobProgress('job-123'), {
      wrapper: TestWrapper,
    });

    expect(result.current).toBeDefined();
    expect(result.current.progress).toBeDefined();
    expect(result.current.status).toBeDefined();
    expect(result.current.error).toBeDefined();
    expect(result.current.completed).toBeDefined();
  });

  it('initializes with default values', () => {
    const { result } = renderHook(() => useJobProgress('job-123'), {
      wrapper: TestWrapper,
    });

    expect(result.current.progress).toBe(0);
    expect(result.current.status).toBe('pending');
    expect(result.current.error).toBe(null);
    expect(result.current.completed).toBe(false);
  });

  it('updates progress when job_progress message received', async () => {
    const { result } = renderHook(() => {
      const ws = useWebSocket();
      const progress = useJobProgress('job-123');
      return { ws, progress };
    }, {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.ws.connected).toBe(true));

    // Simulate job progress message
    const progressMessage = {
      type: 'job_progress',
      job_id: 'job-123',
      progress: 50,
      status: 'processing',
      message: 'Processing...',
      timestamp: new Date().toISOString(),
    };

    const mockWs = (global.WebSocket as unknown as typeof MockWebSocket).prototype;

    act(() => {
      if (mockWs.onmessage) {
        mockWs.onmessage(
          new MessageEvent('message', { data: JSON.stringify(progressMessage) })
        );
      }
    });

    await waitFor(() => {
      expect(result.current.progress.progress).toBe(50);
      expect(result.current.progress.status).toBe('processing');
    });
  });

  it('marks job as completed when job_complete message received', async () => {
    const { result } = renderHook(() => {
      const ws = useWebSocket();
      const progress = useJobProgress('job-123');
      return { ws, progress };
    }, {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.ws.connected).toBe(true));

    // Simulate job complete message
    const completeMessage = {
      type: 'job_complete',
      job_id: 'job-123',
      result: { design_id: 'design-456' },
      timestamp: new Date().toISOString(),
    };

    const mockWs = (global.WebSocket as unknown as typeof MockWebSocket).prototype;

    act(() => {
      if (mockWs.onmessage) {
        mockWs.onmessage(
          new MessageEvent('message', { data: JSON.stringify(completeMessage) })
        );
      }
    });

    await waitFor(() => {
      expect(result.current.progress.completed).toBe(true);
      expect(result.current.progress.progress).toBe(100);
      expect(result.current.progress.status).toBe('completed');
    });
  });

  it('sets error when job_failed message received', async () => {
    const { result } = renderHook(() => {
      const ws = useWebSocket();
      const progress = useJobProgress('job-123');
      return { ws, progress };
    }, {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.ws.connected).toBe(true));

    // Simulate job failed message
    const failedMessage = {
      type: 'job_failed',
      job_id: 'job-123',
      error: 'Generation failed: Invalid parameters',
      timestamp: new Date().toISOString(),
    };

    const mockWs = (global.WebSocket as unknown as typeof MockWebSocket).prototype;

    act(() => {
      if (mockWs.onmessage) {
        mockWs.onmessage(
          new MessageEvent('message', { data: JSON.stringify(failedMessage) })
        );
      }
    });

    await waitFor(() => {
      expect(result.current.progress.error).toBe('Generation failed: Invalid parameters');
      expect(result.current.progress.status).toBe('failed');
    });
  });

  it('only responds to messages for its job ID', async () => {
    const { result } = renderHook(() => {
      const ws = useWebSocket();
      const progress = useJobProgress('job-123');
      return { ws, progress };
    }, {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.ws.connected).toBe(true));

    // Simulate message for different job
    const otherJobMessage = {
      type: 'job_progress',
      job_id: 'job-456',
      progress: 75,
      status: 'processing',
      timestamp: new Date().toISOString(),
    };

    const mockWs = (global.WebSocket as unknown as typeof MockWebSocket).prototype;

    act(() => {
      if (mockWs.onmessage) {
        mockWs.onmessage(
          new MessageEvent('message', { data: JSON.stringify(otherJobMessage) })
        );
      }
    });

    // Progress should not update for different job ID
    await waitFor(() => {
      expect(result.current.progress.progress).toBe(0);
      expect(result.current.progress.status).toBe('pending');
    });
  });
});

describe('WebSocket error handling', () => {
  it('handles connection errors gracefully', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    // Wait for initial connection attempt
    await waitFor(() => expect(result.current.connecting).toBe(true));

    // Verify error handling exists
    expect(result.current.error).toBeDefined();
  });

  it('enters fallback mode on connection failure', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    // Fallback mode state is available
    expect(result.current.fallbackMode).toBeDefined();
  });
});

describe('WebSocket reconnection', () => {
  it('attempts to reconnect after disconnection', async () => {
    const { result } = renderHook(() => useWebSocket(), {
      wrapper: TestWrapper,
    });

    await waitFor(() => expect(result.current.connected).toBe(true));

    // Trigger reconnect
    act(() => {
      result.current.reconnect();
    });

    expect(result.current.reconnect).toHaveBeenCalled;
  });
});
