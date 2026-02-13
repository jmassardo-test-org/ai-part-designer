/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Usage API client.
 *
 * Handles usage tracking and billing dashboard data.
 */

/** Subscription tier information. */
export interface SubscriptionTier {
  [key: string]: any;
  name: string;
  level: string;
  credits_included: number;
  features: string[];
}

/** Credit transaction record. */
export interface CreditTransaction {
  [key: string]: any;
  id: string;
  amount: number;
  type: 'usage' | 'purchase' | 'refund' | 'bonus';
  description: string;
  created_at: string;
  balance_after: number;
}

/** Usage dashboard summary. */
export interface UsageDashboard {
  [key: string]: any;
  current_period: {
    start: string;
    end: string;
  };
  credits: any;
  generations: number;
  downloads: number;
  storage_used: number;
  api_calls: number;
}

/** Usage API methods. */
export const usageApi: any = {
  async getDashboard(token?: string): Promise<UsageDashboard> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/usage/dashboard', { headers });
    if (!resp.ok) throw new Error(`Failed to get usage dashboard: ${resp.status}`);
    return resp.json();
  },
  async getTransactions(token?: string, params?: Record<string, string>): Promise<CreditTransaction[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const query = params ? '?' + new URLSearchParams(params).toString() : '';
    const resp = await fetch(`/api/v1/usage/transactions${query}`, { headers });
    if (!resp.ok) throw new Error(`Failed to get transactions: ${resp.status}`);
    return resp.json();
  },
};
