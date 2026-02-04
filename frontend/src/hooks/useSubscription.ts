/**
 * useSubscription Hook.
 * 
 * Provides subscription status, usage, and management functions.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  subscriptionsApi,
  SubscriptionStatus,
  UsageStats,
  PaymentHistoryItem,
} from '@/lib/api/subscriptions';

interface UseSubscriptionReturn {
  // Status
  subscription: SubscriptionStatus | null;
  usage: UsageStats | null;
  payments: PaymentHistoryItem[];
  
  // Loading states
  isLoading: boolean;
  isLoadingUsage: boolean;
  isLoadingPayments: boolean;
  
  // Error states
  error: string | null;
  
  // Computed properties
  isPremium: boolean;
  tier: string;
  isActive: boolean;
  isCanceling: boolean;
  
  // Actions
  refresh: () => Promise<void>;
  refreshUsage: () => Promise<void>;
  loadPayments: (limit?: number, offset?: number) => Promise<void>;
  cancelSubscription: (immediately?: boolean) => Promise<void>;
  resumeSubscription: () => Promise<void>;
  redirectToPortal: () => Promise<void>;
  redirectToCheckout: (plan: string, interval?: 'monthly' | 'yearly') => Promise<void>;
}

export function useSubscription(): UseSubscriptionReturn {
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [payments, setPayments] = useState<PaymentHistoryItem[]>([]);
  
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingUsage, setIsLoadingUsage] = useState(false);
  const [isLoadingPayments, setIsLoadingPayments] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch subscription status
  const refresh = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await subscriptionsApi.getCurrentSubscription();
      setSubscription(data);
    } catch (err) {
      console.error('Failed to fetch subscription:', err);
      setError('Failed to load subscription status');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch usage stats
  const refreshUsage = useCallback(async () => {
    try {
      setIsLoadingUsage(true);
      const data = await subscriptionsApi.getUsage();
      setUsage(data);
    } catch (err) {
      console.error('Failed to fetch usage:', err);
    } finally {
      setIsLoadingUsage(false);
    }
  }, []);

  // Fetch payment history
  const loadPayments = useCallback(async (limit = 20, offset = 0) => {
    try {
      setIsLoadingPayments(true);
      const data = await subscriptionsApi.getPaymentHistory(limit, offset);
      setPayments(data);
    } catch (err) {
      console.error('Failed to fetch payments:', err);
    } finally {
      setIsLoadingPayments(false);
    }
  }, []);

  // Cancel subscription
  const cancelSubscription = useCallback(async (immediately = false) => {
    try {
      const updated = await subscriptionsApi.cancelSubscription(immediately);
      setSubscription(updated);
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      throw err;
    }
  }, []);

  // Resume subscription
  const resumeSubscription = useCallback(async () => {
    try {
      const updated = await subscriptionsApi.resumeSubscription();
      setSubscription(updated);
    } catch (err) {
      console.error('Failed to resume subscription:', err);
      throw err;
    }
  }, []);

  // Redirect to billing portal
  const redirectToPortal = useCallback(async () => {
    await subscriptionsApi.redirectToBillingPortal();
  }, []);

  // Redirect to checkout
  const redirectToCheckout = useCallback(
    async (plan: string, interval: 'monthly' | 'yearly' = 'monthly') => {
      await subscriptionsApi.redirectToCheckout(plan, interval);
    },
    []
  );

  // Load subscription on mount
  useEffect(() => {
    refresh();
    refreshUsage();
  }, [refresh, refreshUsage]);

  // Computed properties
  const isPremium = subscription?.is_premium ?? false;
  const tier = subscription?.tier ?? 'free';
  const isActive = subscription?.is_active ?? true;
  const isCanceling = subscription?.cancel_at_period_end ?? false;

  return {
    subscription,
    usage,
    payments,
    isLoading,
    isLoadingUsage,
    isLoadingPayments,
    error,
    isPremium,
    tier,
    isActive,
    isCanceling,
    refresh,
    refreshUsage,
    loadPayments,
    cancelSubscription,
    resumeSubscription,
    redirectToPortal,
    redirectToCheckout,
  };
}

export default useSubscription;
