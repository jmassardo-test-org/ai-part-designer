import { describe, it, expect, beforeEach } from 'vitest';
import { tokenStorage } from './api';

describe('api module', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('tokenStorage', () => {
    describe('getAccessToken', () => {
      it('returns token from localStorage', () => {
        localStorage.setItem('access_token', 'local-token');
        expect(tokenStorage.getAccessToken()).toBe('local-token');
      });

      it('returns token from sessionStorage if not in localStorage', () => {
        sessionStorage.setItem('access_token', 'session-token');
        expect(tokenStorage.getAccessToken()).toBe('session-token');
      });

      it('prefers localStorage over sessionStorage', () => {
        localStorage.setItem('access_token', 'local-token');
        sessionStorage.setItem('access_token', 'session-token');
        expect(tokenStorage.getAccessToken()).toBe('local-token');
      });

      it('returns null when no token exists', () => {
        expect(tokenStorage.getAccessToken()).toBeNull();
      });
    });

    describe('getRefreshToken', () => {
      it('returns refresh token from localStorage', () => {
        localStorage.setItem('refresh_token', 'local-refresh');
        expect(tokenStorage.getRefreshToken()).toBe('local-refresh');
      });

      it('returns refresh token from sessionStorage if not in localStorage', () => {
        sessionStorage.setItem('refresh_token', 'session-refresh');
        expect(tokenStorage.getRefreshToken()).toBe('session-refresh');
      });

      it('returns null when no refresh token exists', () => {
        expect(tokenStorage.getRefreshToken()).toBeNull();
      });
    });

    describe('setTokens', () => {
      const mockTokens = {
        access_token: 'new-access',
        refresh_token: 'new-refresh',
        token_type: 'Bearer',
        expires_in: 3600,
      };

      it('stores tokens in sessionStorage by default', () => {
        tokenStorage.setTokens(mockTokens);
        expect(sessionStorage.getItem('access_token')).toBe('new-access');
        expect(sessionStorage.getItem('refresh_token')).toBe('new-refresh');
        expect(localStorage.getItem('access_token')).toBeNull();
      });

      it('stores tokens in localStorage when rememberMe is true', () => {
        tokenStorage.setTokens(mockTokens, true);
        expect(localStorage.getItem('access_token')).toBe('new-access');
        expect(localStorage.getItem('refresh_token')).toBe('new-refresh');
        expect(sessionStorage.getItem('access_token')).toBeNull();
      });
    });

    describe('clearTokens', () => {
      it('clears tokens from both storages', () => {
        localStorage.setItem('access_token', 'local');
        localStorage.setItem('refresh_token', 'local-refresh');
        sessionStorage.setItem('access_token', 'session');
        sessionStorage.setItem('refresh_token', 'session-refresh');

        tokenStorage.clearTokens();

        expect(localStorage.getItem('access_token')).toBeNull();
        expect(localStorage.getItem('refresh_token')).toBeNull();
        expect(sessionStorage.getItem('access_token')).toBeNull();
        expect(sessionStorage.getItem('refresh_token')).toBeNull();
      });
    });

    describe('hasTokens', () => {
      it('returns true when access token exists', () => {
        localStorage.setItem('access_token', 'token');
        expect(tokenStorage.hasTokens()).toBe(true);
      });

      it('returns false when no access token exists', () => {
        expect(tokenStorage.hasTokens()).toBe(false);
      });
    });
  });
});
