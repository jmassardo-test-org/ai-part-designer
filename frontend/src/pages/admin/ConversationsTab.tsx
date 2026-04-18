/**
 * Conversations Tab Component (US-10.16).
 *
 * Conversation statistics, flagged conversation list, conversation detail
 * viewer with message thread, quality metrics, export.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  RefreshCw,
  BarChart3,
  Eye,
  Download,
  X,
  MessageSquare,
  Flag,
} from 'lucide-react';
import { adminApi } from '../../lib/api/admin';
import type {
  ConversationStats,
  FlaggedConversation,
  FlaggedConversationListResponse,
  ConversationDetail,
  ConversationQualityMetrics,
} from '../../types/admin';

// =============================================================================
// Sub-views
// =============================================================================

type ConversationView = 'flagged' | 'stats' | 'quality';

// =============================================================================
// Conversation Detail Modal
// =============================================================================

interface DetailModalProps {
  conversationId: string;
  onClose: () => void;
}

function ConversationDetailModal({ conversationId, onClose }: DetailModalProps) {
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      try {
        const data = await adminApi.conversations.get(conversationId);
        setDetail(data);
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [conversationId]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-2xl max-h-[85vh] overflow-hidden rounded-lg bg-white shadow-xl dark:bg-gray-800 flex flex-col">
        <div className="flex items-center justify-between border-b p-4 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Conversation Detail</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
          ) : detail ? (
            <div className="space-y-4">
              {/* Metadata */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500 dark:text-gray-400">User:</span>{' '}
                  <span className="font-medium text-gray-900 dark:text-white">{detail.user_email ?? detail.user_id}</span>
                </div>
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Status:</span>{' '}
                  <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${
                    detail.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                    detail.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                  }`}>{detail.status}</span>
                </div>
                {detail.title && (
                  <div className="col-span-2">
                    <span className="text-gray-500 dark:text-gray-400">Title:</span>{' '}
                    <span className="font-medium text-gray-900 dark:text-white">{detail.title}</span>
                  </div>
                )}
                <div>
                  <span className="text-gray-500 dark:text-gray-400">Created:</span>{' '}
                  <span className="text-gray-700 dark:text-gray-300">{new Date(detail.created_at).toLocaleString()}</span>
                </div>
                {detail.design_id && (
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">Design:</span>{' '}
                    <span className="font-mono text-xs text-gray-700 dark:text-gray-300">{detail.design_id}</span>
                  </div>
                )}
              </div>

              {/* Messages */}
              <div>
                <h4 className="mb-2 text-sm font-semibold text-gray-700 dark:text-gray-300">Messages ({detail.messages.length})</h4>
                <div className="space-y-3">
                  {detail.messages.map((msg, idx) => {
                    const role = (msg.role as string) ?? 'unknown';
                    const content = (msg.content as string) ?? JSON.stringify(msg);
                    const isUser = role === 'user';
                    return (
                      <div key={idx} className={`rounded-lg p-3 text-sm ${isUser ? 'bg-blue-50 dark:bg-blue-900/20' : 'bg-gray-50 dark:bg-gray-700'}`}>
                        <div className="mb-1 text-xs font-semibold uppercase text-gray-400">{role}</div>
                        <div className="whitespace-pre-wrap text-gray-900 dark:text-white">{content}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Intent / Build Plan / Result data */}
              {detail.intent_data && Object.keys(detail.intent_data).length > 0 && (
                <div>
                  <h4 className="mb-1 text-sm font-semibold text-gray-700 dark:text-gray-300">Intent Data</h4>
                  <pre className="rounded-md bg-gray-100 p-3 text-xs text-gray-700 dark:bg-gray-900 dark:text-gray-300 overflow-x-auto">
                    {JSON.stringify(detail.intent_data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="py-8 text-center text-sm text-gray-500">Failed to load conversation.</div>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * ConversationsTab shows conversation statistics, flagged conversations,
 * quality metrics, and allows viewing individual conversation threads.
 */
export function ConversationsTab() {
  const [view, setView] = useState<ConversationView>('flagged');

  // Stats
  const [stats, setStats] = useState<ConversationStats | null>(null);

  // Flagged
  const [flagged, setFlagged] = useState<FlaggedConversation[]>([]);
  const [flaggedTotal, setFlaggedTotal] = useState(0);
  const [flaggedPage, setFlaggedPage] = useState(1);
  const [isLoadingFlagged, setIsLoadingFlagged] = useState(false);

  // Quality
  const [quality, setQuality] = useState<ConversationQualityMetrics | null>(null);

  // Detail
  const [selectedConversation, setSelectedConversation] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const pageSize = 20;

  // -------------------------------------------------------------------------
  // Fetch functions
  // -------------------------------------------------------------------------

  const fetchStats = useCallback(async () => {
    try {
      const data = await adminApi.conversations.getStats();
      setStats(data);
    } catch {
      // silent
    }
  }, []);

  const fetchFlagged = useCallback(async () => {
    setIsLoadingFlagged(true);
    setError(null);
    try {
      const data: FlaggedConversationListResponse = await adminApi.conversations.getFlagged({ page: flaggedPage, page_size: pageSize });
      setFlagged(data.items);
      setFlaggedTotal(data.total);
    } catch (err) {
      setError('Failed to load flagged conversations');
      console.error(err);
    } finally {
      setIsLoadingFlagged(false);
    }
  }, [flaggedPage]);

  const fetchQuality = useCallback(async () => {
    try {
      const data = await adminApi.conversations.getQualityMetrics();
      setQuality(data);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    fetchStats(); // Always load stats
  }, [fetchStats]);

  useEffect(() => {
    if (view === 'flagged') fetchFlagged();
    if (view === 'quality') fetchQuality();
  }, [view, fetchFlagged, fetchQuality]);

  const handleExport = async () => {
    try {
      const blob = await adminApi.conversations.export({ format: 'csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `conversations-export-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export', err);
    }
  };

  // -------------------------------------------------------------------------
  // Render — Quality Metrics
  // -------------------------------------------------------------------------

  if (view === 'quality') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Quality Metrics</h2>
          <button onClick={() => setView('flagged')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
        </div>
        {!quality ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard label="Total Conversations" value={quality.total_conversations} />
            <StatCard label="Completed" value={quality.completed_conversations} />
            <StatCard label="Failed" value={quality.failed_conversations} />
            <StatCard label="Completion Rate" value={`${(quality.completion_rate * 100).toFixed(1)}%`} />
            <StatCard label="Avg Messages to Complete" value={quality.avg_messages_to_completion.toFixed(1)} />
            {Object.entries(quality.conversations_by_status).map(([k, v]) => (
              <StatCard key={k} label={`Status: ${k}`} value={v} />
            ))}
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Stats
  // -------------------------------------------------------------------------

  if (view === 'stats') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Conversation Statistics</h2>
          <button onClick={() => setView('flagged')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
        </div>
        {!stats ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <StatCard label="Total Conversations" value={stats.total_conversations} />
            <StatCard label="Total Messages" value={stats.total_messages.toLocaleString()} />
            <StatCard label="Avg Messages/Conversation" value={stats.avg_messages_per_conversation.toFixed(1)} />
            <StatCard label="Active Today" value={stats.active_today} />
            <StatCard label="Active This Week" value={stats.active_this_week} />
            {Object.entries(stats.conversations_by_status).map(([k, v]) => (
              <StatCard key={k} label={`Status: ${k}`} value={v} />
            ))}
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Flagged list (default)
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Conversations</h2>
        <div className="flex gap-2">
          <button onClick={() => setView('stats')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><BarChart3 className="h-4 w-4" /> Stats</button>
          <button onClick={() => setView('quality')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><MessageSquare className="h-4 w-4" /> Quality</button>
          <button onClick={handleExport} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><Download className="h-4 w-4" /> Export</button>
          <button onClick={fetchFlagged} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
        </div>
      </div>

      {/* Stats summary bar */}
      {stats && (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Total" value={stats.total_conversations} />
          <StatCard label="Active Today" value={stats.active_today} />
          <StatCard label="Avg Messages" value={stats.avg_messages_per_conversation.toFixed(1)} />
          <StatCard label="Flagged" value={flaggedTotal} />
        </div>
      )}

      {/* Loading / Error */}
      {isLoadingFlagged && <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>}
      {error && <div className="py-8 text-center text-red-500">{error}</div>}

      {/* Table */}
      {!isLoadingFlagged && !error && (
        <>
          {flagged.length === 0 ? (
            <div className="py-12 text-center text-sm text-gray-500">No flagged conversations.</div>
          ) : (
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Title</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Messages</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Flag Reason</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Created</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {flagged.map((conv) => (
                    <tr key={conv.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{conv.user_email ?? conv.user_id}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">{conv.title ?? '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                          conv.status === 'completed' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                          conv.status === 'failed' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' :
                          'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
                        }`}>{conv.status}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{conv.message_count}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                        <span className="flex items-center gap-1"><Flag className="h-3 w-3 text-orange-500" />{conv.flag_reason}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{new Date(conv.created_at).toLocaleDateString()}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <button onClick={() => setSelectedConversation(conv.id)} title="View Detail" className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700">
                          <Eye className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {flaggedTotal > pageSize && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500">Showing {((flaggedPage - 1) * pageSize) + 1}–{Math.min(flaggedPage * pageSize, flaggedTotal)} of {flaggedTotal}</span>
              <div className="flex gap-2">
                <button onClick={() => setFlaggedPage((p) => Math.max(1, p - 1))} disabled={flaggedPage === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
                <button onClick={() => setFlaggedPage((p) => p + 1)} disabled={flaggedPage * pageSize >= flaggedTotal} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Detail modal */}
      {selectedConversation && (
        <ConversationDetailModal conversationId={selectedConversation} onClose={() => setSelectedConversation(null)} />
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
