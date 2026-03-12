/**
 * Assemblies Tab Component (US-10.15).
 *
 * Assembly browser, assembly stats, vendor CRUD (list/create/edit/delete),
 * vendor analytics, bulk price update, BOM audit queue.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  Plus,
  Search,
  RefreshCw,
  Pencil,
  Trash2,
  BarChart3,
  X,
  Package,
  DollarSign,
  ClipboardList,
} from 'lucide-react';
import { adminApi } from '../../lib/api/admin';
import type {
  AdminAssembly,
  AdminAssemblyListResponse,
  AssemblyStats,
  AdminVendor,
  VendorCreateRequest,
  VendorUpdateRequest,
  VendorAnalytics,
  BOMAuditItem,
  BulkPriceUpdateRequest,
} from '../../types/admin';

// =============================================================================
// Sub-views
// =============================================================================

type AssemblyView = 'assemblies' | 'vendors' | 'bom-audit' | 'stats';

// =============================================================================
// Vendor Form Modal
// =============================================================================

interface VendorFormModalProps {
  vendor: AdminVendor | null;
  onClose: () => void;
  onSaved: () => void;
}

function VendorFormModal({ vendor, onClose, onSaved }: VendorFormModalProps) {
  const isEdit = !!vendor;
  const [name, setName] = useState(vendor?.name ?? '');
  const [displayName, setDisplayName] = useState(vendor?.display_name ?? '');
  const [website, setWebsite] = useState(vendor?.website ?? '');
  const [logoUrl, setLogoUrl] = useState(vendor?.logo_url ?? '');
  const [apiType, setApiType] = useState(vendor?.api_type ?? '');
  const [categoriesStr, setCategoriesStr] = useState((vendor?.categories ?? []).join(', '));
  const [isActive, setIsActive] = useState(vendor?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const cats = categoriesStr.split(',').map((s) => s.trim()).filter(Boolean);
      if (isEdit) {
        const body: VendorUpdateRequest = {
          name: name || undefined,
          display_name: displayName || undefined,
          website: website || undefined,
          logo_url: logoUrl || undefined,
          api_type: apiType || undefined,
          categories: cats.length > 0 ? cats : undefined,
          is_active: isActive,
        };
        await adminApi.vendors.update(vendor!.id, body);
      } else {
        const body: VendorCreateRequest = {
          name,
          display_name: displayName,
          website: website || undefined,
          logo_url: logoUrl || undefined,
          api_type: apiType || undefined,
          categories: cats.length > 0 ? cats : undefined,
        };
        await adminApi.vendors.create(body);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save vendor');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-lg rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{isEdit ? 'Edit Vendor' : 'Create Vendor'}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name *</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Display Name *</label>
            <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Website</label>
            <input type="url" value={website} onChange={(e) => setWebsite(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Logo URL</label>
            <input type="url" value={logoUrl} onChange={(e) => setLogoUrl(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">API Type</label>
            <input type="text" value={apiType} onChange={(e) => setApiType(e.target.value)} placeholder="e.g. rest, graphql" className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Categories (comma-separated)</label>
            <input type="text" value={categoriesStr} onChange={(e) => setCategoriesStr(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          {isEdit && (
            <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
              <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} className="rounded" />
              Active
            </label>
          )}
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Saving…' : isEdit ? 'Update' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Bulk Price Update Modal
// =============================================================================

interface BulkPriceModalProps {
  onClose: () => void;
}

function BulkPriceModal({ onClose }: BulkPriceModalProps) {
  const [rows, setRows] = useState<Array<{ component_id: string; new_price: string }>>([{ component_id: '', new_price: '' }]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const addRow = () => setRows([...rows, { component_id: '', new_price: '' }]);
  const removeRow = (idx: number) => setRows(rows.filter((_, i) => i !== idx));
  const updateRow = (idx: number, field: 'component_id' | 'new_price', value: string) => {
    const copy = [...rows];
    copy[idx] = { ...copy[idx], [field]: value };
    setRows(copy);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updates = rows
        .filter((r) => r.component_id && r.new_price)
        .map((r) => ({ component_id: r.component_id, new_price: parseFloat(r.new_price) }));
      if (updates.length === 0) {
        setError('Add at least one valid row');
        setSaving(false);
        return;
      }
      const body: BulkPriceUpdateRequest = { updates };
      await adminApi.components.bulkPriceUpdate(body);
      setSuccess(`Updated ${updates.length} prices`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update prices');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-lg max-h-[80vh] overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Bulk Price Update</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-3 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        {success && <div className="mb-3 rounded-md bg-green-50 p-3 text-sm text-green-700 dark:bg-green-900/30 dark:text-green-400">{success}</div>}
        <form onSubmit={handleSubmit} className="space-y-3">
          {rows.map((row, idx) => (
            <div key={idx} className="flex gap-2">
              <input type="text" placeholder="Component ID" value={row.component_id} onChange={(e) => updateRow(idx, 'component_id', e.target.value)} className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
              <input type="number" step="0.01" placeholder="New Price" value={row.new_price} onChange={(e) => updateRow(idx, 'new_price', e.target.value)} className="w-32 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
              <button type="button" onClick={() => removeRow(idx)} className="rounded p-2 text-gray-400 hover:text-red-500"><Trash2 className="h-4 w-4" /></button>
            </div>
          ))}
          <button type="button" onClick={addRow} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700"><Plus className="h-4 w-4" /> Add Row</button>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Updating…' : 'Update Prices'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * AssembliesTab provides assembly browsing, vendor management,
 * BOM audit queue, and assembly stats.
 */
