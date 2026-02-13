/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * API client instance for direct fetch calls.
 *
 * Provides a thin wrapper around fetch with auth header injection.
 */

const BASE_URL = '/api/v1';

/** Configured API client for making authenticated requests. */
export const apiClient: any = {
  async get<T = unknown>(url: string, options?: { token?: string }): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, { headers });
    if (!resp.ok) throw new Error(`GET ${url} failed: ${resp.status}`);
    return resp.json();
  },
  async post<T = unknown>(url: string, body?: unknown, options?: { token?: string }): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`POST ${url} failed: ${resp.status}`);
    return resp.json();
  },
  async put<T = unknown>(url: string, body?: unknown, options?: { token?: string }): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'PUT',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`PUT ${url} failed: ${resp.status}`);
    return resp.json();
  },
  async delete<T = any>(url: string, options?: { token?: string }): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`DELETE ${url} failed: ${resp.status}`);
    return resp.json();
  },
  async patch<T = any>(url: string, body?: unknown, options?: { token?: string }): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'PATCH',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`PATCH ${url} failed: ${resp.status}`);
    return resp.json();
  },
};

export default apiClient;
