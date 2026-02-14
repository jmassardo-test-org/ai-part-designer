import { describe, it, expect, beforeEach } from 'vitest';
import { tokenStorage } from './client';

describe('api/client', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  describe('tokenStorage', () => {
    describe('getAccessToken', () => {
      it('returns token from localStorage first', () => {
        localStorage.setItem('access_token', 'local-token');
        sessionStorage.setItem('access_token', 'session-token');
        expect(tokenStorage.getAccessToken()).toBe('local-token');
      });

      it('falls back to sessionStorage', () => {
        sessionStorage.setItem('access_token', 'session-token');
        expect(tokenStorage.getAccessToken()).toBe('session-token');
      });

      it('returns null when no token exists', () => {
        expect(tokenStorage.getAccessToken()).toBeNull();
      });
    });
  });
});
