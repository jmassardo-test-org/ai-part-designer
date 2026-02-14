/**
 * Admin API Service Tests.
 *
 * Unit tests for admin API client functions.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { adminApi } from './admin';

// Store original fetch
const originalFetch = global.fetch;

// Mock fetch helper that returns proper Response-like object
function createMockResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: () => Promise.resolve(data),
    clone: function() { return this; },
    headers: new Headers(),
    redirected: false,
    statusText: ok ? 'OK' : 'Error',
    type: 'basic',
    url: '',
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response;
}

describe('adminApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe('getStats', () => {
    it('fetches admin stats without token', async () => {
      const mockData = { users: 100, projects: 50 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.getStats();

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/admin/stats', {
        headers: {},
      });
      expect(result).toEqual(mockData);
    });

    it('fetches admin stats with token', async () => {
      const mockData = { users: 100, projects: 50 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.getStats('test-token');

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/admin/stats', {
        headers: { Authorization: 'Bearer test-token' },
      });
      expect(result).toEqual(mockData);
    });

    it('throws error on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 403));

      await expect(adminApi.getStats()).rejects.toThrow(
        'Failed to get admin stats: 403'
      );
    });
  });

  describe('getUsers', () => {
    it('fetches users without params or token', async () => {
      const mockData = { users: [{ id: '1', name: 'Test User' }] };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.getUsers();

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/admin/users', {
        headers: {},
      });
      expect(result).toEqual(mockData);
    });

    it('fetches users with params', async () => {
      const mockData = { users: [{ id: '1', name: 'Test User' }] };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.getUsers({ page: '1', limit: '10' });

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/admin/users?page=1&limit=10',
        { headers: {} }
      );
      expect(result).toEqual(mockData);
    });

    it('fetches users with token', async () => {
      const mockData = { users: [] };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.getUsers(undefined, 'test-token');

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/admin/users', {
        headers: { Authorization: 'Bearer test-token' },
      });
      expect(result).toEqual(mockData);
    });

    it('throws error on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 500));

      await expect(adminApi.getUsers()).rejects.toThrow(
        'Failed to get users: 500'
      );
    });
  });

  describe('getSystemHealth', () => {
    it('fetches system health without token', async () => {
      const mockData = { status: 'healthy', uptime: 12345 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.getSystemHealth();

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/admin/health', {
        headers: {},
      });
      expect(result).toEqual(mockData);
    });

    it('fetches system health with token', async () => {
      const mockData = { status: 'healthy', uptime: 12345 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.getSystemHealth('test-token');

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/admin/health', {
        headers: { Authorization: 'Bearer test-token' },
      });
      expect(result).toEqual(mockData);
    });

    it('throws error on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 503));

      await expect(adminApi.getSystemHealth()).rejects.toThrow(
        'Failed to get system health: 503'
      );
    });
  });
});
