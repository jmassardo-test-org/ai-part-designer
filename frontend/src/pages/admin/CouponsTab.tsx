/**
 * Coupons Tab Component (US-10.5c).
 *
 * Full coupon management: list with filters, create modal, edit modal,
 * view usage, apply to user, bulk apply, promotion analytics.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  Plus,
  Search,
  RefreshCw,
  Pencil,
  Trash2,
  Eye,
  Tag,
  Users,
  BarChart3,
  X,
} from 'lucide-react';
import { adminApi } from '../../lib/api/admin';
import type {
  AdminCoupon,
  CouponListResponse,
  CreateCouponRequest,
  UpdateCouponRequest,
  CouponUsageResponse,
  CouponRedemption,
  PromotionAnalyticsResponse,
  BulkApplyCouponRequest,
} from '../../types/admin';

// =============================================================================
// Sub-views
// =============================================================================

type CouponView = 'list' | 'analytics';

// =============================================================================
// Create / Edit Modal
// =============================================================================

interface CouponFormModalProps {
  coupon: AdminCoupon | null;
  onClose: () => void;
  onSaved: () => void;
}

function CouponFormModal({ coupon, onClose, onSaved }: CouponFormModalProps) {
  const isEdit = !!coupon;
  const [code, setCode] = useState(coupon?.code ?? '');
  const [description, setDescription] = useState(coupon?.description ?? '');
  const [couponType, setCouponType] = useState(coupon?.coupon_type ?? 'discount_percent');
  const [discountPercent, setDiscountPercent] = useState<number | ''>(coupon?.discount_percent ?? '');
  const [discountAmount, setDiscountAmount] = useState<number | ''>(coupon?.discount_amount ?? '');
  const [freeCredits, setFreeCredits] = useState<number | ''>(coupon?.free_credits ?? '');
  const [upgradeTier, setUpgradeTier] = useState(coupon?.upgrade_tier ?? '');
  const [validFrom, setValidFrom] = useState(coupon?.valid_from?.split('T')[0] ?? '');
  const [validUntil, setValidUntil] = useState(coupon?.valid_until?.split('T')[0] ?? '');
  const [maxUses, setMaxUses] = useState<number | ''>(coupon?.max_uses ?? '');
  const [maxUsesPerUser, setMaxUsesPerUser] = useState<number>(coupon?.max_uses_per_user ?? 1);
  const [newUsersOnly, setNewUsersOnly] = useState(coupon?.new_users_only ?? false);
  const [isActive, setIsActive] = useState(coupon?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (isEdit) {
        const body: UpdateCouponRequest = {
          description: description || undefined,
          valid_from: validFrom || undefined,
          valid_until: validUntil || undefined,
          max_uses: maxUses !== '' ? maxUses : undefined,
          max_uses_per_user: maxUsesPerUser,
          is_active: isActive,
          new_users_only: newUsersOnly,
        };
        await adminApi.coupons.update(coupon!.code, body);
      } else {
        const body: CreateCouponRequest = {
          code,
          description: description || undefined,
          coupon_type: couponType,
          discount_percent: discountPercent !== '' ? discountPercent : undefined,
          discount_amount: discountAmount !== '' ? discountAmount : undefined,
          free_credits: freeCredits !== '' ? freeCredits : undefined,
          upgrade_tier: upgradeTier || undefined,
          valid_from: validFrom || undefined,
          valid_until: validUntil || undefined,
          max_uses: maxUses !== '' ? maxUses : undefined,
          max_uses_per_user: maxUsesPerUser,
          new_users_only: newUsersOnly,
        };
        await adminApi.coupons.create(body);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save coupon');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {isEdit ? 'Edit Coupon' : 'Create Coupon'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Code *</label>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                required
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>
          {!isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Type *</label>
              <select
                value={couponType}
                onChange={(e) => setCouponType(e.target.value)}
                className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              >
                <option value="discount_percent">Discount %</option>
                <option value="discount_amount">Discount $</option>
                <option value="free_credits">Free Credits</option>
                <option value="upgrade_tier">Tier Upgrade</option>
              </select>
            </div>
          )}
          {couponType === 'discount_percent' && !isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Discount %</label>
              <input type="number" min={1} max={100} value={discountPercent} onChange={(e) => setDiscountPercent(e.target.value ? Number(e.target.value) : '')} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
          )}
          {couponType === 'discount_amount' && !isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Discount Amount (cents)</label>
              <input type="number" min={1} value={discountAmount} onChange={(e) => setDiscountAmount(e.target.value ? Number(e.target.value) : '')} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
          )}
          {couponType === 'free_credits' && !isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Free Credits</label>
              <input type="number" min={1} value={freeCredits} onChange={(e) => setFreeCredits(e.target.value ? Number(e.target.value) : '')} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
          )}
          {couponType === 'upgrade_tier' && !isEdit && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Upgrade Tier</label>
              <input type="text" value={upgradeTier} onChange={(e) => setUpgradeTier(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Valid From</label>
              <input type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Valid Until</label>
              <input type="date" value={validUntil} onChange={(e) => setValidUntil(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Max Uses</label>
              <input type="number" min={1} value={maxUses} onChange={(e) => setMaxUses(e.target.value ? Number(e.target.value) : '')} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Max Per User</label>
              <input type="number" min={1} value={maxUsesPerUser} onChange={(e) => setMaxUsesPerUser(Number(e.target.value))} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
          </div>
          <div className="flex gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input type="checkbox" checked={newUsersOnly} onChange={(e) => setNewUsersOnly(e.target.checked)} className="rounded" />
              New users only
            </label>
            {isEdit && (
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="rounded" />
                Active
              </label>
            )}
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">
              Cancel
            </button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {saving ? 'Saving…' : isEdit ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Usage Modal
// =============================================================================

interface UsageModalProps {
  couponCode: string;
  onClose: () => void;
}

function UsageModal({ couponCode, onClose }: UsageModalProps) {
  const [items, setItems] = useState<CouponRedemption[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const pageSize = 10;

  const fetchUsage = useCallback(async () => {
    setIsLoading(true);
    try {
      const data: CouponUsageResponse = await adminApi.coupons.getUsage(couponCode, { page, page_size: pageSize });
      setItems(data.items);
      setTotal(data.total);
    } catch {
      // ignore
    } finally {
      setIsLoading(false);
    }
  }, [couponCode, page]);

  useEffect(() => { fetchUsage(); }, [fetchUsage]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Usage — {couponCode}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-8"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : items.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-500">No redemptions yet.</p>
        ) : (
          <>
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">User</th>
                  <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">Redeemed At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {items.map((r) => (
                  <tr key={r.id}>
                    <td className="px-4 py-2 text-sm text-gray-900 dark:text-white">{r.user_email ?? r.user_id}</td>
                    <td className="px-4 py-2 text-sm text-gray-500">{new Date(r.redeemed_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-3 flex items-center justify-between">
              <span className="text-xs text-gray-500">Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}</span>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded border px-2 py-1 text-xs disabled:opacity-50">Prev</button>
                <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total} className="rounded border px-2 py-1 text-xs disabled:opacity-50">Next</button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Apply to User Modal
// =============================================================================

interface ApplyToUserModalProps {
  onClose: () => void;
}

function ApplyToUserModal({ onClose }: ApplyToUserModalProps) {
  const [userId, setUserId] = useState('');
  const [couponCode, setCouponCode] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await adminApi.coupons.applyToUser(userId, { coupon_code: couponCode });
      setSuccess('Coupon applied successfully');
      setUserId('');
      setCouponCode('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply coupon');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Apply Coupon to User</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        {success && <div className="mb-3 rounded-md bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-400">{success}</div>}
        <form onSubmit={handleApply} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">User ID *</label>
            <input type="text" value={userId} onChange={(e) => setUserId(e.target.value)} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Coupon Code *</label>
            <input type="text" value={couponCode} onChange={(e) => setCouponCode(e.target.value.toUpperCase())} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Applying…' : 'Apply'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Bulk Apply Modal
// =============================================================================

interface BulkApplyModalProps {
  onClose: () => void;
}

function BulkApplyModal({ onClose }: BulkApplyModalProps) {
  const [couponCode, setCouponCode] = useState('');
  const [target, setTarget] = useState('all');
  const [targetValue, setTargetValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleBulkApply = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const body: BulkApplyCouponRequest = { coupon_code: couponCode, target, target_value: targetValue || undefined };
      const result = await adminApi.coupons.bulkApply(body);
      setSuccess(`Applied to ${result.success_count} of ${result.total} users`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk apply failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Bulk Apply Coupon</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        {success && <div className="mb-3 rounded-md bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-400">{success}</div>}
        <form onSubmit={handleBulkApply} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Coupon Code *</label>
            <input type="text" value={couponCode} onChange={(e) => setCouponCode(e.target.value.toUpperCase())} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Target</label>
            <select value={target} onChange={(e) => setTarget(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
              <option value="all">All Users</option>
              <option value="tier">By Tier</option>
              <option value="organization">By Organization</option>
            </select>
          </div>
          {target !== 'all' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Target Value</label>
              <input type="text" value={targetValue} onChange={(e) => setTargetValue(e.target.value)} placeholder={target === 'tier' ? 'e.g. free' : 'Organization ID'} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
          )}
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Applying…' : 'Bulk Apply'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Main Tab Component
// =============================================================================

/**
 * CouponsTab provides full CRUD management for coupon codes and promotions.
 */
