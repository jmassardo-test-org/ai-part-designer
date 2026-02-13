/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * API client singleton and token storage.
 *
 * Provides a configured axios-like client and helpers for managing auth tokens.
 */

const BASE_URL = '/api/v1';

/** Simple token storage using localStorage. */
export const tokenStorage = {
  getToken: (): string | null => localStorage.getItem('auth_token'),
  getAccessToken: (): string | null => localStorage.getItem('access_token'),
  setToken: (token: string): void => localStorage.setItem('auth_token', token),
  setTokens: (tokensOrAccess: any, _refreshTokenOrFlag?: any): void => {
    if (typeof tokensOrAccess === 'string') {
      localStorage.setItem('auth_token', tokensOrAccess);
      localStorage.setItem('access_token', tokensOrAccess);
      if (_refreshTokenOrFlag && typeof _refreshTokenOrFlag === 'string') localStorage.setItem('refresh_token', _refreshTokenOrFlag);
    } else {
      localStorage.setItem('auth_token', tokensOrAccess.access_token);
      localStorage.setItem('access_token', tokensOrAccess.access_token);
      if (tokensOrAccess.refresh_token) localStorage.setItem('refresh_token', tokensOrAccess.refresh_token);
    }
  },
  removeToken: (): void => localStorage.removeItem('auth_token'),
  clearTokens: (): void => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },
  hasTokens: (): boolean => !!localStorage.getItem('auth_token'),
};

/** Headers helper for authenticated requests. */
function authHeaders(token?: string | null): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  const t = token ?? tokenStorage.getToken();
  if (t) headers['Authorization'] = `Bearer ${t}`;
  return headers;
}

/** Base API client with common HTTP methods. */
const api: any = {
  async get<T = unknown>(path: string, token?: string | null): Promise<T> {
    const resp = await fetch(`${BASE_URL}${path}`, { headers: authHeaders(token) });
    if (!resp.ok) throw new Error(`GET ${path} failed: ${resp.status}`);
    return resp.json();
  },
  async post<T = unknown>(path: string, body?: unknown, token?: string | null): Promise<T> {
    const resp = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: authHeaders(token),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`POST ${path} failed: ${resp.status}`);
    return resp.json();
  },
  async put<T = unknown>(path: string, body?: unknown, token?: string | null): Promise<T> {
    const resp = await fetch(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers: authHeaders(token),
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`PUT ${path} failed: ${resp.status}`);
    return resp.json();
  },
  async delete<T = unknown>(path: string, token?: string | null): Promise<T> {
    const resp = await fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
    if (!resp.ok) throw new Error(`DELETE ${path} failed: ${resp.status}`);
    return resp.json();
  },
};

export default api;
