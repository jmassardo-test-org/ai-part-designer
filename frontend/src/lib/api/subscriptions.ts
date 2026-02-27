/**
 * Subscriptions API client.
 *
 * Handles subscription management, plans, checkout, and billing.
 */

/** Subscription plan details returned by GET /subscriptions/plans. */
export interface SubscriptionPlan {
  slug: string;
  name: string;
  description: string | null;
  monthly_credits: number;
  max_concurrent_jobs: number;
  max_storage_gb: number;
  max_projects: number;
  max_designs_per_project: number;
  max_file_size_mb: number;
  features: Record<string, boolean>;
  price_monthly: number;
  price_yearly: number;
  stripe_price_id_monthly: string | null;
  stripe_price_id_yearly: string | null;
}

/** Current subscription status returned by GET /subscriptions/current. */
export interface SubscriptionStatus {
  tier: string;
  status: string;
  is_active: boolean;
  is_premium: boolean;
  stripe_subscription_id: string | null;
  stripe_customer_id: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

/** Usage statistics returned by GET /subscriptions/usage. */
export interface UsageStats {
  tier: string;
  credits_used: number;
  credits_remaining: number;
  credits_total: number;
  storage_used_gb: number;
  storage_limit_gb: number;
  generations_this_period: number;
  generations_limit: number;
  period_start: string | null;
  period_end: string | null;
}

/** Payment history entry returned by GET /subscriptions/payments. */
export interface PaymentHistoryItem {
  id: string;
  payment_type: string;
  status: string;
  amount: number;
  currency: string;
  description: string;
  paid_at: string | null;
  invoice_url: string | null;
}

/** Stripe publishable key config. */
export interface StripeConfig {
  publishable_key: string;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`/api/v1/subscriptions${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new Error(detail || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

export const subscriptionsApi = {
  /** Get Stripe publishable key for frontend initialization. */
  async getStripeConfig(): Promise<StripeConfig> {
    return apiFetch('/config');
  },

  /** List all available subscription plans. */
  async listPlans(): Promise<SubscriptionPlan[]> {
    return apiFetch('/plans');
  },

  /** Get the current user's subscription status. */
  async getCurrentSubscription(): Promise<SubscriptionStatus> {
    return apiFetch('/current');
  },

  /** Get current usage statistics. */
  async getUsage(): Promise<UsageStats> {
    return apiFetch('/usage');
  },

  /** Get payment history. */
  async getPaymentHistory(
    limit = 20,
    offset = 0
  ): Promise<PaymentHistoryItem[]> {
    return apiFetch(`/payments?limit=${limit}&offset=${offset}`);
  },

  /**
   * Create a Stripe Checkout session and redirect the user.
   * Returns the checkout URL (also redirects automatically).
   */
  async redirectToCheckout(
    planSlug: string,
    billingInterval: 'monthly' | 'yearly' = 'monthly',
    successUrl?: string,
    cancelUrl?: string
  ): Promise<void> {
    const data = await apiFetch<{ checkout_url: string; session_id: string }>(
      '/checkout',
      {
        method: 'POST',
        body: JSON.stringify({
          plan_slug: planSlug,
          billing_interval: billingInterval,
          success_url: successUrl,
          cancel_url: cancelUrl,
        }),
      }
    );
    window.location.href = data.checkout_url;
  },

  /** Open the Stripe Billing Portal for payment method / invoice management. */
  async redirectToBillingPortal(returnUrl?: string): Promise<void> {
    const data = await apiFetch<{ portal_url: string }>('/portal', {
      method: 'POST',
      body: JSON.stringify({ return_url: returnUrl }),
    });
    window.location.href = data.portal_url;
  },

  /** Cancel the current subscription. */
  async cancelSubscription(immediately = false): Promise<SubscriptionStatus> {
    return apiFetch(`/cancel?immediately=${immediately}`, { method: 'POST' });
  },

  /** Resume a subscription that was set to cancel at period end. */
  async resumeSubscription(): Promise<SubscriptionStatus> {
    return apiFetch('/resume', { method: 'POST' });
  },
};