export function AssembliesTab() {
  const [view, setView] = useState<AssemblyView>('assemblies');

  // Assemblies
  const [assemblies, setAssemblies] = useState<AdminAssembly[]>([]);
  const [assemblyTotal, setAssemblyTotal] = useState(0);
  const [assemblyPage, setAssemblyPage] = useState(1);
  const [assemblySearch, setAssemblySearch] = useState('');
  const [assemblyStatus, setAssemblyStatus] = useState('');
  const [isLoadingAssemblies, setIsLoadingAssemblies] = useState(false);

  // Stats
  const [stats, setStats] = useState<AssemblyStats | null>(null);

  // Vendors
  const [vendors, setVendors] = useState<AdminVendor[]>([]);
  const [vendorTotal, setVendorTotal] = useState(0);
  const [vendorPage, setVendorPage] = useState(1);
  const [isLoadingVendors, setIsLoadingVendors] = useState(false);
  const [showVendorModal, setShowVendorModal] = useState(false);
  const [editVendor, setEditVendor] = useState<AdminVendor | null>(null);
  const [deleteVendorConfirm, setDeleteVendorConfirm] = useState<AdminVendor | null>(null);
  const [vendorAnalytics, setVendorAnalytics] = useState<VendorAnalytics | null>(null);

  // BOM
  const [bomItems, setBomItems] = useState<BOMAuditItem[]>([]);
  const [bomTotal, setBomTotal] = useState(0);
  const [bomPage, setBomPage] = useState(1);
  const [isLoadingBom, setIsLoadingBom] = useState(false);

  // Modals
  const [showBulkPrice, setShowBulkPrice] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const pageSize = 20;

  // -------------------------------------------------------------------------
  // Fetch functions
  // -------------------------------------------------------------------------

  const fetchAssemblies = useCallback(async () => {
    setIsLoadingAssemblies(true);
    setError(null);
    try {
      const data: AdminAssemblyListResponse = await adminApi.assemblies.list({
        search: assemblySearch || undefined,
        status: assemblyStatus || undefined,
        page: assemblyPage,
        page_size: pageSize,
      });
      setAssemblies(data.items);
      setAssemblyTotal(data.total);
    } catch (err) {
      setError('Failed to load assemblies');
      console.error(err);
    } finally {
      setIsLoadingAssemblies(false);
    }
  }, [assemblySearch, assemblyStatus, assemblyPage]);

  const fetchStats = useCallback(async () => {
    try {
      const data = await adminApi.assemblies.getStats();
      setStats(data);
    } catch {
      // silent
    }
  }, []);

  const fetchVendors = useCallback(async () => {
    setIsLoadingVendors(true);
    try {
      const data = await adminApi.vendors.list({ page: vendorPage, page_size: pageSize });
      setVendors(data.items);
      setVendorTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingVendors(false);
    }
  }, [vendorPage]);

  const fetchVendorAnalytics = useCallback(async () => {
    try {
      const data = await adminApi.vendors.getAnalytics();
      setVendorAnalytics(data);
    } catch {
      // silent
    }
  }, []);

  const fetchBom = useCallback(async () => {
    setIsLoadingBom(true);
    try {
      const data = await adminApi.bom.getAuditQueue({ page: bomPage, page_size: pageSize });
      setBomItems(data.items);
      setBomTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingBom(false);
    }
  }, [bomPage]);

  useEffect(() => {
    if (view === 'assemblies') fetchAssemblies();
    if (view === 'stats') fetchStats();
    if (view === 'vendors') { fetchVendors(); fetchVendorAnalytics(); }
    if (view === 'bom-audit') fetchBom();
  }, [view, fetchAssemblies, fetchStats, fetchVendors, fetchVendorAnalytics, fetchBom]);

  const handleDeleteVendor = async (vendor: AdminVendor) => {
    try {
      await adminApi.vendors.delete(vendor.id);
      setDeleteVendorConfirm(null);
      fetchVendors();
    } catch (err) {
      console.error('Failed to delete vendor', err);
    }
  };

  // -------------------------------------------------------------------------
  // Render — Stats
  // -------------------------------------------------------------------------

  if (view === 'stats') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Assembly Statistics</h2>
          <button onClick={() => setView('assemblies')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
        </div>
        {!stats ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard label="Total Assemblies" value={stats.total_assemblies} />
            <StatCard label="Avg Components/Assembly" value={stats.avg_components_per_assembly.toFixed(1)} />
            <StatCard label="Created Today" value={stats.assemblies_created_today} />
            <StatCard label="Created This Week" value={stats.assemblies_created_this_week} />
            {Object.entries(stats.assemblies_by_status).map(([k, v]) => (
              <StatCard key={k} label={`Status: ${k}`} value={v} />
            ))}
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Vendors
  // -------------------------------------------------------------------------

  if (view === 'vendors') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Vendor Management</h2>
          <div className="flex gap-2">
            <button onClick={() => setView('assemblies')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
            <button onClick={() => setShowBulkPrice(true)} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><DollarSign className="h-4 w-4" /> Bulk Price</button>
            <button onClick={() => setShowVendorModal(true)} className="flex items-center gap-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"><Plus className="h-4 w-4" /> New Vendor</button>
          </div>
        </div>

        {/* Vendor analytics summary */}
        {vendorAnalytics && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Total Vendors" value={vendorAnalytics.total_vendors} />
            <StatCard label="Active Vendors" value={vendorAnalytics.active_vendors} />
            <StatCard label="Most Used" value={vendorAnalytics.most_used_vendors.length} />
          </div>
        )}

        {isLoadingVendors ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : vendors.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500">No vendors found.</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Display Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">API Type</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Categories</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                {vendors.map((v) => (
                  <tr key={v.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{v.name}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{v.display_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{v.api_type ?? '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{v.categories.join(', ') || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${v.is_active ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'}`}>
                        {v.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <button onClick={() => setEditVendor(v)} title="Edit" className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"><Pencil className="h-4 w-4" /></button>
                        <button onClick={() => setDeleteVendorConfirm(v)} title="Delete" className="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30"><Trash2 className="h-4 w-4" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {vendorTotal > pageSize && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Showing {((vendorPage - 1) * pageSize) + 1}–{Math.min(vendorPage * pageSize, vendorTotal)} of {vendorTotal}</span>
            <div className="flex gap-2">
              <button onClick={() => setVendorPage((p) => Math.max(1, p - 1))} disabled={vendorPage === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
              <button onClick={() => setVendorPage((p) => p + 1)} disabled={vendorPage * pageSize >= vendorTotal} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
            </div>
          </div>
        )}

        {/* Modals */}
        {(showVendorModal || editVendor) && (
          <VendorFormModal vendor={editVendor} onClose={() => { setShowVendorModal(false); setEditVendor(null); }} onSaved={() => { setShowVendorModal(false); setEditVendor(null); fetchVendors(); }} />
        )}
        {showBulkPrice && <BulkPriceModal onClose={() => setShowBulkPrice(false)} />}
        {deleteVendorConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
            <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Delete Vendor</h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Delete vendor &quot;{deleteVendorConfirm.display_name}&quot;? This cannot be undone.</p>
              <div className="mt-4 flex justify-end gap-3">
                <button onClick={() => setDeleteVendorConfirm(null)} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
                <button onClick={() => handleDeleteVendor(deleteVendorConfirm)} className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Delete</button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — BOM Audit Queue
  // -------------------------------------------------------------------------

  if (view === 'bom-audit') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">BOM Audit Queue</h2>
          <div className="flex gap-2">
            <button onClick={() => setView('assemblies')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
            <button onClick={fetchBom} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
          </div>
        </div>

        {isLoadingBom ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : bomItems.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500">No items in audit queue.</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Part Number</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Category</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Unit Cost</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                {bomItems.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-white">{item.part_number ?? '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{item.description}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{item.category}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{item.unit_cost != null ? `$${item.unit_cost.toFixed(2)}` : '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{item.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {bomTotal > pageSize && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-500">Showing {((bomPage - 1) * pageSize) + 1}–{Math.min(bomPage * pageSize, bomTotal)} of {bomTotal}</span>
            <div className="flex gap-2">
              <button onClick={() => setBomPage((p) => Math.max(1, p - 1))} disabled={bomPage === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
              <button onClick={() => setBomPage((p) => p + 1)} disabled={bomPage * pageSize >= bomTotal} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Assemblies list (default)
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Assemblies & BOM</h2>
        <div className="flex gap-2">
          <button onClick={() => setView('stats')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><BarChart3 className="h-4 w-4" /> Stats</button>
          <button onClick={() => setView('vendors')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><Package className="h-4 w-4" /> Vendors</button>
          <button onClick={() => setView('bom-audit')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><ClipboardList className="h-4 w-4" /> BOM Audit</button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <input type="text" placeholder="Search assemblies…" value={assemblySearch} onChange={(e) => { setAssemblySearch(e.target.value); setAssemblyPage(1); }} className="rounded-md border border-gray-300 pl-9 pr-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
        </div>
        <select value={assemblyStatus} onChange={(e) => { setAssemblyStatus(e.target.value); setAssemblyPage(1); }} className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
          <option value="">All Status</option>
          <option value="draft">Draft</option>
          <option value="active">Active</option>
          <option value="archived">Archived</option>
        </select>
        <button onClick={fetchAssemblies} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
      </div>

      {/* Loading / Error */}
      {isLoadingAssemblies && <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>}
      {error && <div className="py-8 text-center text-red-500">{error}</div>}

      {/* Table */}
      {!isLoadingAssemblies && !error && (
        <>
          {assemblies.length === 0 ? (
            <div className="py-12 text-center text-sm text-gray-500">No assemblies found.</div>
          ) : (
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Owner</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Components</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Version</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {assemblies.map((a) => (
                    <tr key={a.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{a.name}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${a.status === 'active' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : a.status === 'draft' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'}`}>
                          {a.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{a.user_email ?? a.user_id}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{a.component_count}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">v{a.version}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{new Date(a.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {assemblyTotal > pageSize && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Showing {((assemblyPage - 1) * pageSize) + 1}–{Math.min(assemblyPage * pageSize, assemblyTotal)} of {assemblyTotal}</span>
              <div className="flex gap-2">
                <button onClick={() => setAssemblyPage((p) => Math.max(1, p - 1))} disabled={assemblyPage === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
                <button onClick={() => setAssemblyPage((p) => p + 1)} disabled={assemblyPage * pageSize >= assemblyTotal} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
              </div>
            </div>
          )}
        </>
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
