/**
 * CouponsTab Tests.
 *
 * Unit tests for the CouponsTab component.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from '@/lib/api/admin';
import type { CouponListResponse, PromotionAnalyticsResponse } from '@/types/admin';

// Mock the admin API
vi.mock('@/lib/api/admin', () => ({
  adminApi: {
    coupons: {
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      getUsage: vi.fn(),
      applyToUser: vi.fn(),
      bulkApply: vi.fn(),
      getPromotionAnalytics: vi.fn(),
    },
  },
}));

const mockAdminApi = vi.mocked(adminApi, true);

// Import after mocks
import { CouponsTab } from './CouponsTab';

describe('CouponsTab', () => {
  const mockCouponsResponse: CouponListResponse = {
    items: [
      {
        id: 'coupon-1',
        code: 'SUMMER20',
        coupon_type: 'percentage',
        discount_percent: 20,
        discount_amount: null,
        free_credits: null,
        upgrade_tier: null,
        description: 'Summer sale 20% off',
        is_active: true,
        current_uses: 15,
        max_uses: 100,
        max_uses_per_user: 1,
        valid_from: '2024-06-01T00:00:00Z',
        valid_until: '2024-08-31T23:59:59Z',
        restricted_to_tiers: null,
        new_users_only: false,
        created_at: '2024-05-15T00:00:00Z',
        created_by: null,
      },
      {
        id: 'coupon-2',
        code: 'FLAT10',
        coupon_type: 'fixed',
        discount_percent: null,
        discount_amount: 10,
        free_credits: null,
        upgrade_tier: null,
        description: 'Flat $10 off',
        is_active: false,
        current_uses: 50,
        max_uses: 50,
        max_uses_per_user: 1,
        valid_from: '2024-01-01T00:00:00Z',
        valid_until: '2024-03-31T23:59:59Z',
        restricted_to_tiers: null,
        new_users_only: false,
        created_at: '2024-01-01T00:00:00Z',
        created_by: null,
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminApi.coupons.list.mockResolvedValue(mockCouponsResponse);
  });

  it('renders the coupon list heading', async () => {
    render(<CouponsTab />);

    expect(screen.getByText('Coupon Management')).toBeInTheDocument();
  });

  it('fetches and displays coupons on mount', async () => {
    render(<CouponsTab />);

    await waitFor(() => {
      expect(mockAdminApi.coupons.list).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('SUMMER20')).toBeInTheDocument();
      expect(screen.getByText('FLAT10')).toBeInTheDocument();
    });
  });

  it('displays active/inactive status badges correctly', async () => {
    render(<CouponsTab />);

    await waitFor(() => {
      expect(screen.getByText('Active')).toBeInTheDocument();
      expect(screen.getByText('Inactive')).toBeInTheDocument();
    });
  });

  it('opens create modal when Create Coupon is clicked', async () => {
    render(<CouponsTab />);

    await waitFor(() => {
      expect(screen.getByText('SUMMER20')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Coupon'));

    await waitFor(() => {
      expect(screen.getAllByText('Create Coupon').length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('Code *')).toBeInTheDocument();
    });
  });

  it('filters coupons by status', async () => {
    render(<CouponsTab />);

    await waitFor(() => {
      expect(mockAdminApi.coupons.list).toHaveBeenCalledTimes(1);
    });

    const statusSelect = screen.getAllByRole('combobox')[0];
    fireEvent.change(statusSelect, { target: { value: 'active' } });

    await waitFor(() => {
      expect(mockAdminApi.coupons.list).toHaveBeenCalledTimes(2);
    });
  });

  it('shows empty state when no coupons are returned', async () => {
    mockAdminApi.coupons.list.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    render(<CouponsTab />);

    await waitFor(() => {
      expect(screen.getByText('No coupons found.')).toBeInTheDocument();
    });
  });

  it('handles API error gracefully', async () => {
    mockAdminApi.coupons.list.mockRejectedValue(new Error('Network error'));

    render(<CouponsTab />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load coupons')).toBeInTheDocument();
    });
  });

  it('opens promotion analytics view', async () => {
    mockAdminApi.coupons.getPromotionAnalytics.mockResolvedValue({
      total_coupons: 10,
      active_coupons: 5,
      total_redemptions: 150,
      most_used_coupons: [],
    } satisfies PromotionAnalyticsResponse);

    render(<CouponsTab />);

    await waitFor(() => {
      expect(screen.getByText('SUMMER20')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Analytics'));

    await waitFor(() => {
      expect(mockAdminApi.coupons.getPromotionAnalytics).toHaveBeenCalled();
    });
  });

  it('deletes a coupon with confirmation', async () => {
    mockAdminApi.coupons.delete.mockResolvedValue({ message: 'Deleted' });

    render(<CouponsTab />);

    await waitFor(() => {
      expect(screen.getByText('SUMMER20')).toBeInTheDocument();
    });

    // Click the delete button for the first coupon
    const deleteButtons = screen.getAllByTitle('Delete');
    fireEvent.click(deleteButtons[0]);

    // Confirm deletion
    await waitFor(() => {
      expect(screen.getByText(/cannot be undone/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Delete'));

    await waitFor(() => {
      expect(mockAdminApi.coupons.delete).toHaveBeenCalledWith('SUMMER20');
    });
  });
});
