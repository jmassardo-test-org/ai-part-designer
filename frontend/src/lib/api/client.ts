/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * API client instance for direct fetch calls.
 *
 * Provides a thin wrapper around fetch with auth header injection.
 */

const BASE_URL = '/api/v1';

interface ApiClientOptions {
  token?: string;
  params?: Record<string, string | number | boolean>;
}

interface ApiClient {
  get<T = unknown>(url: string, options?: ApiClientOptions): Promise<{ data: T }>;
  post<T = unknown>(url: string, body?: unknown, options?: ApiClientOptions): Promise<{ data: T }>;
  put<T = unknown>(url: string, body?: unknown, options?: ApiClientOptions): Promise<{ data: T }>;
  delete<T = any>(url: string, options?: ApiClientOptions): Promise<{ data: T }>;
  patch<T = any>(url: string, body?: unknown, options?: ApiClientOptions): Promise<{ data: T }>;
}

/** Configured API client for making authenticated requests. */
export const apiClient: ApiClient = {
  async get<T = unknown>(url: string, options?: ApiClientOptions): Promise<{ data: T }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    let fullUrl = `${BASE_URL}${url}`;
    if (options?.params) {
      const searchParams = new URLSearchParams();
      for (const [key, value] of Object.entries(options.params)) {
        searchParams.set(key, String(value));
      }
      fullUrl += `?${searchParams.toString()}`;
    }
    const resp = await fetch(fullUrl, { headers });
    if (!resp.ok) throw new Error(`GET ${url} failed: ${resp.status}`);
    return { data: await resp.json() };
  },
  async post<T = unknown>(url: string, body?: unknown, options?: ApiClientOptions): Promise<{ data: T }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'POST',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`POST ${url} failed: ${resp.status}`);
    return { data: await resp.json() };
  },
  async put<T = unknown>(url: string, body?: unknown, options?: ApiClientOptions): Promise<{ data: T }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'PUT',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`PUT ${url} failed: ${resp.status}`);
    return { data: await resp.json() };
  },
  async delete<T = any>(url: string, options?: ApiClientOptions): Promise<{ data: T }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`DELETE ${url} failed: ${resp.status}`);
    return { data: await resp.json() };
  },
  async patch<T = any>(url: string, body?: unknown, options?: ApiClientOptions): Promise<{ data: T }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (options?.token) headers['Authorization'] = `Bearer ${options.token}`;
    const resp = await fetch(`${BASE_URL}${url}`, {
      method: 'PATCH',
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!resp.ok) throw new Error(`PATCH ${url} failed: ${resp.status}`);
    return { data: await resp.json() };
  },
};

export default apiClient;
