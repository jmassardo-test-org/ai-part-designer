/**
 * Admin Dashboard Page.
 * 
 * Provides admin tools for:
 * - Content moderation queue
 * - User management (warnings/bans)
 * - System metrics
 * - Backup status
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  Users,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle,
  Search,
  RefreshCw,
  Eye,
  Database,
  HardDrive,
  Activity,
  BarChart3,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface ModerationItem {
  id: string;
  design_id: string | null;
  user_id: string;
  user_email: string | null;
  content_type: string;
  content_text: string | null;
  decision: string;
  reason: string | null;
  confidence_score: number | null;
  details: Record<string, unknown>;
  is_appealed: boolean;
  created_at: string;
}

interface ModerationStats {
  pending_count: number;
  escalated_count: number;
  approved_today: number;
  rejected_today: number;
  appeals_pending: number;
  avg_review_time_hours: number | null;
}

// =============================================================================
// Admin Dashboard Component
// =============================================================================

export function AdminDashboard() {
  const { token: _token } = useAuth();
  const [activeTab, setActiveTab] = useState<'moderation' | 'users' | 'system'>('moderation');

  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-sm text-gray-500">Manage content, users, and system</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4">
          <TabButton
            active={activeTab === 'moderation'}
            onClick={() => setActiveTab('moderation')}
            icon={<AlertTriangle className="w-4 h-4" />}
            label="Moderation"
          />
          <TabButton
            active={activeTab === 'users'}
            onClick={() => setActiveTab('users')}
            icon={<Users className="w-4 h-4" />}
            label="Users"
          />
          <TabButton
            active={activeTab === 'system'}
            onClick={() => setActiveTab('system')}
            icon={<Activity className="w-4 h-4" />}
            label="System"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === 'moderation' && <ModerationTab />}
        {activeTab === 'users' && <UsersTab />}
        {activeTab === 'system' && <SystemTab />}
      </div>
    </div>
  );
}

// =============================================================================
// Tab Button Component
// =============================================================================

interface TabButtonProps {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}

function TabButton({ active, onClick, icon, label }: TabButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
        active
          ? 'bg-blue-100 text-blue-700'
          : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// =============================================================================
// Moderation Tab
// =============================================================================

function ModerationTab() {
  const { token } = useAuth();
  const [items, setItems] = useState<ModerationItem[]>([]);
  const [stats, setStats] = useState<ModerationStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedItem, setSelectedItem] = useState<ModerationItem | null>(null);
  const [filter, setFilter] = useState<string>('pending_review');

  const fetchData = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);

    try {
      // Fetch queue
      const queueRes = await fetch(
        `${API_BASE}/admin/moderation/queue?status_filter=${filter}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (queueRes.ok) {
        const data = await queueRes.json();
        setItems(data.items);
      }

      // Fetch stats
      const statsRes = await fetch(`${API_BASE}/admin/moderation/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (error) {
      console.error('Failed to fetch moderation data:', error);
    } finally {
      setIsLoading(false);
    }
  }, [token, filter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleApprove = async (itemId: string) => {
    if (!token) return;
    try {
      await fetch(`${API_BASE}/admin/moderation/${itemId}/approve`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });
      fetchData();
      setSelectedItem(null);
    } catch (error) {
      console.error('Failed to approve:', error);
    }
  };

  const handleReject = async (itemId: string, reason: string) => {
    if (!token) return;
    try {
      await fetch(`${API_BASE}/admin/moderation/${itemId}/reject`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ reason, warn_user: true }),
      });
      fetchData();
      setSelectedItem(null);
    } catch (error) {
      console.error('Failed to reject:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Pending Review"
            value={stats.pending_count}
            icon={<Clock className="w-5 h-5" />}
            color="yellow"
          />
          <StatCard
            label="Escalated"
            value={stats.escalated_count}
            icon={<AlertTriangle className="w-5 h-5" />}
            color="red"
          />
          <StatCard
            label="Approved Today"
            value={stats.approved_today}
            icon={<CheckCircle className="w-5 h-5" />}
            color="green"
          />
          <StatCard
            label="Rejected Today"
            value={stats.rejected_today}
            icon={<XCircle className="w-5 h-5" />}
            color="gray"
          />
        </div>
      )}

      {/* Queue Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Moderation Queue</h2>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            <option value="pending_review">Pending Review</option>
            <option value="escalated">Escalated</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 text-gray-500 hover:text-gray-700 rounded-lg"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Queue List */}
      <div className="bg-white rounded-lg border divide-y">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading...
          </div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
            No items in queue
          </div>
        ) : (
          items.map((item) => (
            <ModerationRow
              key={item.id}
              item={item}
              onSelect={() => setSelectedItem(item)}
              onApprove={() => handleApprove(item.id)}
              onReject={() => handleReject(item.id, 'policy_violation')}
            />
          ))
        )}
      </div>

      {/* Detail Modal */}
      {selectedItem && (
        <ModerationDetailModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
          onApprove={() => handleApprove(selectedItem.id)}
          onReject={(reason) => handleReject(selectedItem.id, reason)}
        />
      )}
    </div>
  );
}

// =============================================================================
// Moderation Row Component
// =============================================================================

interface ModerationRowProps {
  item: ModerationItem;
  onSelect: () => void;
  onApprove: () => void;
  onReject: () => void;
}

