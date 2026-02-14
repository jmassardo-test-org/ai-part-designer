/**
 * OAuth API client tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './client';
import { oauthApi } from './oauth';

// Mock the api client
vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('oauthApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('initiateLogin', () => {
    it('initiates Google OAuth login', async () => {
      const mockResponse = {
        authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?...',
        state: 'random-state-123',
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await oauthApi.initiateLogin('google');

      expect(api.get).toHaveBeenCalledWith('/auth/oauth/google/login');
      expect(result.authorization_url).toContain('google.com');
      expect(result.state).toBe('random-state-123');
    });

    it('initiates GitHub OAuth login', async () => {
      const mockResponse = {
        authorization_url: 'https://github.com/login/oauth/authorize?...',
        state: 'github-state-456',
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await oauthApi.initiateLogin('github');

      expect(api.get).toHaveBeenCalledWith('/auth/oauth/github/login');
      expect(result.authorization_url).toContain('github.com');
    });

    it('includes redirect_uri when provided', async () => {
      const mockResponse = {
        authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?redirect_uri=...',
        state: 'state-with-redirect',
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      await oauthApi.initiateLogin('google', 'https://myapp.com/callback');

      expect(api.get).toHaveBeenCalledWith(
        '/auth/oauth/google/login?redirect_uri=https%3A%2F%2Fmyapp.com%2Fcallback'
      );
    });

    it('handles login initiation errors', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('OAuth provider unavailable')
      );

      await expect(oauthApi.initiateLogin('google')).rejects.toThrow(
        'OAuth provider unavailable'
      );
    });
  });

  describe('getConnections', () => {
    it('returns list of connected OAuth providers', async () => {
      const mockConnections = {
        connections: [
          {
            id: 'conn-1',
            provider: 'google',
            provider_email: 'user@gmail.com',
            provider_username: null,
            connected_at: '2025-01-15T10:00:00Z',
          },
          {
            id: 'conn-2',
            provider: 'github',
            provider_email: null,
            provider_username: 'user123',
            connected_at: '2025-01-20T14:30:00Z',
          },
        ],
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockConnections,
      });

      const result = await oauthApi.getConnections();

      expect(api.get).toHaveBeenCalledWith('/auth/oauth/connections');
      expect(result.connections).toHaveLength(2);
      expect(result.connections[0].provider).toBe('google');
      expect(result.connections[1].provider).toBe('github');
    });

    it('returns empty connections list for new user', async () => {
      const mockConnections = { connections: [] };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockConnections,
      });

      const result = await oauthApi.getConnections();

      expect(result.connections).toHaveLength(0);
    });

    it('handles unauthorized access', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Unauthorized')
      );

      await expect(oauthApi.getConnections()).rejects.toThrow('Unauthorized');
    });
  });

  describe('initiateLink', () => {
    it('initiates linking Google account', async () => {
      const mockResponse = {
        authorization_url: 'https://accounts.google.com/o/oauth2/v2/auth?state=link-...',
        state: 'link-google-789',
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await oauthApi.initiateLink('google');

      expect(api.post).toHaveBeenCalledWith('/auth/oauth/link/google');
      expect(result.state).toContain('link');
    });

    it('initiates linking GitHub account', async () => {
      const mockResponse = {
        authorization_url: 'https://github.com/login/oauth/authorize?...',
        state: 'link-github-101',
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await oauthApi.initiateLink('github');

      expect(api.post).toHaveBeenCalledWith('/auth/oauth/link/github');
      expect(result.authorization_url).toBeDefined();
    });

    it('handles linking when provider already connected', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Provider already connected')
      );

      await expect(oauthApi.initiateLink('google')).rejects.toThrow(
        'Provider already connected'
      );
    });
  });

  describe('unlinkProvider', () => {
    it('unlinks a connected provider', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { message: 'Provider unlinked successfully' },
      });

      const result = await oauthApi.unlinkProvider('google');

      expect(api.delete).toHaveBeenCalledWith('/auth/oauth/connections/google');
      expect(result.message).toBe('Provider unlinked successfully');
    });

    it('unlinks GitHub provider', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { message: 'GitHub account disconnected' },
      });

      const result = await oauthApi.unlinkProvider('github');

      expect(api.delete).toHaveBeenCalledWith('/auth/oauth/connections/github');
      expect(result.message).toBeDefined();
    });

    it('handles unlinking last auth method', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Cannot remove last authentication method')
      );

      await expect(oauthApi.unlinkProvider('google')).rejects.toThrow(
        'Cannot remove last authentication method'
      );
    });

    it('handles unlinking non-existent connection', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Connection not found')
      );

      await expect(oauthApi.unlinkProvider('twitter')).rejects.toThrow(
        'Connection not found'
      );
    });
  });
});
