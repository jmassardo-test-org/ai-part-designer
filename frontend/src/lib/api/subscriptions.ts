/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Subscriptions API client.
 *
 * Handles subscription management, plans, and billing.
 */

/** Subscription plan details. */
export interface SubscriptionPlan {
  [key: string]: any;
  id: string;
  name: string;
  price: number;
  interval: 'month' | 'year';
  features: string[];
  credits: number;
}

/** Current subscription status. */
export interface SubscriptionStatus {
  [key: string]: any;
  plan: string;
  status: 'active' | 'canceled' | 'past_due' | 'trialing' | 'inactive';
  current_period_end: string;
  cancel_at_period_end: boolean;
  credits_remaining: number;
  credits_total: number;
}

/** Usage statistics for the current billing period. */
export interface UsageStats {
  [key: string]: any;
  generations: number;
  downloads: number;
  storage_used: number;
  api_calls: number;
}

/** Payment history entry. */
export interface PaymentHistoryItem {
  [key: string]: any;
  id: string;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
  invoice_url?: string;
}

/** Subscriptions API methods. */
export const subscriptionsApi: any = {
  async getStatus(token?: string): Promise<SubscriptionStatus> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/status', { headers });
    if (!resp.ok) throw new Error(`Failed to get subscription status: ${resp.status}`);
    return resp.json();
  },
  async listPlans(token?: string): Promise<SubscriptionPlan[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/plans', { headers });
    if (!resp.ok) throw new Error(`Failed to list plans: ${resp.status}`);
    return resp.json();
  },
  async createCheckout(planId: string, token?: string): Promise<{ url: string }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/checkout', {
      method: 'POST',
      headers,
      body: JSON.stringify({ plan_id: planId }),
    });
    if (!resp.ok) throw new Error(`Failed to create checkout: ${resp.status}`);
    return resp.json();
  },
  async cancelSubscription(token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/cancel', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to cancel subscription: ${resp.status}`);
  },
  async getUsage(token?: string): Promise<UsageStats> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/usage', { headers });
    if (!resp.ok) throw new Error(`Failed to get usage: ${resp.status}`);
    return resp.json();
  },
  async getPaymentHistory(token?: string): Promise<PaymentHistoryItem[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/payments', { headers });
    if (!resp.ok) throw new Error(`Failed to get payment history: ${resp.status}`);
    return resp.json();
  },
  async createPortalSession(token?: string): Promise<{ url: string }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/portal', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to create portal session: ${resp.status}`);
    return resp.json();
  },
  async verifyCheckout(sessionId: string, token?: string): Promise<SubscriptionStatus> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/subscriptions/verify', {
      method: 'POST',
      headers,
      body: JSON.stringify({ session_id: sessionId }),
    });
    if (!resp.ok) throw new Error(`Failed to verify checkout: ${resp.status}`);
    return resp.json();
  },
};
