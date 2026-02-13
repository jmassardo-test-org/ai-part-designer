/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Admin API client.
 *
 * Handles admin dashboard operations and system management.
 */

/** Admin API methods. */
export const adminApi: any = {
  async getStats(token?: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/admin/stats', { headers });
    if (!resp.ok) throw new Error(`Failed to get admin stats: ${resp.status}`);
    return resp.json();
  },
  async getUsers(params?: Record<string, string>, token?: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    const resp = await fetch(`/api/v1/admin/users${query}`, { headers });
    if (!resp.ok) throw new Error(`Failed to get users: ${resp.status}`);
    return resp.json();
  },
  async getSystemHealth(token?: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/admin/health', { headers });
    if (!resp.ok) throw new Error(`Failed to get system health: ${resp.status}`);
    return resp.json();
  },
};