export function CouponsTab() {
  const [view, setView] = useState<CouponView>('list');
  const [items, setItems] = useState<AdminCoupon[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Modals
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editCoupon, setEditCoupon] = useState<AdminCoupon | null>(null);
  const [usageCouponCode, setUsageCouponCode] = useState<string | null>(null);
  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showBulkApplyModal, setShowBulkApplyModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Analytics
  const [analytics, setAnalytics] = useState<PromotionAnalyticsResponse | null>(null);

  const fetchCoupons = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data: CouponListResponse = await adminApi.coupons.list({
        search: searchQuery || undefined,
        status: statusFilter || undefined,
        type: typeFilter || undefined,
        page,
        page_size: pageSize,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError('Failed to load coupons');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, statusFilter, typeFilter, page]);

  const fetchAnalytics = useCallback(async () => {
    try {
      const data = await adminApi.coupons.getPromotionAnalytics();
      setAnalytics(data);
    } catch {
      // Silently fail for analytics
    }
  }, []);

  useEffect(() => {
    if (view === 'list') fetchCoupons();
    if (view === 'analytics') fetchAnalytics();
  }, [view, fetchCoupons, fetchAnalytics]);

  const handleDelete = async (code: string) => {
    try {
      await adminApi.coupons.delete(code);
      setDeleteConfirm(null);
      fetchCoupons();
    } catch (err) {
      console.error('Failed to delete coupon', err);
    }
  };

  // -------------------------------------------------------------------------
  // Render — Analytics view
  // -------------------------------------------------------------------------

  if (view === 'analytics') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Promotion Analytics</h2>
          <button onClick={() => setView('list')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">
            Back to List
          </button>
        </div>
        {!analytics ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Coupons" value={analytics.total_coupons} />
            <StatCard label="Active" value={analytics.active_coupons} />
            <StatCard label="Total Redemptions" value={analytics.total_redemptions} />
            <StatCard label="Most Used" value={analytics.most_used_coupons.length} />
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — List view
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Coupon Management</h2>
        <div className="flex gap-2">
          <button onClick={() => setView('analytics')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300">
            <BarChart3 className="h-4 w-4" /> Analytics
          </button>
          <button onClick={() => setShowApplyModal(true)} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300">
            <Tag className="h-4 w-4" /> Apply to User
          </button>
          <button onClick={() => setShowBulkApplyModal(true)} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300">
            <Users className="h-4 w-4" /> Bulk Apply
          </button>
          <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            <Plus className="h-4 w-4" /> Create Coupon
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search coupons…"
            value={searchQuery}
            onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }}
            className="rounded-md border border-gray-300 pl-9 pr-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          />
        </div>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="expired">Expired</option>
        </select>
        <select value={typeFilter} onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
          <option value="">All Types</option>
          <option value="discount_percent">Discount %</option>
          <option value="discount_amount">Discount $</option>
          <option value="free_credits">Free Credits</option>
          <option value="upgrade_tier">Tier Upgrade</option>
        </select>
        <button onClick={fetchCoupons} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {/* Loading / Error */}
      {isLoading && <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>}
      {error && <div className="py-8 text-center text-red-500">{error}</div>}

      {/* Table */}
      {!isLoading && !error && (
        <>
          {items.length === 0 ? (
            <div className="py-12 text-center text-sm text-gray-500">No coupons found.</div>
          ) : (
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Code</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Value</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Uses</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Valid Until</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {items.map((coupon) => (
                    <tr key={coupon.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="whitespace-nowrap px-4 py-3 text-sm font-mono font-medium text-gray-900 dark:text-white">{coupon.code}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{coupon.coupon_type}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {coupon.discount_percent != null && `${coupon.discount_percent}%`}
                        {coupon.discount_amount != null && `$${(coupon.discount_amount / 100).toFixed(2)}`}
                        {coupon.free_credits != null && `${coupon.free_credits} credits`}
                        {coupon.upgrade_tier && `→ ${coupon.upgrade_tier}`}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${coupon.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'}`}>
                          {coupon.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {coupon.current_uses}{coupon.max_uses != null ? ` / ${coupon.max_uses}` : ''}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        {coupon.valid_until ? new Date(coupon.valid_until).toLocaleDateString() : '—'}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <div className="flex justify-end gap-1">
                          <button onClick={() => setUsageCouponCode(coupon.code)} title="View Usage" className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700">
                            <Eye className="h-4 w-4" />
                          </button>
                          <button onClick={() => setEditCoupon(coupon)} title="Edit" className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700">
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button onClick={() => setDeleteConfirm(coupon.code)} title="Delete" className="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30">
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">
                Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
                <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      {(showCreateModal || editCoupon) && (
        <CouponFormModal
          coupon={editCoupon}
          onClose={() => { setShowCreateModal(false); setEditCoupon(null); }}
          onSaved={() => { setShowCreateModal(false); setEditCoupon(null); fetchCoupons(); }}
        />
      )}
      {usageCouponCode && <UsageModal couponCode={usageCouponCode} onClose={() => setUsageCouponCode(null)} />}
      {showApplyModal && <ApplyToUserModal onClose={() => setShowApplyModal(false)} />}
      {showBulkApplyModal && <BulkApplyModal onClose={() => setShowBulkApplyModal(false)} />}

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Delete Coupon</h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Are you sure you want to delete coupon <strong>{deleteConfirm}</strong>? This cannot be undone.</p>
            <div className="mt-4 flex justify-end gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Stat Card helper
// =============================================================================

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}
