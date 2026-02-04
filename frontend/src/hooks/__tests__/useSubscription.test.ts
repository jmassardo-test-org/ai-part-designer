/**
 * useSubscription hook tests.
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock modules before importing them
vi.mock('@/lib/api/subscriptions', () => ({
  subscriptionsApi: {
    getCurrentSubscription: vi.fn(),
    getUsage: vi.fn(),
    getPaymentHistory: vi.fn(),
    cancelSubscription: vi.fn(),
    resumeSubscription: vi.fn(),
    redirectToBillingPortal: vi.fn(),
    redirectToCheckout: vi.fn(),
  },
}));

// Import after mocking
import { useSubscription } from '@/hooks/useSubscription';
import { subscriptionsApi } from '@/lib/api/subscriptions';

describe('useSubscription', () => {
  const mockSubscriptionsApi = subscriptionsApi as {
    getCurrentSubscription: ReturnType<typeof vi.fn>;
    getUsage: ReturnType<typeof vi.fn>;
    getPaymentHistory: ReturnType<typeof vi.fn>;
    cancelSubscription: ReturnType<typeof vi.fn>;
    resumeSubscription: ReturnType<typeof vi.fn>;
    redirectToBillingPortal: ReturnType<typeof vi.fn>;
    redirectToCheckout: ReturnType<typeof vi.fn>;
  };

  const mockSubscription = {
    tier: 'pro',
    status: 'active',
    is_active: true,
    is_premium: true,
    stripe_subscription_id: 'sub_123',
    stripe_customer_id: 'cus_456',
    current_period_start: '2025-01-01T00:00:00Z',
    current_period_end: '2025-02-01T00:00:00Z',
    cancel_at_period_end: false,
  };

  const mockUsage = {
    tier: 'pro',
    credits_used: 45,
    credits_remaining: 55,
    credits_total: 100,
    storage_used_gb: 12.5,
    storage_limit_gb: 50,
    generations_this_period: 45,
    generations_limit: 100,
    period_start: '2025-01-01T00:00:00Z',
    period_end: '2025-02-01T00:00:00Z',
  };

  const mockPayments = [
    {
      id: 'pay_1',
      payment_type: 'subscription',
      status: 'paid',
      amount: 1999,
      currency: 'usd',
      description: 'Professional monthly',
      paid_at: '2025-01-01T00:00:00Z',
      invoice_url: 'https://invoice.stripe.com/i/in_1',
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    mockSubscriptionsApi.getCurrentSubscription.mockResolvedValue(mockSubscription);
    mockSubscriptionsApi.getUsage.mockResolvedValue(mockUsage);
    mockSubscriptionsApi.getPaymentHistory.mockResolvedValue(mockPayments);
  });

  describe('initial load', () => {
    it('fetches subscription and usage on mount', async () => {
      const { result } = renderHook(() => useSubscription());

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockSubscriptionsApi.getCurrentSubscription).toHaveBeenCalled();
      expect(mockSubscriptionsApi.getUsage).toHaveBeenCalled();
      expect(result.current.subscription).toEqual(mockSubscription);
      expect(result.current.usage).toEqual(mockUsage);
    });

    it('sets computed properties correctly', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isPremium).toBe(true);
      expect(result.current.tier).toBe('pro');
      expect(result.current.isActive).toBe(true);
      expect(result.current.isCanceling).toBe(false);
    });

    it('handles free tier correctly', async () => {
      mockSubscriptionsApi.getCurrentSubscription.mockResolvedValue({
        tier: 'free',
        status: 'active',
        is_active: true,
        is_premium: false,
        stripe_subscription_id: null,
        stripe_customer_id: null,
        current_period_start: null,
        current_period_end: null,
        cancel_at_period_end: false,
      });

      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isPremium).toBe(false);
      expect(result.current.tier).toBe('free');
    });

    it('handles canceling subscription', async () => {
      mockSubscriptionsApi.getCurrentSubscription.mockResolvedValue({
        ...mockSubscription,
        cancel_at_period_end: true,
      });

      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isCanceling).toBe(true);
    });

    it('handles fetch error', async () => {
      mockSubscriptionsApi.getCurrentSubscription.mockRejectedValue(
        new Error('Network error')
      );

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBe('Failed to load subscription status');
      consoleSpy.mockRestore();
    });
  });

  describe('refresh', () => {
    it('refreshes subscription status', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      mockSubscriptionsApi.getCurrentSubscription.mockResolvedValue({
        ...mockSubscription,
        tier: 'enterprise',
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(mockSubscriptionsApi.getCurrentSubscription).toHaveBeenCalledTimes(2);
      expect(result.current.subscription?.tier).toBe('enterprise');
    });
  });

  describe('refreshUsage', () => {
    it('refreshes usage statistics', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      mockSubscriptionsApi.getUsage.mockResolvedValue({
        ...mockUsage,
        credits_used: 75,
        credits_remaining: 25,
      });

      await act(async () => {
        await result.current.refreshUsage();
      });

      expect(mockSubscriptionsApi.getUsage).toHaveBeenCalledTimes(2);
      expect(result.current.usage?.credits_used).toBe(75);
    });
  });

  describe('loadPayments', () => {
    it('loads payment history', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.loadPayments();
      });

      expect(mockSubscriptionsApi.getPaymentHistory).toHaveBeenCalledWith(20, 0);
      expect(result.current.payments).toEqual(mockPayments);
    });

    it('loads payment history with custom params', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.loadPayments(10, 20);
      });

      expect(mockSubscriptionsApi.getPaymentHistory).toHaveBeenCalledWith(10, 20);
    });
  });

  describe('cancelSubscription', () => {
    it('cancels subscription at period end', async () => {
      mockSubscriptionsApi.cancelSubscription.mockResolvedValue({
        ...mockSubscription,
        cancel_at_period_end: true,
      });

      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.cancelSubscription();
      });

      expect(mockSubscriptionsApi.cancelSubscription).toHaveBeenCalledWith(false);
      expect(result.current.subscription?.cancel_at_period_end).toBe(true);
    });

    it('cancels subscription immediately', async () => {
      mockSubscriptionsApi.cancelSubscription.mockResolvedValue({
        tier: 'free',
        status: 'canceled',
        is_active: true,
        is_premium: false,
        stripe_subscription_id: null,
        stripe_customer_id: 'cus_456',
        current_period_start: null,
        current_period_end: null,
        cancel_at_period_end: false,
      });

      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.cancelSubscription(true);
      });

      expect(mockSubscriptionsApi.cancelSubscription).toHaveBeenCalledWith(true);
      expect(result.current.subscription?.tier).toBe('free');
    });

    it('handles cancel error', async () => {
      mockSubscriptionsApi.cancelSubscription.mockRejectedValue(
        new Error('Cancel failed')
      );

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.cancelSubscription();
        })
      ).rejects.toThrow('Cancel failed');

      consoleSpy.mockRestore();
    });
  });

  describe('resumeSubscription', () => {
    it('resumes a canceling subscription', async () => {
      mockSubscriptionsApi.getCurrentSubscription.mockResolvedValue({
        ...mockSubscription,
        cancel_at_period_end: true,
      });
      mockSubscriptionsApi.resumeSubscription.mockResolvedValue({
        ...mockSubscription,
        cancel_at_period_end: false,
      });

      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isCanceling).toBe(true);

      await act(async () => {
        await result.current.resumeSubscription();
      });

      expect(mockSubscriptionsApi.resumeSubscription).toHaveBeenCalled();
      expect(result.current.subscription?.cancel_at_period_end).toBe(false);
    });

    it('handles resume error', async () => {
      mockSubscriptionsApi.resumeSubscription.mockRejectedValue(
        new Error('Resume failed')
      );

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.resumeSubscription();
        })
      ).rejects.toThrow('Resume failed');

      consoleSpy.mockRestore();
    });
  });

  describe('redirectToPortal', () => {
    it('redirects to billing portal', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.redirectToPortal();
      });

      expect(mockSubscriptionsApi.redirectToBillingPortal).toHaveBeenCalled();
    });
  });

  describe('redirectToCheckout', () => {
    it('redirects to checkout with monthly billing', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.redirectToCheckout('pro');
      });

      expect(mockSubscriptionsApi.redirectToCheckout).toHaveBeenCalledWith(
        'pro',
        'monthly'
      );
    });

    it('redirects to checkout with yearly billing', async () => {
      const { result } = renderHook(() => useSubscription());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.redirectToCheckout('enterprise', 'yearly');
      });

      expect(mockSubscriptionsApi.redirectToCheckout).toHaveBeenCalledWith(
        'enterprise',
        'yearly'
      );
    });
  });
});
