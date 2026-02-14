/**
 * Subscriptions API client tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from './client';
import {
  subscriptionsApi,
  getStripeConfig,
  getPlans,
  getCurrentSubscription,
  createCheckoutSession,
  createBillingPortalSession,
  cancelSubscription,
  resumeSubscription,
  getUsage,
  getPaymentHistory,
} from './subscriptions';

// Mock the apiClient
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

// Mock window.location
const mockLocation = { href: '' };
Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true,
});

describe('subscriptions API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLocation.href = '';
  });

  describe('getStripeConfig', () => {
    it('returns Stripe publishable key', async () => {
      const mockConfig = {
        publishable_key: 'pk_test_abc123xyz',
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockConfig,
      });

      const result = await getStripeConfig();

      expect(apiClient.get).toHaveBeenCalledWith('/subscriptions/config');
      expect(result.publishable_key).toBe('pk_test_abc123xyz');
    });
  });

  describe('getPlans', () => {
    it('returns list of subscription plans', async () => {
      const mockPlans = [
        {
          slug: 'free',
          name: 'Free',
          description: 'Basic features for hobbyists',
          monthly_credits: 5,
          max_concurrent_jobs: 1,
          max_storage_gb: 1,
          max_projects: 3,
          max_designs_per_project: 10,
          max_file_size_mb: 25,
          features: { basic_templates: true, ai_chat: true },
          price_monthly: 0,
          price_yearly: 0,
          stripe_price_id_monthly: null,
          stripe_price_id_yearly: null,
        },
        {
          slug: 'pro',
          name: 'Professional',
          description: 'For serious makers',
          monthly_credits: 100,
          max_concurrent_jobs: 5,
          max_storage_gb: 50,
          max_projects: 50,
          max_designs_per_project: 100,
          max_file_size_mb: 100,
          features: { basic_templates: true, ai_chat: true, priority_support: true },
          price_monthly: 19.99,
          price_yearly: 199.99,
          stripe_price_id_monthly: 'price_pro_monthly',
          stripe_price_id_yearly: 'price_pro_yearly',
        },
      ];

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockPlans,
      });

      const result = await getPlans();

      expect(apiClient.get).toHaveBeenCalledWith('/subscriptions/plans');
      expect(result).toHaveLength(2);
      expect(result[0].slug).toBe('free');
      expect(result[1].price_monthly).toBe(19.99);
    });
  });

  describe('getCurrentSubscription', () => {
    it('returns current subscription status', async () => {
      const mockSubscription = {
        tier: 'pro',
        status: 'active',
        is_active: true,
        is_premium: true,
        stripe_subscription_id: 'sub_123abc',
        stripe_customer_id: 'cus_456def',
        current_period_start: '2025-01-01T00:00:00Z',
        current_period_end: '2025-02-01T00:00:00Z',
        cancel_at_period_end: false,
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockSubscription,
      });

      const result = await getCurrentSubscription();

      expect(apiClient.get).toHaveBeenCalledWith('/subscriptions/current');
      expect(result.tier).toBe('pro');
      expect(result.is_premium).toBe(true);
      expect(result.cancel_at_period_end).toBe(false);
    });

    it('returns free tier for users without subscription', async () => {
      const mockSubscription = {
        tier: 'free',
        status: 'active',
        is_active: true,
        is_premium: false,
        stripe_subscription_id: null,
        stripe_customer_id: null,
        current_period_start: null,
        current_period_end: null,
        cancel_at_period_end: false,
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockSubscription,
      });

      const result = await getCurrentSubscription();

      expect(result.tier).toBe('free');
      expect(result.is_premium).toBe(false);
      expect(result.stripe_subscription_id).toBeNull();
    });
  });

  describe('createCheckoutSession', () => {
    it('creates checkout session for monthly subscription', async () => {
      const mockResponse = {
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_123',
        session_id: 'cs_test_123',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await createCheckoutSession({
        plan_slug: 'pro',
        billing_interval: 'monthly',
      });

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/checkout', {
        plan_slug: 'pro',
        billing_interval: 'monthly',
      });
      expect(result.checkout_url).toContain('stripe.com');
      expect(result.session_id).toBe('cs_test_123');
    });

    it('creates checkout session for yearly subscription', async () => {
      const mockResponse = {
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_yearly',
        session_id: 'cs_test_yearly',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await createCheckoutSession({
        plan_slug: 'enterprise',
        billing_interval: 'yearly',
        success_url: 'https://app.example.com/success',
        cancel_url: 'https://app.example.com/pricing',
      });

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/checkout', {
        plan_slug: 'enterprise',
        billing_interval: 'yearly',
        success_url: 'https://app.example.com/success',
        cancel_url: 'https://app.example.com/pricing',
      });
      expect(result.session_id).toBe('cs_test_yearly');
    });
  });

  describe('createBillingPortalSession', () => {
    it('creates billing portal session', async () => {
      const mockResponse = {
        portal_url: 'https://billing.stripe.com/session/bp_test_123',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await createBillingPortalSession();

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/portal', null, {
        params: { return_url: undefined },
      });
      expect(result.portal_url).toContain('billing.stripe.com');
    });

    it('creates portal session with return URL', async () => {
      const mockResponse = {
        portal_url: 'https://billing.stripe.com/session/bp_test_456',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await createBillingPortalSession('https://app.example.com/billing');

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/portal', null, {
        params: { return_url: 'https://app.example.com/billing' },
      });
      expect(result.portal_url).toBeDefined();
    });
  });

  describe('cancelSubscription', () => {
    it('cancels subscription at period end', async () => {
      const mockResponse = {
        tier: 'pro',
        status: 'active',
        is_active: true,
        is_premium: true,
        stripe_subscription_id: 'sub_123',
        stripe_customer_id: 'cus_456',
        current_period_start: '2025-01-01T00:00:00Z',
        current_period_end: '2025-02-01T00:00:00Z',
        cancel_at_period_end: true,
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await cancelSubscription();

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/cancel', null, {
        params: { immediately: false },
      });
      expect(result.cancel_at_period_end).toBe(true);
    });

    it('cancels subscription immediately', async () => {
      const mockResponse = {
        tier: 'free',
        status: 'canceled',
        is_active: true,
        is_premium: false,
        stripe_subscription_id: null,
        stripe_customer_id: 'cus_456',
        current_period_start: null,
        current_period_end: null,
        cancel_at_period_end: false,
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await cancelSubscription(true);

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/cancel', null, {
        params: { immediately: true },
      });
      expect(result.tier).toBe('free');
    });
  });

  describe('resumeSubscription', () => {
    it('resumes a subscription set to cancel', async () => {
      const mockResponse = {
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

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await resumeSubscription();

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/resume');
      expect(result.cancel_at_period_end).toBe(false);
    });
  });

  describe('getUsage', () => {
    it('returns usage statistics', async () => {
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

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockUsage,
      });

      const result = await getUsage();

      expect(apiClient.get).toHaveBeenCalledWith('/subscriptions/usage');
      expect(result.credits_used).toBe(45);
      expect(result.credits_remaining).toBe(55);
      expect(result.storage_used_gb).toBe(12.5);
    });
  });

  describe('getPaymentHistory', () => {
    it('returns payment history with default params', async () => {
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
        {
          id: 'pay_2',
          payment_type: 'subscription',
          status: 'paid',
          amount: 1999,
          currency: 'usd',
          description: 'Professional monthly',
          paid_at: '2024-12-01T00:00:00Z',
          invoice_url: 'https://invoice.stripe.com/i/in_2',
        },
      ];

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockPayments,
      });

      const result = await getPaymentHistory();

      expect(apiClient.get).toHaveBeenCalledWith('/subscriptions/payments', {
        params: { limit: 20, offset: 0 },
      });
      expect(result).toHaveLength(2);
      expect(result[0].amount).toBe(1999);
    });

    it('returns payment history with custom params', async () => {
      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: [],
      });

      await getPaymentHistory(10, 20);

      expect(apiClient.get).toHaveBeenCalledWith('/subscriptions/payments', {
        params: { limit: 10, offset: 20 },
      });
    });
  });

  describe('redirectToCheckout', () => {
    it('redirects to Stripe checkout', async () => {
      const mockResponse = {
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_redirect',
        session_id: 'cs_test_redirect',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      await subscriptionsApi.redirectToCheckout('pro', 'monthly');

      expect(apiClient.post).toHaveBeenCalledWith('/subscriptions/checkout', {
        plan_slug: 'pro',
        billing_interval: 'monthly',
      });
      expect(mockLocation.href).toBe('https://checkout.stripe.com/pay/cs_test_redirect');
    });

    it('redirects with yearly billing', async () => {
      const mockResponse = {
        checkout_url: 'https://checkout.stripe.com/pay/cs_test_yearly_redirect',
        session_id: 'cs_test_yearly_redirect',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      await subscriptionsApi.redirectToCheckout('enterprise', 'yearly');

      expect(mockLocation.href).toBe('https://checkout.stripe.com/pay/cs_test_yearly_redirect');
    });
  });

  describe('redirectToBillingPortal', () => {
    it('redirects to Stripe billing portal', async () => {
      const mockResponse = {
        portal_url: 'https://billing.stripe.com/session/bp_test_redirect',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      await subscriptionsApi.redirectToBillingPortal();

      expect(mockLocation.href).toBe('https://billing.stripe.com/session/bp_test_redirect');
    });
  });
});
