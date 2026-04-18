/**
 * Security Dashboard Tab Component (US-10.13 expansion).
 *
 * Security overview, security events list, failed logins,
 * blocked IPs manager, active sessions, session termination.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  RefreshCw,
  ShieldAlert,
  Ban,
  Plus,
  Trash2,
  X,
  Monitor,
  Lock,
} from 'lucide-react';
import { adminApi } from '../../lib/api/admin';
import type {
  SecurityDashboard as SecurityDashboardData,
  SecurityEvent,
  SecurityEventListResponse,
  FailedLoginEntry,
  FailedLoginListResponse,
  BlockedIPEntry,
  ActiveSession,
  ActiveSessionListResponse,
} from '../../types/admin';

// =============================================================================
// Sub-views
// =============================================================================

type SecurityView = 'overview' | 'events' | 'failed-logins' | 'blocked-ips' | 'sessions';

// =============================================================================
// Block IP Modal
// =============================================================================

interface BlockIPModalProps {
  onClose: () => void;
  onSaved: () => void;
}

function BlockIPModal({ onClose, onSaved }: BlockIPModalProps) {
  const [ip, setIp] = useState('');
  const [reason, setReason] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await adminApi.security.blockIP({ ip_address: ip, reason });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to block IP');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Block IP Address</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">IP Address *</label>
            <input type="text" value={ip} onChange={(e) => setIp(e.target.value)} required placeholder="e.g. 192.168.1.100" className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Reason *</label>
            <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">{saving ? 'Blocking…' : 'Block'}</button>
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
 * SecurityDashboardTab provides a comprehensive security overview,
 * event browsing, failed login monitoring, IP blocking, and session management.
 */
