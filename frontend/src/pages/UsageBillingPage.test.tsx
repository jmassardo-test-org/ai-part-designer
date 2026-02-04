/**
 * UsageBillingPage Tests.
 *
 * Tests for the usage and billing page including usage stats,
 * billing portal, and subscription management.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as subscriptionsApi from '@/lib/api/subscriptions';
import * as usageApi from '@/lib/api/usage';
import { UsageBillingPage } from './UsageBillingPage';

// Mock APIs
vi.mock('@/lib/api/usage', async () => {
  const actual = await vi.importActual('@/lib/api/usage');
  return {
    ...actual,
    usageApi: {
      getDashboard: vi.fn(),
      getTiers: vi.fn(),
    },
  };
});

vi.mock('@/lib/api/subscriptions', async () => {
  const actual = await vi.importActual('@/lib/api/subscriptions');
  return {
    ...actual,
    subscriptionsApi: {
      getCurrentSubscription: vi.fn(),
      cancelSubscription: vi.fn(),
      resumeSubscription: vi.fn(),
      redirectToBillingPortal: vi.fn(),
    },
  };
});

// Mock data
const mockDashboard = {
  credits: {
    balance: 75,
    lifetime_earned: 100,
    lifetime_spent: 25,
    next_refill_at: '2026-02-01T00:00:00Z',
    credits_per_month: 100,
  },
  quota: {
    storage_used_bytes: 1073741824, // 1 GB
    storage_limit_bytes: 53687091200, // 50 GB
    storage_used_percent: 2,
    active_jobs_count: 1,
    max_concurrent_jobs: 5,
    projects_count: 3,
    max_projects: 20,
    period_generations: 15,
    period_exports: 5,
  },
  current_tier: {
    id: 'tier-pro',
    name: 'Pro',
    slug: 'pro',
    description: 'For professionals',
    monthly_credits: 100,
    max_concurrent_jobs: 5,
    max_storage_gb: 50,
    max_projects: 20,
    max_file_size_mb: 100,
    features: {},
    price_monthly: 19,
    price_yearly: 190,
    is_current: true,
  },
  recent_transactions: [
    {
      id: 'tx-1',
      amount: -5,
      transaction_type: 'generation',
      description: 'Design generation',
      balance_after: 75,
      created_at: '2026-01-25T10:00:00Z',
      reference_type: 'design',
    },
    {
      id: 'tx-2',
      amount: 100,
      transaction_type: 'monthly_refill',
      description: 'Monthly credit refill',
      balance_after: 80,
      created_at: '2026-01-01T00:00:00Z',
      reference_type: null,
    },
  ],
};

const mockTiers = [
  {
    id: 'tier-free',
    name: 'Free',
    slug: 'free',
    description: 'Get started',
    monthly_credits: 10,
    max_concurrent_jobs: 1,
    max_storage_gb: 1,
    max_projects: 3,
    max_file_size_mb: 10,
    features: {},
    price_monthly: 0,
    price_yearly: 0,
    is_current: false,
  },
  {
    id: 'tier-pro',
    name: 'Pro',
    slug: 'pro',
    description: 'For professionals',
    monthly_credits: 100,
    max_concurrent_jobs: 5,
    max_storage_gb: 50,
    max_projects: 20,
    max_file_size_mb: 100,
    features: {},
    price_monthly: 19,
    price_yearly: 190,
    is_current: true,
  },
];

const mockSubscription = {
  tier: 'pro',
  status: 'active',
  is_active: true,
  is_premium: true,
  stripe_subscription_id: 'sub_123',
  stripe_customer_id: 'cus_123',
  current_period_start: '2026-01-01T00:00:00Z',
  current_period_end: '2026-02-01T00:00:00Z',
  cancel_at_period_end: false,
};

const renderPage = () => {
  return render(
    <MemoryRouter>
      <UsageBillingPage />
    </MemoryRouter>
  );
};

describe('UsageBillingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (usageApi.usageApi.getDashboard as any).mockResolvedValue(mockDashboard);
    (usageApi.usageApi.getTiers as any).mockResolvedValue(mockTiers);
    (subscriptionsApi.subscriptionsApi.getCurrentSubscription as any).mockResolvedValue(mockSubscription);
  });

  describe('Loading State', () => {
    it('shows loading spinner initially', () => {
      renderPage();
      expect(document.querySelector('.animate-spin')).toBeTruthy();
    });
  });

  describe('Overview Tab', () => {
    it('displays credit balance', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('75')).toBeInTheDocument();
      });
    });

    it('displays storage usage', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/1.*GB/i)).toBeInTheDocument();
      });
    });

    it('displays active jobs count', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/of 5 allowed/i)).toBeInTheDocument();
      });
    });

    it('displays current plan info', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Pro')).toBeInTheDocument();
        expect(screen.getByText('$19/month')).toBeInTheDocument();
      });
    });

    it('displays next credit refill date', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/\+100 credits/i)).toBeInTheDocument();
      });
    });

    it('shows recent transactions', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Design generation')).toBeInTheDocument();
        expect(screen.getByText('Monthly credit refill')).toBeInTheDocument();
      });
    });
  });

  describe('Tabs Navigation', () => {
    it('switches to transactions tab', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /transactions/i }));

      await waitFor(() => {
        expect(screen.getByText('Transaction History')).toBeInTheDocument();
      });
    });

    it('switches to tiers tab', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /tiers/i }));

      await waitFor(() => {
        expect(screen.getByText('Free')).toBeInTheDocument();
        expect(screen.getByText('Pro')).toBeInTheDocument();
      });
    });

    it('switches to billing tab', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /billing/i }));

      await waitFor(() => {
        expect(screen.getByText('Subscription Details')).toBeInTheDocument();
        expect(screen.getByText('Manage Billing')).toBeInTheDocument();
      });
    });
  });

  describe('Billing Tab', () => {
    it('displays subscription status', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Overview')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /billing/i }));

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument();
      });
    });

    it('displays next billing date', async () => {
      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        expect(screen.getByText(/Next Billing Date/i)).toBeInTheDocument();
        // The date format may vary based on locale
        expect(screen.getByText(/2026/i)).toBeInTheDocument();
      });
    });

    it('shows manage payment button', async () => {
      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /manage payment/i })).toBeInTheDocument();
      });
    });

    it('opens billing portal when clicking manage payment', async () => {
      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        const manageButton = screen.getByRole('button', { name: /manage payment/i });
        fireEvent.click(manageButton);
      });

      await waitFor(() => {
        expect(subscriptionsApi.subscriptionsApi.redirectToBillingPortal).toHaveBeenCalled();
      });
    });

    it('shows cancel subscription button for premium users', async () => {
      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel plan/i })).toBeInTheDocument();
      });
    });
  });

  describe('Cancel Subscription Flow', () => {
    it('opens confirmation dialog when clicking cancel', async () => {
      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /cancel plan/i }));
      });

      await waitFor(() => {
        expect(screen.getByText('Cancel Subscription?')).toBeInTheDocument();
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });
    });

    it('allows dismissing cancel dialog', async () => {
      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /cancel plan/i }));
      });

      await waitFor(() => {
        expect(screen.getByText('Cancel Subscription?')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /keep subscription/i }));

      await waitFor(() => {
        expect(screen.queryByText('Cancel Subscription?')).not.toBeInTheDocument();
      });
    });

    it('calls cancel API when confirming cancellation', async () => {
      (subscriptionsApi.subscriptionsApi.cancelSubscription as any).mockResolvedValue({
        ...mockSubscription,
        cancel_at_period_end: true,
      });

      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /cancel plan/i }));
      });

      await waitFor(() => {
        // Click the "Cancel Subscription" button in the dialog
        const buttons = screen.getAllByRole('button', { name: /cancel subscription/i });
        fireEvent.click(buttons[buttons.length - 1]); // Get the confirm button
      });

      await waitFor(() => {
        expect(subscriptionsApi.subscriptionsApi.cancelSubscription).toHaveBeenCalledWith(false);
      });
    });
  });

  describe('Resume Subscription Flow', () => {
    it('shows resume button when subscription is canceling', async () => {
      (subscriptionsApi.subscriptionsApi.getCurrentSubscription as any).mockResolvedValue({
        ...mockSubscription,
        cancel_at_period_end: true,
      });

      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /keep subscription/i })).toBeInTheDocument();
      });
    });

    it('calls resume API when clicking keep subscription', async () => {
      (subscriptionsApi.subscriptionsApi.getCurrentSubscription as any).mockResolvedValue({
        ...mockSubscription,
        cancel_at_period_end: true,
      });
      (subscriptionsApi.subscriptionsApi.resumeSubscription as any).mockResolvedValue(mockSubscription);

      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /billing/i }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /keep subscription/i }));
      });

      await waitFor(() => {
        expect(subscriptionsApi.subscriptionsApi.resumeSubscription).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when API fails', async () => {
      (usageApi.usageApi.getDashboard as any).mockRejectedValue(new Error('API Error'));

      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/failed to load usage data/i)).toBeInTheDocument();
      });
    });

    it('shows retry button on error', async () => {
      (usageApi.usageApi.getDashboard as any).mockRejectedValue(new Error('API Error'));

      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
      });
    });

    it('retries loading when clicking retry', async () => {
      (usageApi.usageApi.getDashboard as any).mockRejectedValueOnce(new Error('API Error'));
      (usageApi.usageApi.getDashboard as any).mockResolvedValueOnce(mockDashboard);

      renderPage();

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /retry/i }));
      });

      await waitFor(() => {
        expect(usageApi.usageApi.getDashboard).toHaveBeenCalledTimes(2);
      });
    });
  });
});
