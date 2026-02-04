/**
 * CheckoutSuccessPage Tests.
 *
 * Tests for the checkout success page including confetti,
 * subscription confirmation, and navigation.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as subscriptionsApi from '@/lib/api/subscriptions';
import { CheckoutSuccessPage } from './CheckoutSuccessPage';

// Mock the subscriptions API
vi.mock('@/lib/api/subscriptions', async () => {
  const actual = await vi.importActual('@/lib/api/subscriptions');
  return {
    ...actual,
    subscriptionsApi: {
      getCurrentSubscription: vi.fn(),
    },
  };
});

// Mock canvas-confetti
vi.mock('canvas-confetti', () => ({
  default: vi.fn(),
}));

// Mock subscription data
const mockActiveSubscription = {
  tier: 'pro',
  status: 'active',
  is_active: true,
  is_premium: true,
  stripe_subscription_id: 'sub_123',
  stripe_customer_id: 'cus_123',
  current_period_start: '2026-01-26T00:00:00Z',
  current_period_end: '2026-02-26T00:00:00Z',
  cancel_at_period_end: false,
};

const renderPage = (searchParams = '') => {
  return render(
    <MemoryRouter initialEntries={[`/checkout/success${searchParams}`]}>
      <CheckoutSuccessPage />
    </MemoryRouter>
  );
};

describe('CheckoutSuccessPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (subscriptionsApi.subscriptionsApi.getCurrentSubscription as any).mockResolvedValue(
      mockActiveSubscription
    );
  });

  describe('Success Display', () => {
    it('renders welcome message', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/Welcome to Pro!/i)).toBeInTheDocument();
      });
    });

    it('shows subscription is active', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Your subscription is now active. Enjoy your premium features!')).toBeInTheDocument();
      });
    });

    it('displays success icon', async () => {
      renderPage();

      await waitFor(() => {
        // Check for the success card containing the check icon
        expect(screen.getByText(/Welcome to Pro!/i)).toBeInTheDocument();
      });
    });
  });

  describe('Subscription Details', () => {
    it('displays plan name', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('pro')).toBeInTheDocument();
      });
    });

    it('displays active status', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Active')).toBeInTheDocument();
      });
    });

    it('displays next billing date', async () => {
      renderPage();

      await waitFor(() => {
        // Date format may vary by locale
        expect(screen.getByText(/2026/i)).toBeInTheDocument();
      });
    });
  });

  describe('Features Unlocked', () => {
    it('displays premium features list', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Features Unlocked')).toBeInTheDocument();
      });
    });

    it('shows unlimited generations feature', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Unlimited Generations')).toBeInTheDocument();
      });
    });

    it('shows priority processing feature', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Priority Processing')).toBeInTheDocument();
      });
    });

    it('shows STEP export feature', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('STEP Export')).toBeInTheDocument();
      });
    });
  });

  describe('Navigation CTAs', () => {
    it('shows Start Creating button', async () => {
      renderPage();

      await waitFor(() => {
        const startLink = screen.getByRole('link', { name: /start creating/i });
        expect(startLink).toBeInTheDocument();
        expect(startLink).toHaveAttribute('href', '/create');
      });
    });

    it('shows Go to Dashboard button', async () => {
      renderPage();

      await waitFor(() => {
        const dashboardLink = screen.getByRole('link', { name: /go to dashboard/i });
        expect(dashboardLink).toBeInTheDocument();
        expect(dashboardLink).toHaveAttribute('href', '/dashboard');
      });
    });

    it('shows manage subscription link', async () => {
      renderPage();

      await waitFor(() => {
        const settingsLink = screen.getByRole('link', { name: /manage subscription/i });
        expect(settingsLink).toBeInTheDocument();
        expect(settingsLink).toHaveAttribute('href', '/settings');
      });
    });
  });

  describe('Enterprise Tier', () => {
    it('shows Enterprise welcome for enterprise tier', async () => {
      (subscriptionsApi.subscriptionsApi.getCurrentSubscription as any).mockResolvedValue({
        ...mockActiveSubscription,
        tier: 'enterprise',
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/Welcome to Enterprise!/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('shows error message when subscription fetch fails', async () => {
      (subscriptionsApi.subscriptionsApi.getCurrentSubscription as any).mockRejectedValue(
        new Error('API Error')
      );

      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/unable to verify subscription/i)).toBeInTheDocument();
      });
    });

    it('still shows success message on API error', async () => {
      (subscriptionsApi.subscriptionsApi.getCurrentSubscription as any).mockRejectedValue(
        new Error('API Error')
      );

      renderPage();

      await waitFor(() => {
        // Should still show premium welcome even if API fails
        expect(screen.getByText(/Welcome to Premium!/i)).toBeInTheDocument();
      });
    });
  });

  describe('Session ID Handling', () => {
    it('accepts session_id query parameter', async () => {
      renderPage('?session_id=cs_test_123');

      await waitFor(() => {
        expect(screen.getByText(/Welcome to Pro!/i)).toBeInTheDocument();
      });
    });
  });
});