export function SecurityDashboardTab() {
  const [view, setView] = useState<SecurityView>('overview');

  // Dashboard
  const [dashboard, setDashboard] = useState<SecurityDashboardData | null>(null);

  // Events
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [eventsTotal, setEventsTotal] = useState(0);
  const [eventsPage, setEventsPage] = useState(1);
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');
  const [isLoadingEvents, setIsLoadingEvents] = useState(false);

  // Failed logins
  const [failedLogins, setFailedLogins] = useState<FailedLoginEntry[]>([]);
  const [failedLoginsTotal, setFailedLoginsTotal] = useState(0);
  const [failedPage, setFailedPage] = useState(1);
  const [isLoadingFailed, setIsLoadingFailed] = useState(false);

  // Blocked IPs
  const [blockedIPs, setBlockedIPs] = useState<BlockedIPEntry[]>([]);
  const [isLoadingBlocked, setIsLoadingBlocked] = useState(false);
  const [showBlockModal, setShowBlockModal] = useState(false);

  // Sessions
  const [sessions, setSessions] = useState<ActiveSession[]>([]);
  const [sessionsTotal, setSessionsTotal] = useState(0);
  const [sessionsPage, setSessionsPage] = useState(1);
  const [isLoadingSessions, setIsLoadingSessions] = useState(false);
  const [terminateConfirm, setTerminateConfirm] = useState<string | null>(null);

  const [error, setError] = useState<string | null>(null);
  const pageSize = 20;

  // -------------------------------------------------------------------------
  // Fetch functions
  // -------------------------------------------------------------------------

  const fetchDashboard = useCallback(async () => {
    try {
      const data = await adminApi.security.getDashboard();
      setDashboard(data);
    } catch {
      // silent
    }
  }, []);

  const fetchEvents = useCallback(async () => {
    setIsLoadingEvents(true);
    setError(null);
    try {
      const data: SecurityEventListResponse = await adminApi.security.getEvents({
        page: eventsPage,
        page_size: pageSize,
        event_type: eventTypeFilter || undefined,
        severity: severityFilter || undefined,
      });
      setEvents(data.items);
      setEventsTotal(data.total);
    } catch (err) {
      setError('Failed to load security events');
      console.error(err);
    } finally {
      setIsLoadingEvents(false);
    }
  }, [eventsPage, eventTypeFilter, severityFilter]);

  const fetchFailedLogins = useCallback(async () => {
    setIsLoadingFailed(true);
    try {
      const data: FailedLoginListResponse = await adminApi.security.getFailedLogins({ page: failedPage, page_size: pageSize });
      setFailedLogins(data.items);
      setFailedLoginsTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingFailed(false);
    }
  }, [failedPage]);

  const fetchBlockedIPs = useCallback(async () => {
    setIsLoadingBlocked(true);
    try {
      const data = await adminApi.security.getBlockedIPs();
      setBlockedIPs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingBlocked(false);
    }
  }, []);

  const fetchSessions = useCallback(async () => {
    setIsLoadingSessions(true);
    try {
      const data: ActiveSessionListResponse = await adminApi.security.getSessions({ page: sessionsPage, page_size: pageSize });
      setSessions(data.items);
      setSessionsTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoadingSessions(false);
    }
  }, [sessionsPage]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  useEffect(() => {
    if (view === 'events') fetchEvents();
    if (view === 'failed-logins') fetchFailedLogins();
    if (view === 'blocked-ips') fetchBlockedIPs();
    if (view === 'sessions') fetchSessions();
  }, [view, fetchEvents, fetchFailedLogins, fetchBlockedIPs, fetchSessions]);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  const handleUnblockIP = async (ip: string) => {
    try {
      await adminApi.security.unblockIP(ip);
      fetchBlockedIPs();
    } catch (err) {
      console.error('Failed to unblock IP', err);
    }
  };

  const handleTerminateSession = async (sessionId: string) => {
    try {
      await adminApi.security.terminateSession(sessionId);
      setTerminateConfirm(null);
      fetchSessions();
    } catch (err) {
      console.error('Failed to terminate session', err);
    }
  };

  // -------------------------------------------------------------------------
  // Threat level badge
  // -------------------------------------------------------------------------

  const threatBadge = (level: string) => {
    const classes: Record<string, string> = {
      low: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
      high: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
      critical: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };
    return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${classes[level] ?? classes['low']}`}>{level}</span>;
  };

  // -------------------------------------------------------------------------
  // Render — Events
  // -------------------------------------------------------------------------

  if (view === 'events') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Security Events</h2>
          <div className="flex gap-2">
            <button onClick={() => setView('overview')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
            <button onClick={fetchEvents} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4">
          <select value={eventTypeFilter} onChange={(e) => { setEventTypeFilter(e.target.value); setEventsPage(1); }} className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
            <option value="">All Types</option>
            <option value="login_failure">Login Failure</option>
            <option value="privilege_escalation">Privilege Escalation</option>
            <option value="suspicious_activity">Suspicious Activity</option>
            <option value="account_lockout">Account Lockout</option>
          </select>
          <select value={severityFilter} onChange={(e) => { setSeverityFilter(e.target.value); setEventsPage(1); }} className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
            <option value="">All Severity</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </div>

        {isLoadingEvents ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : error ? (
          <div className="py-8 text-center text-red-500">{error}</div>
        ) : events.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500">No security events found.</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Severity</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">IP</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {events.map((evt) => (
                    <tr key={evt.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{evt.event_type}</td>
                      <td className="px-4 py-3">{threatBadge(evt.severity ?? 'low')}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{evt.user_email ?? evt.user_id ?? '—'}</td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-500 dark:text-gray-400">{evt.ip_address ?? '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{new Date(evt.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {eventsTotal > pageSize && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Showing {((eventsPage - 1) * pageSize) + 1}–{Math.min(eventsPage * pageSize, eventsTotal)} of {eventsTotal}</span>
                <div className="flex gap-2">
                  <button onClick={() => setEventsPage((p) => Math.max(1, p - 1))} disabled={eventsPage === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
                  <button onClick={() => setEventsPage((p) => p + 1)} disabled={eventsPage * pageSize >= eventsTotal} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Failed Logins
  // -------------------------------------------------------------------------

  if (view === 'failed-logins') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Failed Logins</h2>
          <div className="flex gap-2">
            <button onClick={() => setView('overview')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
            <button onClick={fetchFailedLogins} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
          </div>
        </div>

        {isLoadingFailed ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : failedLogins.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500">No failed logins.</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Email</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">IP Address</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {failedLogins.map((entry, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{entry.user_email ?? '—'}</td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-500 dark:text-gray-400">{entry.ip_address ?? '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{new Date(entry.timestamp).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {failedLoginsTotal > pageSize && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Showing {((failedPage - 1) * pageSize) + 1}–{Math.min(failedPage * pageSize, failedLoginsTotal)} of {failedLoginsTotal}</span>
                <div className="flex gap-2">
                  <button onClick={() => setFailedPage((p) => Math.max(1, p - 1))} disabled={failedPage === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
                  <button onClick={() => setFailedPage((p) => p + 1)} disabled={failedPage * pageSize >= failedLoginsTotal} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Blocked IPs
  // -------------------------------------------------------------------------

  if (view === 'blocked-ips') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Blocked IPs</h2>
          <div className="flex gap-2">
            <button onClick={() => setView('overview')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
            <button onClick={() => setShowBlockModal(true)} className="flex items-center gap-1 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"><Plus className="h-4 w-4" /> Block IP</button>
          </div>
        </div>

        {isLoadingBlocked ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : blockedIPs.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500">No blocked IPs.</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">IP Address</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Reason</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Blocked At</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Blocked By</th>
                  <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                {blockedIPs.map((entry) => (
                  <tr key={entry.ip_address} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-3 text-sm font-mono font-medium text-gray-900 dark:text-white">{entry.ip_address}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{entry.reason ?? '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{new Date(entry.blocked_at).toLocaleString()}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{entry.blocked_by ?? '—'}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-right">
                      <button onClick={() => handleUnblockIP(entry.ip_address)} title="Unblock" className="rounded p-1 text-gray-400 hover:bg-green-100 hover:text-green-600 dark:hover:bg-green-900/30">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showBlockModal && <BlockIPModal onClose={() => setShowBlockModal(false)} onSaved={() => { setShowBlockModal(false); fetchBlockedIPs(); }} />}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Active Sessions
  // -------------------------------------------------------------------------

  if (view === 'sessions') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Active Sessions</h2>
          <div className="flex gap-2">
            <button onClick={() => setView('overview')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back</button>
            <button onClick={fetchSessions} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
          </div>
        </div>

        {isLoadingSessions ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : sessions.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500">No active sessions.</div>
        ) : (
          <>
            <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">User</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">IP</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">User Agent</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Last Activity</th>
                    <th className="px-4 py-3 text-right text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                  {sessions.map((session) => (
                    <tr key={session.session_id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-3 text-sm text-gray-900 dark:text-white">{session.user_email ?? session.user_id ?? '—'}</td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-500 dark:text-gray-400">{session.ip_address ?? '—'}</td>
                      <td className="max-w-xs truncate px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{session.user_agent ?? '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{session.last_activity ? new Date(session.last_activity).toLocaleString() : '—'}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-right">
                        <button onClick={() => setTerminateConfirm(session.session_id)} title="Terminate" className="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30">
                          <Ban className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {sessionsTotal > pageSize && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">Showing {((sessionsPage - 1) * pageSize) + 1}–{Math.min(sessionsPage * pageSize, sessionsTotal)} of {sessionsTotal}</span>
                <div className="flex gap-2">
                  <button onClick={() => setSessionsPage((p) => Math.max(1, p - 1))} disabled={sessionsPage === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
                  <button onClick={() => setSessionsPage((p) => p + 1)} disabled={sessionsPage * pageSize >= sessionsTotal} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
                </div>
              </div>
            )}
          </>
        )}

        {/* Terminate confirmation */}
        {terminateConfirm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
            <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Terminate Session</h3>
              <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Force-terminate this session? The user will be logged out.</p>
              <div className="mt-4 flex justify-end gap-3">
                <button onClick={() => setTerminateConfirm(null)} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
                <button onClick={() => handleTerminateSession(terminateConfirm)} className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Terminate</button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Overview (default)
  // -------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Security Dashboard</h2>
        <button onClick={fetchDashboard} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
      </div>

      {/* Dashboard stats */}
      {!dashboard ? (
        <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard label="Threat Level" value={dashboard.threat_level} highlight />
            <StatCard label="Failed Logins (24h)" value={dashboard.failed_logins_24h} />
            <StatCard label="Blocked IPs" value={dashboard.blocked_ips_count} />
            <StatCard label="Active Sessions" value={dashboard.active_sessions} />
            <StatCard label="Events (24h)" value={dashboard.security_events_24h} />
          </div>

          {/* Navigation cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <NavCard icon={<ShieldAlert className="h-6 w-6 text-orange-500" />} title="Security Events" description="Browse all security events" onClick={() => setView('events')} />
            <NavCard icon={<Lock className="h-6 w-6 text-red-500" />} title="Failed Logins" description="Recent failed login attempts" onClick={() => setView('failed-logins')} />
            <NavCard icon={<Ban className="h-6 w-6 text-red-600" />} title="Blocked IPs" description="Manage blocked IP addresses" onClick={() => setView('blocked-ips')} />
            <NavCard icon={<Monitor className="h-6 w-6 text-blue-500" />} title="Active Sessions" description="View and terminate sessions" onClick={() => setView('sessions')} />
          </div>
        </>
      )}
    </div>
  );
}

// =============================================================================
// Helpers
// =============================================================================

function StatCard({ label, value, highlight }: { label: string; value: string | number; highlight?: boolean }) {
  return (
    <div className={`rounded-lg border p-4 ${highlight ? 'border-orange-300 bg-orange-50 dark:border-orange-700 dark:bg-orange-900/20' : 'bg-white dark:border-gray-700 dark:bg-gray-800'}`}>
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className={`mt-1 text-2xl font-bold ${highlight ? 'text-orange-700 dark:text-orange-400' : 'text-gray-900 dark:text-white'}`}>{value}</p>
    </div>
  );
}

function NavCard({ icon, title, description, onClick }: { icon: React.ReactNode; title: string; description: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex items-start gap-3 rounded-lg border bg-white p-4 text-left transition-colors hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:hover:bg-gray-700"
    >
      <div className="mt-0.5">{icon}</div>
      <div>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
        <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{description}</p>
      </div>
    </button>
  );
}
