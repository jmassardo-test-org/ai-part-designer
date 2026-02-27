/**
 * Usage API client.
 *
 * Handles usage tracking, credit balance, tiers, and billing dashboard data.
 */

/** Subscription tier information from GET /usage/tiers. */
export interface SubscriptionTier {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  monthly_credits: number;
  max_concurrent_jobs: number;
  max_storage_gb: number;
  max_projects: number;
  max_file_size_mb: number;
  features: Record<string, boolean>;
  price_monthly: number;
  price_yearly: number;
  is_current: boolean;
}

/** Credit balance information. */
export interface CreditBalance {
  balance: number;
  lifetime_earned: number;
  lifetime_spent: number;
  next_refill_at: string | null;
  credits_per_month: number;
}

/** Quota usage information. */
export interface QuotaUsage {
  storage_used_bytes: number;
  storage_limit_bytes: number;
  storage_used_percent: number;
  active_jobs_count: number;
  max_concurrent_jobs: number;
  projects_count: number;
  max_projects: number;
  period_generations: number;
  period_exports: number;
}

/** Credit transaction record. */
export interface CreditTransaction {
  id: string;
  amount: number;
  transaction_type: string;
  description: string;
  balance_after: number;
  created_at: string;
  reference_type: string | null;
}

/** Complete usage dashboard from GET /usage/dashboard. */
export interface UsageDashboard {
  credits: CreditBalance;
  quota: QuotaUsage;
  current_tier: SubscriptionTier;
  recent_transactions: CreditTransaction[];
}

/** Usage breakdown by type. */
export interface UsageByType {
  transaction_type: string;
  credits_spent: number;
  operation_count: number;
}

/** Usage summary for a period. */
export interface UsageSummary {
  current_balance: number;
  lifetime_earned: number;
  lifetime_spent: number;
  period_days: number;
  usage_by_type: UsageByType[];
  next_refill_at: string | null;
}

async function apiFetch<T>(path: string): Promise<T> {
  const resp = await fetch(`/api/v1/usage${path}`);
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new Error(detail || `Request failed: ${resp.status}`);
  }
  return resp.json();
}

/** Usage API methods. */
export const usageApi = {
  /** Get the complete usage dashboard. */
  async getDashboard(): Promise<UsageDashboard> {
    return apiFetch('/dashboard');
  },

  /** List all available subscription tiers with current tier marked. */
  async getTiers(): Promise<SubscriptionTier[]> {
    return apiFetch('/tiers');
  },

  /** Get a specific tier by slug. */
  async getTier(slug: string): Promise<SubscriptionTier> {
    return apiFetch(`/tiers/${slug}`);
  },

  /** Get current credit balance. */
  async getCreditBalance(): Promise<CreditBalance> {
    return apiFetch('/credits/balance');
  },

  /** Get credit transaction history. */
  async getTransactions(params?: {
    limit?: number;
    offset?: number;
    transaction_type?: string;
  }): Promise<CreditTransaction[]> {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    if (params?.transaction_type)
      searchParams.set('transaction_type', params.transaction_type);
    const query = searchParams.toString();
    return apiFetch(`/credits/transactions${query ? '?' + query : ''}`);
  },

  /** Get usage summary for a period. */
  async getUsageSummary(days = 30): Promise<UsageSummary> {
    return apiFetch(`/credits/usage?days=${days}`);
  },

  /** Get current quota usage. */
  async getQuota(): Promise<QuotaUsage> {
    return apiFetch('/quota');
  },
};