function ModerationRow({ item, onSelect, onApprove, onReject }: ModerationRowProps) {
  const severityColors: Record<string, string> = {
    low: 'bg-yellow-100 text-yellow-700',
    medium: 'bg-orange-100 text-orange-700',
    high: 'bg-red-100 text-red-700',
    critical: 'bg-red-200 text-red-800',
  };

  const confidence = item.confidence_score ?? 0;
  const severity = confidence > 0.8 ? 'high' : confidence > 0.5 ? 'medium' : 'low';

  return (
    <div className="p-4 hover:bg-gray-50 flex items-center gap-4">
      {/* Severity indicator */}
      <div className={`px-2 py-1 rounded text-xs font-medium ${severityColors[severity]}`}>
        {Math.round(confidence * 100)}%
      </div>

      {/* Content info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900">{item.content_type}</span>
          {item.is_appealed && (
            <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
              Appealed
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 truncate">
          {item.user_email || item.user_id}
        </p>
        {item.content_text && (
          <p className="text-sm text-gray-600 truncate mt-1">
            "{item.content_text}"
          </p>
        )}
      </div>

      {/* Reason */}
      {item.reason && (
        <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
          {item.reason}
        </span>
      )}

      {/* Actions */}
      <div className="flex items-center gap-1">
        <button
          onClick={(e) => { e.stopPropagation(); onApprove(); }}
          className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
          title="Approve"
        >
          <CheckCircle className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onReject(); }}
          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
          title="Reject"
        >
          <XCircle className="w-4 h-4" />
        </button>
        <button
          onClick={onSelect}
          className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
          title="View Details"
        >
          <Eye className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// Moderation Detail Modal
// =============================================================================

interface ModerationDetailModalProps {
  item: ModerationItem;
  onClose: () => void;
  onApprove: () => void;
  onReject: (reason: string) => void;
}

function ModerationDetailModal({
  item,
  onClose,
  onApprove,
  onReject,
}: ModerationDetailModalProps) {
  const [rejectReason, setRejectReason] = useState('');

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-auto">
        <div className="p-6">
          <h3 className="text-lg font-semibold mb-4">Review Content</h3>

          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">Content Type</dt>
              <dd className="font-medium">{item.content_type}</dd>
            </div>
            <div>
              <dt className="text-gray-500">User</dt>
              <dd className="font-medium">{item.user_email || item.user_id}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Confidence</dt>
              <dd className="font-medium">{Math.round((item.confidence_score ?? 0) * 100)}%</dd>
            </div>
            <div>
              <dt className="text-gray-500">Created</dt>
              <dd className="font-medium">{new Date(item.created_at).toLocaleString()}</dd>
            </div>
          </dl>

          {item.content_text && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
              <p className="text-sm text-gray-600">{item.content_text}</p>
            </div>
          )}

          {Object.keys(item.details).length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Details</h4>
              <pre className="text-xs bg-gray-50 p-3 rounded-lg overflow-auto">
                {JSON.stringify(item.details, null, 2)}
              </pre>
            </div>
          )}

          {/* Reject reason input */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Rejection Reason (if rejecting)
            </label>
            <select
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            >
              <option value="">Select reason...</option>
              <option value="weapons">Weapons/Violence</option>
              <option value="adult">Adult Content</option>
              <option value="hate_speech">Hate Speech</option>
              <option value="ip_violation">IP Violation</option>
              <option value="other">Other</option>
            </select>
          </div>

          {/* Actions */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              onClick={() => onReject(rejectReason || 'policy_violation')}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
            >
              Reject
            </button>
            <button
              onClick={onApprove}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
            >
              Approve
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Users Tab
// =============================================================================

function UsersTab() {
  const { token: _token } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search users by email..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border rounded-lg"
          />
        </div>
      </div>

      <div className="bg-white rounded-lg border p-8 text-center text-gray-500">
        <Users className="w-12 h-12 mx-auto mb-4 text-gray-300" />
        <p>User management panel</p>
        <p className="text-sm">Search for users to view details, issue warnings, or manage bans</p>
      </div>
    </div>
  );
}

// =============================================================================
// System Tab
// =============================================================================

function SystemTab() {
  return (
    <div className="space-y-6">
      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard
          label="Total Users"
          value={0}
          icon={<Users className="w-5 h-5" />}
          color="blue"
        />
        <StatCard
          label="Active Today"
          value={0}
          icon={<Activity className="w-5 h-5" />}
          color="green"
        />
        <StatCard
          label="Queue Depth"
          value={0}
          icon={<BarChart3 className="w-5 h-5" />}
          color="yellow"
        />
        <StatCard
          label="Storage Used"
          value="0 GB"
          icon={<HardDrive className="w-5 h-5" />}
          color="purple"
        />
        <StatCard
          label="Total Designs"
          value={0}
          icon={<Database className="w-5 h-5" />}
          color="gray"
        />
        <StatCard
          label="Total Jobs"
          value={0}
          icon={<Activity className="w-5 h-5" />}
          color="blue"
        />
      </div>

      {/* Backup Status */}
      <div className="bg-white rounded-lg border p-6">
        <h3 className="text-lg font-semibold mb-4">Backup Status</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <div>
                <p className="font-medium text-green-900">Last Backup</p>
                <p className="text-sm text-green-700">Daily backup completed</p>
              </div>
            </div>
            <span className="text-sm text-green-600">Today, 2:00 AM</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium">Next Scheduled</p>
              <p className="text-sm text-gray-500">Daily database backup</p>
            </div>
            <span className="text-sm text-gray-600">Tomorrow, 2:00 AM</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Stat Card Component
// =============================================================================

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray';
}

function StatCard({ label, value, icon, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    yellow: 'bg-yellow-50 text-yellow-600',
    red: 'bg-red-50 text-red-600',
    purple: 'bg-purple-50 text-purple-600',
    gray: 'bg-gray-50 text-gray-600',
  };

  return (
    <div className="bg-white rounded-lg border p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>
          {icon}
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </div>
    </div>
  );
}

export default AdminDashboard;
