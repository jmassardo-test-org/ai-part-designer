/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Content moderation API client.
 *
 * Handles content moderation for admin workflows.
 */

/** Detail of a reported item. */
export interface ReportDetailResponse {
  [key: string]: any;
  id: string;
  reporter_id: string;
  target_id: string;
  target_type: string;
  reason: string;
  status: string;
  created_at: string;
  resolved_at?: string;
  details?: string;
}

/** Detail of a ban action. */
export interface BanDetailResponse {
  [key: string]: any;
  id: string;
  user_id: string;
  reason: string;
  banned_at: string;
  expires_at?: string;
  banned_by: string;
}

/** Moderation statistics. */
export interface ModerationStats {
  [key: string]: any;
  total_reports: number;
  pending_reports: number;
  resolved_reports: number;
  active_bans: number;
}

/** Moderation API methods. */
export const moderationApi: any = {
  async getStats(token?: string): Promise<ModerationStats> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/admin/moderation/stats', { headers });
    if (!resp.ok) throw new Error(`Failed to get moderation stats: ${resp.status}`);
    return resp.json();
  },
  async listReports(token?: string, params?: Record<string, string>): Promise<ReportDetailResponse[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    const resp = await fetch(`/api/v1/admin/moderation/reports${query}`, { headers });
    if (!resp.ok) throw new Error(`Failed to list reports: ${resp.status}`);
    return resp.json();
  },
  async resolveReport(reportId: string, action: string, token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/admin/moderation/reports/${reportId}/resolve`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ action }),
    });
    if (!resp.ok) throw new Error(`Failed to resolve report: ${resp.status}`);
  },
  async listBans(token?: string): Promise<BanDetailResponse[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/admin/moderation/bans', { headers });
    if (!resp.ok) throw new Error(`Failed to list bans: ${resp.status}`);
    return resp.json();
  },
  async banUser(userId: string, reason: string, expiresAt?: string, token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/admin/moderation/bans', {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId, reason, expires_at: expiresAt }),
    });
    if (!resp.ok) throw new Error(`Failed to ban user: ${resp.status}`);
  },
  async unbanUser(banId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/admin/moderation/bans/${banId}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`Failed to unban user: ${resp.status}`);
  },
};
