/**
 * Audit Logs API client
 *
 * Provides methods for fetching user audit logs.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export interface AuditLog {
  id: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  actor_type: string;
  status: string;
  error_message: string | null;
  context: Record<string, any>;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface AuditLogsResponse {
  logs: AuditLog[];
  total: number;
  skip: number;
  limit: number;
}

export interface AuditLogsFilters {
  skip?: number;
  limit?: number;
  action?: string;
  resource_type?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
}

/**
 * Build query string from filters
 */
function buildQueryString(filters: AuditLogsFilters): string {
  const params = new URLSearchParams();

  if (filters.skip !== undefined) {
    params.append('skip', filters.skip.toString());
  }
  if (filters.limit !== undefined) {
    params.append('limit', filters.limit.toString());
  }
  if (filters.action) {
    params.append('action', filters.action);
  }
  if (filters.resource_type) {
    params.append('resource_type', filters.resource_type);
  }
  if (filters.status) {
    params.append('status', filters.status);
  }
  if (filters.start_date) {
    params.append('start_date', filters.start_date);
  }
  if (filters.end_date) {
    params.append('end_date', filters.end_date);
  }

  const queryString = params.toString();
  return queryString ? `?${queryString}` : '';
}

export const auditLogsApi = {
  /**
   * Get audit logs for the current user
   */
  async getUserAuditLogs(filters: AuditLogsFilters = {}): Promise<AuditLogsResponse> {
    const token = localStorage.getItem('token');
    if (!token) {
      throw new Error('Not authenticated');
    }

    const queryString = buildQueryString(filters);
    const response = await fetch(`${API_BASE}/users/me/audit-logs${queryString}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Failed to fetch audit logs' }));
      throw new Error(error.detail || 'Failed to fetch audit logs');
    }

    return response.json();
  },
};
