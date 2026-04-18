/**
 * Trash Tab Component (US-10.17).
 *
 * Trash stats by type, retention policy editor, browse trashed items,
 * permanent delete, restore, cleanup, and reclamation calculator.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  RefreshCw,
  Trash2,
  RotateCcw,
  Settings,
  HardDrive,
  X,
  AlertTriangle,
} from 'lucide-react';
import { adminApi } from '../../lib/api/admin';
import type {
  TrashStats,
  TrashResourceType,
  ReclamationPotential,
  TrashCleanupResponse,
} from '../../types/admin';

// =============================================================================
// Retention Policy Modal
// =============================================================================

interface RetentionModalProps {
  onClose: () => void;
  onSaved: () => void;
}

function RetentionPolicyModal({ onClose, onSaved }: RetentionModalProps) {
  const [days, setDays] = useState(30);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await adminApi.trash.updateRetentionPolicy({ retention_days: days });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update policy');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Retention Policy</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Retention Period (days)</label>
            <input type="number" min={1} max={365} value={days} onChange={(e) => setDays(Number(e.target.value))} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            <p className="mt-1 text-xs text-gray-400">Items older than this will be eligible for permanent deletion during cleanup.</p>
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Saving…' : 'Update'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Permanent Delete Confirmation
// =============================================================================

interface DeleteConfirmProps {
  resourceType: TrashResourceType;
  resourceId: string;
  onClose: () => void;
  onConfirm: () => void;
}

function PermanentDeleteModal({ resourceType, resourceId, onClose, onConfirm }: DeleteConfirmProps) {
  const [confirmText, setConfirmText] = useState('');
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-2 flex items-center gap-2">
          <AlertTriangle className="h-5 w-5 text-red-500" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Permanent Delete</h3>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          This will permanently remove this {resourceType} (ID: <span className="font-mono text-xs">{resourceId}</span>). This action <strong>cannot be undone</strong>.
        </p>
        <div className="mt-4">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Type &quot;DELETE&quot; to confirm</label>
          <input type="text" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
        </div>
        <div className="mt-4 flex justify-end gap-3">
          <button onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
          <button onClick={onConfirm} disabled={confirmText !== 'DELETE'} className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">Permanently Delete</button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Browse trashed items placeholder — faking a generic list until we have
// per-type list endpoints. Shows IDs from the stats types.
// =============================================================================

// =============================================================================
// Main Component
// =============================================================================

/**
 * TrashTab shows trash statistics, retention policy management,
 * browse/restore/permanent-delete trashed items, and reclamation calculator.
 */
