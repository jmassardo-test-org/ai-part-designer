/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Components API client.
 *
 * Handles CRUD operations for component library management.
 */

/** Component API methods. */
export const componentsApi: any = {
  async listComponents(token?: string, params?: Record<string, string>): Promise<any> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    const resp = await fetch(`/api/v1/components${query}`, { headers });
    if (!resp.ok) throw new Error(`Failed to list components: ${resp.status}`);
    return resp.json();
  },
  async getComponent(id: string, token?: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/components/${id}`, { headers });
    if (!resp.ok) throw new Error(`Failed to get component: ${resp.status}`);
    return resp.json();
  },
  async uploadComponent(formData: FormData, token?: string): Promise<any> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/components', {
      method: 'POST',
      headers,
      body: formData,
    });
    if (!resp.ok) throw new Error(`Failed to upload component: ${resp.status}`);
    return resp.json();
  },
  async deleteComponent(id: string, token?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/components/${id}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`Failed to delete component: ${resp.status}`);
  },
};
