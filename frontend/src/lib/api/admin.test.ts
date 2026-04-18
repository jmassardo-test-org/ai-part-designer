/**
 * Admin API Service Tests.
 *
 * Unit tests for the comprehensive namespaced admin API client.
 * Covers representative methods from each namespace to validate
 * request construction, auth header injection, query params,
 * body serialisation, and error handling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { adminApi } from './admin';

// Store original fetch
const originalFetch = global.fetch;

/**
 * Create a mock Response object compatible with the fetch API.
 *
 * @param data - The JSON response body.
 * @param ok - Whether the response is OK (status 2xx).
 * @param status - HTTP status code.
 */
function createMockResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: () => Promise.resolve(data),
    clone: function () {
      return this;
    },
    headers: new Headers(),
    redirected: false,
    statusText: ok ? 'OK' : 'Error',
    type: 'basic',
    url: '',
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response;
}

describe('adminApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  // ---------------------------------------------------------------------------
  // Moderation
  // ---------------------------------------------------------------------------
  describe('moderation', () => {
    it('fetches moderation queue', async () => {
      const mockData = { items: [], total: 0, page: 1, page_size: 20, pending_count: 0, escalated_count: 0 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.moderation.getQueue({ page: 1 }, 'tok');

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('/api/v1/admin/moderation/queue');
      expect(url).toContain('page=1');
      expect(result).toEqual(mockData);
    });

    it('fetches moderation stats', async () => {
      const mockData = { pending_count: 5, escalated_count: 1, approved_today: 10, rejected_today: 2, appeals_pending: 0, avg_review_time_hours: null };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.moderation.getStats('tok');
      expect(result).toEqual(mockData);
    });

    it('approves moderation item', async () => {
      const mockData = { id: 'abc', decision: 'approved', reviewed_by: 'admin', reviewed_at: '2025-01-01', message: 'ok' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.moderation.approve('abc', { notes: 'looks good' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/moderation/abc/approve');
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual({ notes: 'looks good' });
      expect(result).toEqual(mockData);
    });

    it('rejects moderation item', async () => {
      const mockData = { id: 'abc', decision: 'rejected', reviewed_by: 'admin', reviewed_at: '2025-01-01', message: 'rejected' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.moderation.reject('abc', { reason: 'spam', warn_user: true }, 'tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('POST');
      expect(JSON.parse(opts.body)).toEqual({ reason: 'spam', warn_user: true });
    });

    it('throws on error', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 403));
      await expect(adminApi.moderation.getStats()).rejects.toThrow();
    });
  });

  // ---------------------------------------------------------------------------
  // Analytics
  // ---------------------------------------------------------------------------
  describe('analytics', () => {
    it('fetches overview', async () => {
      const mockData = { total_users: 100, active_users_daily: 20 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.analytics.getOverview('tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/analytics/overview');
      expect(result).toEqual(mockData);
    });

    it('fetches revenue with period', async () => {
      const mockData = { monthly_recurring_revenue_cents: 5000, total_revenue_cents: 20000 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.analytics.getRevenue({ period: '30d' }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('period=30d');
    });

    it('fetches time series analytics', async () => {
      const mockData = { new_users: [], active_users: [] };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.analytics.getTimeSeries({ days: 7 }, 'tok');
      expect(result).toEqual(mockData);
    });
  });

  // ---------------------------------------------------------------------------
  // Users
  // ---------------------------------------------------------------------------
  describe('users', () => {
    it('lists users with filter', async () => {
      const mockData = { users: [], total: 0, page: 1, page_size: 20 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.users.list({ search: 'john', role: 'admin', page: 1 }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('/api/v1/admin/users');
      expect(url).toContain('search=john');
      expect(url).toContain('role=admin');
      expect(result).toEqual(mockData);
    });

    it('gets user details', async () => {
      const mockData = { id: 'u1', email: 'test@test.com' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.users.get('u1', 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1');
      expect(result).toEqual(mockData);
    });

    it('updates user', async () => {
      const mockData = { id: 'u1', role: 'admin' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.users.update('u1', { role: 'admin' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1');
      expect(opts.method).toBe('PATCH');
      expect(JSON.parse(opts.body)).toEqual({ role: 'admin' });
    });

    it('suspends user', async () => {
      const mockData = { message: 'User suspended' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.users.suspend('u1', { reason: 'TOS violation' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/suspend');
      expect(opts.method).toBe('POST');
    });

    it('unsuspends user', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'ok' }));

      await adminApi.users.unsuspend('u1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/unsuspend');
      expect(opts.method).toBe('POST');
    });

    it('deletes user', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'deleted' }));

      await adminApi.users.delete('u1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1');
      expect(opts.method).toBe('DELETE');
    });

    it('impersonates user', async () => {
      const mockData = { access_token: 'tok2', user_id: 'u1', user_email: 'a@b.com', expires_at: '2025-01-01', audit_id: 'aud1' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.users.impersonate('u1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/impersonate');
      expect(opts.method).toBe('POST');
      expect(result.access_token).toBe('tok2');
    });

    it('warns user', async () => {
      const mockData = { id: 'w1', user_id: 'u1', category: 'tos', severity: 'medium', message: 'warning' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.users.warn('u1', { category: 'tos', message: 'warning' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/warn');
      expect(opts.method).toBe('POST');
    });

    it('bans user', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'b1', user_id: 'u1', reason: 'abuse' }));

      await adminApi.users.ban('u1', { reason: 'abuse', is_permanent: true }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/ban');
      expect(opts.method).toBe('POST');
    });

    it('unbans user', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'unbanned' }));

      await adminApi.users.unban('u1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/ban');
      expect(opts.method).toBe('DELETE');
    });

    it('performs bulk action', async () => {
      const mockData = { total: 3, success_count: 3, failure_count: 0, errors: [] };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.users.bulkAction({ action: 'suspend', user_ids: ['u1', 'u2', 'u3'] }, 'tok');
      expect(result.success_count).toBe(3);
    });

    it('gets login history', async () => {
      const mockData = { entries: [], total: 0, page: 1, page_size: 20 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.users.getLoginHistory('u1', { page: 1 }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('/api/v1/admin/users/u1/login-history');
    });

    it('throws on failed request', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 500));
      await expect(adminApi.users.list()).rejects.toThrow();
    });
  });

  // ---------------------------------------------------------------------------
  // Projects
  // ---------------------------------------------------------------------------
  describe('projects', () => {
    it('lists projects', async () => {
      const mockData = { projects: [], total: 0, page: 1, page_size: 20 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.projects.list({ search: 'test' }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('/api/v1/admin/projects');
      expect(url).toContain('search=test');
    });

    it('transfers project', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'transferred' }));

      await adminApi.projects.transfer('p1', { new_owner_id: 'u2' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/projects/p1/transfer');
      expect(opts.method).toBe('POST');
    });

    it('suspends and unsuspends project', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'suspended' }));
      await adminApi.projects.suspend('p1', { reason: 'test' }, 'tok');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'unsuspended' }));
      await adminApi.projects.unsuspend('p1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/projects/p1/unsuspend');
      expect(opts.method).toBe('POST');
    });
  });

  // ---------------------------------------------------------------------------
  // Designs
  // ---------------------------------------------------------------------------
  describe('designs', () => {
    it('lists designs', async () => {
      const mockData = { designs: [], total: 0, page: 1, page_size: 20 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.designs.list({ is_public: true }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('/api/v1/admin/designs');
    });

    it('restores design', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'restored' }));
      await adminApi.designs.restore('d1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/designs/d1/restore');
      expect(opts.method).toBe('POST');
    });

    it('changes design visibility', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'd1', is_public: true }));
      await adminApi.designs.changeVisibility('d1', { is_public: true }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/designs/d1/visibility');
      expect(opts.method).toBe('PATCH');
    });

    it('gets design versions', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ versions: [], total: 0 }));
      const result = await adminApi.designs.getVersions('d1', 'tok');
      expect(result.versions).toEqual([]);
    });
  });

  // ---------------------------------------------------------------------------
  // Templates
  // ---------------------------------------------------------------------------
  describe('templates', () => {
    it('creates template', async () => {
      const body = { name: 'Test', slug: 'test', category: 'enclosure', parameters: {}, default_values: {}, cadquery_script: 'pass' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 't1', ...body }));

      await adminApi.templates.create(body, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/templates');
      expect(opts.method).toBe('POST');
    });

    it('enables and disables template', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'enabled' }));
      await adminApi.templates.enable('t1', 'tok');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'disabled' }));
      await adminApi.templates.disable('t1', 'tok');
    });

    it('clones template', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 't2', name: 'Copy of Test' }));
      const result = await adminApi.templates.clone('t1', 'tok');
      expect(result.id).toBe('t2');
    });

    it('reorders templates', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'reordered' }));
      await adminApi.templates.reorder({ template_ids: ['t1', 't2', 't3'] }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/templates/reorder');
      expect(opts.method).toBe('PATCH');
    });

    it('gets template analytics', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_templates: 10 }));
      const result = await adminApi.templates.getAnalytics('tok');
      expect(result.total_templates).toBe(10);
    });
  });

  // ---------------------------------------------------------------------------
  // Jobs
  // ---------------------------------------------------------------------------
  describe('jobs', () => {
    it('lists jobs with filter', async () => {
      const mockData = { jobs: [], total: 0, page: 1, page_size: 20 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      await adminApi.jobs.list({ status: 'failed' }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('status=failed');
    });

    it('cancels and retries job', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'cancelled' }));
      await adminApi.jobs.cancel('j1', 'tok');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'retried' }));
      await adminApi.jobs.retry('j1', 'tok');
    });

    it('sets job priority', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'priority set' }));
      await adminApi.jobs.setPriority('j1', { priority: 10 }, 'tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('PATCH');
    });

    it('gets queue status and workers', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ queue_length: 5, active_workers: 2 }));
      const qs = await adminApi.jobs.getQueueStatus('tok');
      expect(qs.queue_length).toBe(5);

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse([{ name: 'w1', status: 'active' }]));
      const workers = await adminApi.jobs.getWorkers('tok');
      expect(workers).toHaveLength(1);
    });

    it('purges jobs', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ purged_count: 42, message: 'ok' }));
      const result = await adminApi.jobs.purge({ status: 'failed' }, 'tok');
      expect(result.purged_count).toBe(42);

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('DELETE');
    });
  });

  // ---------------------------------------------------------------------------
  // Subscriptions
  // ---------------------------------------------------------------------------
  describe('subscriptions', () => {
    it('lists subscriptions', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.subscriptions.list({ tier_filter: 'pro' }, 'tok');
    });

    it('changes subscription tier', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'changed' }));
      await adminApi.subscriptions.changeTier('s1', { tier: 'enterprise' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/subscriptions/s1/tier');
      expect(opts.method).toBe('PATCH');
    });

    it('extends subscription', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'extended' }));
      await adminApi.subscriptions.extend('s1', { days: 30 }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/subscriptions/s1/extend');
      expect(opts.method).toBe('POST');
    });
  });

  // ---------------------------------------------------------------------------
  // Credits
  // ---------------------------------------------------------------------------
  describe('credits', () => {
    it('gets user credits', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ user_id: 'u1', balance: 100 }));
      const result = await adminApi.credits.getBalance('u1', 'tok');
      expect(result.balance).toBe(100);
    });

    it('adds credits', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ user_id: 'u1', balance: 200 }));
      await adminApi.credits.add('u1', { amount: 100, reason: 'bonus' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/credits/add');
      expect(opts.method).toBe('POST');
    });

    it('deducts credits', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ user_id: 'u1', balance: 50 }));
      await adminApi.credits.deduct('u1', { amount: 50, reason: 'adjustment' }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/credits/deduct');
    });

    it('gets credit history', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.credits.getHistory('u1', { page: 1 }, 'tok');
    });

    it('overrides quota', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'overridden' }));
      await adminApi.credits.overrideQuota('u1', { storage_limit_gb: 50 }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/quota/override');
      expect(opts.method).toBe('POST');
    });

    it('gets credit distribution', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_credits_issued: 1000, avg_balance: 50 }));
      const result = await adminApi.credits.getDistribution('tok');
      expect(result.total_credits_issued).toBe(1000);
    });

    it('gets low balance users', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0, threshold: 10 }));
      await adminApi.credits.getLowBalanceUsers({ threshold: 10 }, 'tok');
    });
  });

  // ---------------------------------------------------------------------------
  // Billing
  // ---------------------------------------------------------------------------
  describe('billing', () => {
    it('gets failed payments', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.billing.getFailedPayments(undefined, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/billing/failed-payments');
    });

    it('gets billing revenue', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_revenue_cents: 100000 }));
      await adminApi.billing.getRevenue({ period: '30d' }, 'tok');
    });
  });

  // ---------------------------------------------------------------------------
  // Subscription Tiers
  // ---------------------------------------------------------------------------
  describe('subscriptionTiers', () => {
    it('lists tiers', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse([{ slug: 'free' }, { slug: 'pro' }]));
      const result = await adminApi.subscriptionTiers.list('tok');
      expect(result).toHaveLength(2);
    });

    it('updates tier', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ slug: 'pro', name: 'Pro Updated' }));
      await adminApi.subscriptionTiers.update('tier1', { name: 'Pro Updated' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/subscription-tiers/tier1');
      expect(opts.method).toBe('PATCH');
    });
  });

  // ---------------------------------------------------------------------------
  // Coupons
  // ---------------------------------------------------------------------------
  describe('coupons', () => {
    it('lists coupons', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.coupons.list({ status: 'active' }, 'tok');
    });

    it('creates coupon', async () => {
      const body = { code: 'SAVE20', coupon_type: 'percent', discount_percent: 20 };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'c1', ...body }));
      await adminApi.coupons.create(body, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/coupons');
      expect(opts.method).toBe('POST');
    });

    it('gets coupon by code', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ code: 'SAVE20' }));
      await adminApi.coupons.get('SAVE20', 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/coupons/SAVE20');
    });

    it('applies coupon to user', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'applied' }));
      await adminApi.coupons.applyToUser('u1', { coupon_code: 'SAVE20' }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/apply-coupon');
    });

    it('grants trial', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'granted' }));
      await adminApi.coupons.grantTrial('u1', { tier: 'pro', duration_days: 14 }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/grant-trial');
    });

    it('bulk applies coupon', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total: 10, success_count: 10, failure_count: 0, errors: [] }));
      await adminApi.coupons.bulkApply({ coupon_code: 'SAVE20', target: 'tier', target_value: 'free' }, 'tok');
    });
  });

  // ---------------------------------------------------------------------------
  // Organizations
  // ---------------------------------------------------------------------------
  describe('organizations', () => {
    it('lists organizations', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.organizations.list({ search: 'acme' }, 'tok');
    });

    it('adds member', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ user_id: 'u1', role: 'member' }));
      await adminApi.organizations.addMember('org1', { user_id: 'u1' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/organizations/org1/members');
      expect(opts.method).toBe('POST');
    });

    it('removes member', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'removed' }));
      await adminApi.organizations.removeMember('org1', 'u1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/organizations/org1/members/u1');
      expect(opts.method).toBe('DELETE');
    });

    it('changes member role', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ role: 'admin' }));
      await adminApi.organizations.changeMemberRole('org1', 'u1', { role: 'admin' }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/organizations/org1/members/u1/role');
      expect(opts.method).toBe('PATCH');
    });

    it('transfers ownership', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'transferred' }));
      await adminApi.organizations.transferOwnership('org1', { new_owner_id: 'u2' }, 'tok');
    });

    it('adds org credits', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'credits added' }));
      await adminApi.organizations.addCredits('org1', { amount: 500, reason: 'partner bonus' }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/organizations/org1/credits/add');
    });

    it('gets org stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ org_id: 'org1', member_count: 5 }));
      const result = await adminApi.organizations.getStats('org1', 'tok');
      expect(result.member_count).toBe(5);
    });
  });

  // ---------------------------------------------------------------------------
  // Components
  // ---------------------------------------------------------------------------
  describe('components', () => {
    it('lists components', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.components.list({ library_only: true }, 'tok');
    });

    it('creates component', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'comp1', name: 'Resistor' }));
      await adminApi.components.create({ name: 'Resistor', category: 'passive' }, 'tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('POST');
    });

    it('verifies and features component', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'verified' }));
      await adminApi.components.verify('comp1', 'tok');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'featured' }));
      await adminApi.components.feature('comp1', 'tok');
    });

    it('approves component for library', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'approved' }));
      await adminApi.components.approveForLibrary('comp1', 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/components/comp1/approve-for-library');
    });
  });

  // ---------------------------------------------------------------------------
  // Notifications
  // ---------------------------------------------------------------------------
  describe('notifications', () => {
    it('sends announcement', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'sent', sent_count: 100 }));
      const result = await adminApi.notifications.sendAnnouncement({ title: 'Hello', message: 'World' }, 'tok');
      expect(result.sent_count).toBe(100);
    });

    it('sends notification to user', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'sent' }));
      await adminApi.notifications.sendToUser('u1', { title: 'Hi', message: 'Test' }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/send-notification');
    });

    it('gets notification stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total: 500, unread: 50 }));
      const result = await adminApi.notifications.getStats('tok');
      expect(result.total).toBe(500);
    });

    it('creates notification template', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'tmpl1', name: 'Welcome' }));
      await adminApi.notifications.createTemplate({ name: 'Welcome', subject: 'Hello', body_template: 'Hi {{name}}' }, 'tok');
    });
  });

  // ---------------------------------------------------------------------------
  // Files & Storage
  // ---------------------------------------------------------------------------
  describe('files', () => {
    it('lists files', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.files.list({ user_id: 'u1' }, 'tok');
    });

    it('gets flagged files', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.files.getFlagged(undefined, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/files/flagged');
    });

    it('deletes file', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'deleted' }));
      await adminApi.files.delete('f1', 'tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('DELETE');
    });
  });

  describe('storage', () => {
    it('gets storage stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_files: 1000, total_size_bytes: 50000000 }));
      const result = await adminApi.storage.getStats('tok');
      expect(result.total_files).toBe(1000);
    });

    it('garbage collects', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ files_cleaned: 50, space_reclaimed_mb: 100 }));
      const result = await adminApi.storage.garbageCollect('tok');
      expect(result.files_cleaned).toBe(50);
    });

    it('sets user storage quota', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'set' }));
      await adminApi.storage.setUserQuota('u1', { storage_limit_bytes: 10737418240 }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/users/u1/storage-quota');
    });
  });

  // ---------------------------------------------------------------------------
  // Audit Logs
  // ---------------------------------------------------------------------------
  describe('auditLogs', () => {
    it('lists audit logs with filters', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.auditLogs.list({ action: 'user.login', page: 1 }, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toContain('action=user.login');
    });
  });

  // ---------------------------------------------------------------------------
  // Security
  // ---------------------------------------------------------------------------
  describe('security', () => {
    it('gets security events', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.security.getEvents({ severity: 'high' }, 'tok');
    });

    it('blocks and unblocks IP', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'blocked' }));
      await adminApi.security.blockIP({ ip_address: '1.2.3.4', reason: 'brute force' }, 'tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('POST');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'unblocked' }));
      await adminApi.security.unblockIP('1.2.3.4', 'tok');

      const [url, opts2] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/security/blocked-ips/1.2.3.4');
      expect(opts2.method).toBe('DELETE');
    });

    it('terminates session', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'terminated' }));
      await adminApi.security.terminateSession('sess1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/security/sessions/sess1');
      expect(opts.method).toBe('DELETE');
    });

    it('gets security dashboard', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ threat_level: 'low', active_sessions: 100 }));
      const result = await adminApi.security.getDashboard('tok');
      expect(result.threat_level).toBe('low');
    });
  });

  // ---------------------------------------------------------------------------
  // API Keys
  // ---------------------------------------------------------------------------
  describe('apiKeys', () => {
    it('lists API keys', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.apiKeys.list({ user_id: 'u1' }, 'tok');
    });

    it('revokes API key', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'revoked' }));
      await adminApi.apiKeys.revoke('key1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/api-keys/key1/revoke');
      expect(opts.method).toBe('POST');
    });

    it('gets API key stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_keys: 50, active_keys: 40 }));
      const result = await adminApi.apiKeys.getStats('tok');
      expect(result.total_keys).toBe(50);
    });
  });

  // ---------------------------------------------------------------------------
  // System
  // ---------------------------------------------------------------------------
  describe('system', () => {
    it('gets system health', async () => {
      const mockData = { overall_status: 'healthy', services: [], version: '1.0', uptime_seconds: 12345, last_check: '2025-01-01' };
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockData));

      const result = await adminApi.system.getHealth('tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/system/health');
      expect(result.overall_status).toBe('healthy');
    });

    it('gets system version', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ version: '2.0.0', environment: 'production' }));
      const result = await adminApi.system.getVersion('tok');
      expect(result.version).toBe('2.0.0');
    });

    it('gets service detail', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ name: 'database', status: 'healthy' }));
      await adminApi.system.getServiceDetail('database', 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/system/services/database');
    });

    it('gets performance metrics', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ avg_response_time_ms: 42 }));
      const result = await adminApi.system.getPerformance('tok');
      expect(result.avg_response_time_ms).toBe(42);
    });

    it('runs manual health check', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ overall_status: 'healthy', checked_at: '2025-01-01', duration_ms: 100 }));
      await adminApi.system.runHealthCheck('tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('POST');
    });

    it('gets uptime', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ uptime_seconds: 86400, uptime_formatted: '1d' }));
      const result = await adminApi.system.getUptime('tok');
      expect(result.uptime_seconds).toBe(86400);
    });
  });

  // ---------------------------------------------------------------------------
  // CAD v2
  // ---------------------------------------------------------------------------
  describe('cadV2', () => {
    it('lists CAD v2 components', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0, categories: {} }));
      await adminApi.cadV2.listComponents({ category: 'mcu' }, 'tok');
    });

    it('syncs registry', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ created: 5, updated: 10, total_in_registry: 100 }));
      const result = await adminApi.cadV2.syncRegistry('tok');
      expect(result.created).toBe(5);
    });
  });

  // ---------------------------------------------------------------------------
  // Starters
  // ---------------------------------------------------------------------------
  describe('starters', () => {
    it('lists starters', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0, categories: [] }));
      await adminApi.starters.list({ category: 'enclosure' }, 'tok');
    });

    it('features and unfeatures starter', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'featured' }));
      await adminApi.starters.feature('s1', 'tok');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'unfeatured' }));
      await adminApi.starters.unfeature('s1', 'tok');
    });

    it('reseeds starters', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'reseeded' }));
      await adminApi.starters.reseed('tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/starters/reseed');
    });
  });

  // ---------------------------------------------------------------------------
  // Marketplace
  // ---------------------------------------------------------------------------
  describe('marketplace', () => {
    it('gets marketplace stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_starters: 20, total_public_designs: 100 }));
      const result = await adminApi.marketplace.getStats('tok');
      expect(result.total_starters).toBe(20);
    });

    it('reorders featured', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'reordered' }));
      await adminApi.marketplace.reorderFeatured({ starter_ids: ['s1', 's2'] }, 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/marketplace/reorder-featured');
      expect(opts.method).toBe('POST');
    });
  });

  // ---------------------------------------------------------------------------
  // Content
  // ---------------------------------------------------------------------------
  describe('content', () => {
    it('lists and creates FAQs', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.content.listFaqs({ status: 'published' }, 'tok');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'faq1', title: 'How?' }));
      await adminApi.content.createFaq({ title: 'How?' }, 'tok');
    });

    it('publishes FAQ', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'faq1', status: 'published' }));
      await adminApi.content.publishFaq('faq1', 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/content/faqs/faq1/publish');
    });

    it('creates category', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'cat1', name: 'General' }));
      await adminApi.content.createCategory({ name: 'General', slug: 'general' }, 'tok');
    });

    it('gets content analytics', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_faqs: 10, total_articles: 20 }));
      const result = await adminApi.content.getAnalytics('tok');
      expect(result.total_faqs).toBe(10);
    });
  });

  // ---------------------------------------------------------------------------
  // Assemblies & Vendors & BOM
  // ---------------------------------------------------------------------------
  describe('assemblies', () => {
    it('lists assemblies and gets stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.assemblies.list(undefined, 'tok');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_assemblies: 50 }));
      const result = await adminApi.assemblies.getStats('tok');
      expect(result.total_assemblies).toBe(50);
    });
  });

  describe('vendors', () => {
    it('creates vendor', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'v1', name: 'digikey' }));
      await adminApi.vendors.create({ name: 'digikey', display_name: 'DigiKey' }, 'tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('POST');
    });

    it('gets vendor analytics', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_vendors: 5, active_vendors: 4 }));
      const result = await adminApi.vendors.getAnalytics('tok');
      expect(result.total_vendors).toBe(5);
    });
  });

  describe('bom', () => {
    it('gets audit queue', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.bom.getAuditQueue(undefined, 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/bom/audit-queue');
    });
  });

  // ---------------------------------------------------------------------------
  // Conversations
  // ---------------------------------------------------------------------------
  describe('conversations', () => {
    it('gets conversation stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_conversations: 1000 }));
      const result = await adminApi.conversations.getStats('tok');
      expect(result.total_conversations).toBe(1000);
    });

    it('gets flagged conversations', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ items: [], total: 0 }));
      await adminApi.conversations.getFlagged({ page: 1 }, 'tok');
    });

    it('gets conversation detail', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ id: 'conv1', messages: [] }));
      await adminApi.conversations.get('conv1', 'tok');

      const [url] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/conversations/conv1');
    });

    it('gets quality metrics', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ completion_rate: 0.85 }));
      const result = await adminApi.conversations.getQualityMetrics('tok');
      expect(result.completion_rate).toBe(0.85);
    });
  });

  // ---------------------------------------------------------------------------
  // Trash
  // ---------------------------------------------------------------------------
  describe('trash', () => {
    it('gets trash stats', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_deleted: 42 }));
      const result = await adminApi.trash.getStats('tok');
      expect(result.total_deleted).toBe(42);
    });

    it('updates retention policy', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'updated' }));
      await adminApi.trash.updateRetentionPolicy({ retention_days: 90 }, 'tok');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.method).toBe('PATCH');
    });

    it('permanently deletes resource', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'deleted' }));
      await adminApi.trash.permanentDelete('design', 'd1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/trash/design/d1/permanent');
      expect(opts.method).toBe('DELETE');
    });

    it('restores resource', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ message: 'restored' }));
      await adminApi.trash.restore('project', 'p1', 'tok');

      const [url, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(url).toBe('/api/v1/admin/trash/project/p1/restore');
      expect(opts.method).toBe('POST');
    });

    it('runs cleanup', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ total_cleaned: 10 }));
      const result = await adminApi.trash.cleanup('tok');
      expect(result.total_cleaned).toBe(10);
    });

    it('gets reclamation potential', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ reclaimable_bytes: 1073741824, reclaimable_human: '1 GB' }));
      const result = await adminApi.trash.getReclamationPotential('tok');
      expect(result.reclaimable_human).toBe('1 GB');
    });
  });

  // ---------------------------------------------------------------------------
  // Auth header passing
  // ---------------------------------------------------------------------------
  describe('auth token passing', () => {
    it('passes auth header when token provided', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}));
      await adminApi.system.getHealth('my-secret-token');

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.headers['Authorization']).toBe('Bearer my-secret-token');
    });

    it('omits auth header when no token', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}));
      await adminApi.system.getHealth();

      const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(opts.headers['Authorization']).toBeUndefined();
    });
  });

  // ---------------------------------------------------------------------------
  // Error handling
  // ---------------------------------------------------------------------------
  describe('error handling', () => {
    it('throws on 403 Forbidden', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 403));
      await expect(adminApi.users.list()).rejects.toThrow('403');
    });

    it('throws on 404 Not Found', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 404));
      await expect(adminApi.users.get('nonexistent')).rejects.toThrow('404');
    });

    it('throws on 500 Internal Server Error', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 500));
      await expect(adminApi.system.getHealth()).rejects.toThrow('500');
    });
  });
});
