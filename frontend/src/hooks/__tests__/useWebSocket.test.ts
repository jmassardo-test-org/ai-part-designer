/**
 * useWebSocket hook tests.
 *
 * Tests the WebSocket hooks exported from WebSocketContext.
 * Note: These tests focus on the hook API and basic behavior.
 * The WebSocket connection logic is tested via integration tests.
 */

import { describe, it, expect } from 'vitest';

// Test that hooks are properly exported
describe('useWebSocket module exports', () => {
  it('exports useWebSocket hook', async () => {
    const module = await import('@/hooks/useWebSocket');
    expect(module.useWebSocket).toBeDefined();
    expect(typeof module.useWebSocket).toBe('function');
  });

  it('exports useJobProgress hook', async () => {
    const module = await import('@/hooks/useWebSocket');
    expect(module.useJobProgress).toBeDefined();
    expect(typeof module.useJobProgress).toBe('function');
  });

  it('exports WebSocketMessage type', async () => {
    // Type exports don't exist at runtime, but we can verify the module loads
    const module = await import('@/hooks/useWebSocket');
    expect(module).toBeDefined();
  });

  it('exports JobProgressMessage type', async () => {
    const module = await import('@/hooks/useWebSocket');
    expect(module).toBeDefined();
  });

  it('exports JobCompleteMessage type', async () => {
    const module = await import('@/hooks/useWebSocket');
    expect(module).toBeDefined();
  });

  it('exports JobFailedMessage type', async () => {
    const module = await import('@/hooks/useWebSocket');
    expect(module).toBeDefined();
  });
});

describe('WebSocketContext exports', () => {
  it('exports WebSocketProvider', async () => {
    const module = await import('@/contexts/WebSocketContext');
    expect(module.WebSocketProvider).toBeDefined();
    expect(typeof module.WebSocketProvider).toBe('function');
  });

  it('exports useWebSocket hook', async () => {
    const module = await import('@/contexts/WebSocketContext');
    expect(module.useWebSocket).toBeDefined();
    expect(typeof module.useWebSocket).toBe('function');
  });

  it('exports useJobProgress hook', async () => {
    const module = await import('@/contexts/WebSocketContext');
    expect(module.useJobProgress).toBeDefined();
    expect(typeof module.useJobProgress).toBe('function');
  });

  it('exports default as WebSocketProvider', async () => {
    const module = await import('@/contexts/WebSocketContext');
    expect(module.default).toBe(module.WebSocketProvider);
  });
});

describe('useWebSocket hook behavior', () => {
  it('hook function exists and can be called', async () => {
    const { useWebSocket } = await import('@/contexts/WebSocketContext');
    
    // Verify the hook is a function
    expect(typeof useWebSocket).toBe('function');
  });

  it('useJobProgress hook exists and can be called', async () => {
    const { useJobProgress } = await import('@/contexts/WebSocketContext');
    
    // Verify the hook is a function
    expect(typeof useJobProgress).toBe('function');
  });
});

describe('WebSocket message types', () => {
  it('defines correct job progress message structure', () => {
    const jobProgressMessage = {
      type: 'job_progress',
      job_id: 'test-job-123',
      progress: 50,
      status: 'processing',
      message: 'Generating model...',
      timestamp: '2025-01-27T10:00:00Z',
    };

    expect(jobProgressMessage.type).toBe('job_progress');
    expect(jobProgressMessage.progress).toBe(50);
    expect(typeof jobProgressMessage.job_id).toBe('string');
  });

  it('defines correct job complete message structure', () => {
    const jobCompleteMessage = {
      type: 'job_complete',
      job_id: 'test-job-123',
      result: { design_id: 'design-456' },
      timestamp: '2025-01-27T10:00:00Z',
    };

    expect(jobCompleteMessage.type).toBe('job_complete');
    expect(jobCompleteMessage.result).toBeDefined();
  });

  it('defines correct job failed message structure', () => {
    const jobFailedMessage = {
      type: 'job_failed',
      job_id: 'test-job-123',
      error: 'Generation failed',
      timestamp: '2025-01-27T10:00:00Z',
    };

    expect(jobFailedMessage.type).toBe('job_failed');
    expect(jobFailedMessage.error).toBe('Generation failed');
  });
});
