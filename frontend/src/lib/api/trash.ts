/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Trash API client.
 *
 * Handles soft-deleted item management and restoration.
 */

/** A trashed item. */
export interface TrashedItem {
  [key: string]: any;
  id: string;
  name: string;
  type?: string;
  item_type?: string;
  deleted_at: string;
  expires_at: string;
  deleted_by?: string;
  original_project?: string;
  original_location?: string;
  thumbnail_url?: string;
  size_bytes?: number;
  days_until_deletion?: number;
}

/** Paginated response for trash listing. */
export interface TrashListResponse {
  [key: string]: any;
  items: TrashedItem[];
  total: number;
  page: number;
  page_size: number;
}

/** Trash retention settings. */
export interface TrashSettings {
  [key: string]: any;
  retention_days: number;
  auto_delete: boolean;
}

/** Trash statistics. */
export interface TrashStats {
  [key: string]: any;
  total_items: number;
  total_size: number;
  oldest_item_date?: string;
}

/** Trash API methods. */
const trashApi: any = {
  async list(params?: Record<string, string>, token?: string): Promise<TrashListResponse> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    const resp = await fetch(`/api/v1/trash${query}`, { headers });
    if (!resp.ok) throw new Error(`Failed to list trash: ${resp.status}`);
    return resp.json();
  },
  async restore(itemId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/trash/${itemId}/restore`, { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to restore item: ${resp.status}`);
  },
  async permanentDelete(itemId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/trash/${itemId}`, { method: 'DELETE', headers });
    if (!resp.ok) throw new Error(`Failed to permanently delete item: ${resp.status}`);
  },
  async emptyTrash(token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/trash/empty', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to empty trash: ${resp.status}`);
  },
  async getStats(token?: string): Promise<TrashStats> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/trash/stats', { headers });
    if (!resp.ok) throw new Error(`Failed to get trash stats: ${resp.status}`);
    return resp.json();
  },
  async getSettings(token?: string): Promise<TrashSettings> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/trash/settings', { headers });
    if (!resp.ok) throw new Error(`Failed to get trash settings: ${resp.status}`);
    return resp.json();
  },
};

export default trashApi;
