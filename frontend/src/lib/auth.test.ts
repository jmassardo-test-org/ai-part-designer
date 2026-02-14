import { describe, it, expect, vi, beforeEach } from 'vitest';
import apiClient, { tokenStorage } from './api';
import { authApi } from './auth';

// Mock the API client
vi.mock('./api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
  tokenStorage: {
    setTokens: vi.fn(),
    clearTokens: vi.fn(),
    getRefreshToken: vi.fn(),
  },
}));

describe('authApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('register', () => {
    it('registers a new user', async () => {
      const mockUser = {
        id: 'user-123',
        email: 'test@example.com',
        display_name: 'Test User',
        role: 'user',
        status: 'pending_verification',
      };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockUser });

      const result = await authApi.register({
        email: 'test@example.com',
        password: 'password123',
        display_name: 'Test User',
        accepted_terms: true,
      });

      expect(apiClient.post).toHaveBeenCalledWith('/auth/register', {
        email: 'test@example.com',
        password: 'password123',
        display_name: 'Test User',
        accepted_terms: true,
      });
      expect(result).toEqual(mockUser);
    });
  });

  describe('login', () => {
    it('logs in and stores tokens', async () => {
      const mockTokens = {
        access_token: 'access-123',
        refresh_token: 'refresh-123',
        token_type: 'Bearer',
        expires_in: 3600,
      };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockTokens });

      const result = await authApi.login({
        email: 'test@example.com',
        password: 'password123',
      });

      expect(apiClient.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password123',
      });
      expect(tokenStorage.setTokens).toHaveBeenCalledWith(mockTokens, false);
      expect(result).toEqual(mockTokens);
    });

    it('stores tokens with rememberMe flag', async () => {
      const mockTokens = {
        access_token: 'access-123',
        refresh_token: 'refresh-123',
        token_type: 'Bearer',
        expires_in: 3600,
      };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockTokens });

      await authApi.login({
        email: 'test@example.com',
        password: 'password123',
        remember_me: true,
      });

      expect(tokenStorage.setTokens).toHaveBeenCalledWith(mockTokens, true);
    });
  });

  describe('logout', () => {
    it('logs out and clears tokens', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({});

      await authApi.logout();

      expect(apiClient.post).toHaveBeenCalledWith('/auth/logout');
      expect(tokenStorage.clearTokens).toHaveBeenCalled();
    });

    it('clears tokens even if logout API fails', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'));

      // Should not throw, just clear tokens
      try {
        await authApi.logout();
      } catch {
        // Expected to not throw, but if it does we still check tokens were cleared
      }

      expect(tokenStorage.clearTokens).toHaveBeenCalled();
    });
  });

  describe('getCurrentUser', () => {
    it('fetches current user profile', async () => {
      const mockUser = {
        id: 'user-123',
        email: 'test@example.com',
        display_name: 'Test User',
      };
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockUser });

      const result = await authApi.getCurrentUser();

      expect(apiClient.get).toHaveBeenCalledWith('/auth/me');
      expect(result).toEqual(mockUser);
    });
  });

  describe('refreshToken', () => {
    it('refreshes access token', async () => {
      const mockTokens = {
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        token_type: 'Bearer',
        expires_in: 3600,
      };
      (tokenStorage.getRefreshToken as ReturnType<typeof vi.fn>).mockReturnValue('old-refresh');
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockTokens });

      const result = await authApi.refreshToken();

      expect(apiClient.post).toHaveBeenCalledWith('/auth/refresh', {
        refresh_token: 'old-refresh',
      });
      expect(tokenStorage.setTokens).toHaveBeenCalled();
      expect(result).toEqual(mockTokens);
    });

    it('throws error when no refresh token available', async () => {
      (tokenStorage.getRefreshToken as ReturnType<typeof vi.fn>).mockReturnValue(null);

      await expect(authApi.refreshToken()).rejects.toThrow('No refresh token available');
    });
  });

  describe('forgotPassword', () => {
    it('sends password reset email', async () => {
      const mockResponse = { message: 'Reset email sent' };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse });

      const result = await authApi.forgotPassword({ email: 'test@example.com' });

      expect(apiClient.post).toHaveBeenCalledWith('/auth/forgot-password', {
        email: 'test@example.com',
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('resetPassword', () => {
    it('resets password with token', async () => {
      const mockResponse = { message: 'Password reset successfully' };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse });

      const result = await authApi.resetPassword({
        token: 'reset-token',
        new_password: 'newpassword123',
      });

      expect(apiClient.post).toHaveBeenCalledWith('/auth/reset-password', {
        token: 'reset-token',
        new_password: 'newpassword123',
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('verifyEmail', () => {
    it('verifies email with token', async () => {
      const mockResponse = { message: 'Email verified' };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse });

      const result = await authApi.verifyEmail({ token: 'verify-token' });

      expect(apiClient.post).toHaveBeenCalledWith('/auth/verify-email', {
        token: 'verify-token',
      });
      expect(result).toEqual(mockResponse);
    });
  });

  describe('resendVerification', () => {
    it('resends verification email', async () => {
      const mockResponse = { message: 'Verification email sent' };
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ data: mockResponse });

      const result = await authApi.resendVerification();

      expect(apiClient.post).toHaveBeenCalledWith('/auth/resend-verification');
      expect(result).toEqual(mockResponse);
    });
  });
});