export function TrashTab() {
  // Stats
  const [stats, setStats] = useState<TrashStats | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);

  // Reclamation
  const [reclamation, setReclamation] = useState<ReclamationPotential | null>(null);
  const [showReclamation, setShowReclamation] = useState(false);

  // Retention
  const [showRetention, setShowRetention] = useState(false);

  // Cleanup
  const [cleanupResult, setCleanupResult] = useState<TrashCleanupResponse | null>(null);
  const [isRunningCleanup, setIsRunningCleanup] = useState(false);

  // Action modals
  const [deleteTarget, setDeleteTarget] = useState<{ type: TrashResourceType; id: string } | null>(null);
  const [restoreTarget, setRestoreTarget] = useState<{ type: TrashResourceType; id: string } | null>(null);

  // Manual action input
  const [actionType, setActionType] = useState<TrashResourceType>('design');
  const [actionId, setActionId] = useState('');

  const [error, setError] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Fetch
  // -------------------------------------------------------------------------

  const fetchStats = useCallback(async () => {
    setIsLoadingStats(true);
    try {
      const data = await adminApi.trash.getStats();
      setStats(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingStats(false);
    }
  }, []);

  const fetchReclamation = useCallback(async () => {
    try {
      const data = await adminApi.trash.getReclamationPotential();
      setReclamation(data);
      setShowReclamation(true);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  const handleCleanup = async () => {
    setIsRunningCleanup(true);
    setCleanupResult(null);
    setError(null);
    try {
      const result = await adminApi.trash.cleanup();
      setCleanupResult(result);
      fetchStats();
    } catch (err) {
      setError('Cleanup failed');
      console.error(err);
    } finally {
      setIsRunningCleanup(false);
    }
  };

  const handlePermanentDelete = async () => {
    if (!deleteTarget) return;
    try {
      await adminApi.trash.permanentDelete(deleteTarget.type, deleteTarget.id);
      setDeleteTarget(null);
      fetchStats();
    } catch (err) {
      console.error('Permanent delete failed', err);
    }
  };

  const handleRestore = async () => {
    if (!restoreTarget) return;
    try {
      await adminApi.trash.restore(restoreTarget.type, restoreTarget.id);
      setRestoreTarget(null);
      fetchStats();
    } catch (err) {
      console.error('Restore failed', err);
    }
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Trash &amp; Data Retention</h2>
        <div className="flex gap-2">
          <button onClick={() => setShowRetention(true)} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300">
            <Settings className="h-4 w-4" /> Retention Policy
          </button>
          <button onClick={fetchReclamation} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300">
            <HardDrive className="h-4 w-4" /> Reclamation
          </button>
          <button onClick={handleCleanup} disabled={isRunningCleanup} className="flex items-center gap-1 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">
            {isRunningCleanup ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
            {isRunningCleanup ? 'Running…' : 'Run Cleanup'}
          </button>
        </div>
      </div>

      {/* Stats */}
      {isLoadingStats ? (
        <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
      ) : stats ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Total Deleted" value={stats.total_deleted} />
          <StatCard label="Designs" value={stats.deleted_designs} />
          <StatCard label="Projects" value={stats.deleted_projects} />
          <StatCard label="Assemblies" value={stats.deleted_assemblies} />
          <StatCard label="Files" value={stats.deleted_files} />
          <StatCard label="Oldest" value={stats.oldest_deleted_at ? new Date(stats.oldest_deleted_at).toLocaleDateString() : '—'} />
        </div>
      ) : null}

      {/* Cleanup result */}
      {cleanupResult && (
        <div className="rounded-lg border border-green-300 bg-green-50 p-4 dark:border-green-700 dark:bg-green-900/20">
          <h3 className="font-semibold text-green-800 dark:text-green-400">Cleanup Complete</h3>
          <p className="mt-1 text-sm text-green-700 dark:text-green-300">{cleanupResult.message}</p>
          <p className="text-sm text-green-600 dark:text-green-400">Total cleaned: {cleanupResult.total_cleaned} (retention: {cleanupResult.retention_days} days)</p>
          {Object.keys(cleanupResult.cleaned).length > 0 && (
            <ul className="mt-2 text-sm text-green-600 dark:text-green-400">
              {Object.entries(cleanupResult.cleaned).map(([type, count]) => (
                <li key={type}>{type}: {count}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {error && <div className="py-4 text-center text-red-500">{error}</div>}

      {/* Reclamation panel */}
      {showReclamation && reclamation && (
        <div className="rounded-lg border border-blue-300 bg-blue-50 p-4 dark:border-blue-700 dark:bg-blue-900/20">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-blue-800 dark:text-blue-400">Reclamation Potential</h3>
            <button onClick={() => setShowReclamation(false)} className="text-blue-400 hover:text-blue-600"><X className="h-4 w-4" /></button>
          </div>
          <div className="mt-2 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="text-sm">
              <span className="text-blue-600 dark:text-blue-400">Reclaimable Files:</span>{' '}
              <span className="font-semibold text-blue-800 dark:text-blue-200">{reclamation.reclaimable_files}</span>
            </div>
            <div className="text-sm">
              <span className="text-blue-600 dark:text-blue-400">Reclaimable Space:</span>{' '}
              <span className="font-semibold text-blue-800 dark:text-blue-200">{reclamation.reclaimable_human}</span>
            </div>
            <div className="text-sm">
              <span className="text-blue-600 dark:text-blue-400">By Type:</span>{' '}
              <span className="font-semibold text-blue-800 dark:text-blue-200">
                {Object.entries(reclamation.by_type).map(([t, c]) => `${t}: ${c}`).join(', ') || '—'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Manual actions: Restore / Permanent Delete */}
      <div className="rounded-lg border bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
        <h3 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">Item Actions</h3>
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">Enter a resource type and ID to restore or permanently delete a specific trashed item.</p>
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Type</label>
            <select value={actionType} onChange={(e) => setActionType(e.target.value as TrashResourceType)} className="mt-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
              <option value="design">Design</option>
              <option value="project">Project</option>
              <option value="assembly">Assembly</option>
              <option value="file">File</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">Resource ID</label>
            <input type="text" value={actionId} onChange={(e) => setActionId(e.target.value)} placeholder="UUID" className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <button
            onClick={() => { if (actionId) setRestoreTarget({ type: actionType, id: actionId }); }}
            disabled={!actionId}
            className="flex items-center gap-1 rounded-md border border-green-300 px-4 py-2 text-sm font-medium text-green-700 hover:bg-green-50 disabled:opacity-50 dark:border-green-700 dark:text-green-400 dark:hover:bg-green-900/20"
          >
            <RotateCcw className="h-4 w-4" /> Restore
          </button>
          <button
            onClick={() => { if (actionId) setDeleteTarget({ type: actionType, id: actionId }); }}
            disabled={!actionId}
            className="flex items-center gap-1 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            <Trash2 className="h-4 w-4" /> Delete Permanently
          </button>
        </div>
      </div>

      {/* Modals */}
      {showRetention && <RetentionPolicyModal onClose={() => setShowRetention(false)} onSaved={() => { setShowRetention(false); fetchStats(); }} />}
      {deleteTarget && (
        <PermanentDeleteModal
          resourceType={deleteTarget.type}
          resourceId={deleteTarget.id}
          onClose={() => setDeleteTarget(null)}
          onConfirm={handlePermanentDelete}
        />
      )}
      {restoreTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Restore Item</h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Restore this {restoreTarget.type} (ID: <span className="font-mono text-xs">{restoreTarget.id}</span>)?
            </p>
            <div className="mt-4 flex justify-end gap-3">
              <button onClick={() => setRestoreTarget(null)} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
              <button onClick={handleRestore} className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700">Restore</button>
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
