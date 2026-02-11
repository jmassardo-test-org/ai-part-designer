/**
 * Admin Dashboard Page.
 *
 * Comprehensive admin panel providing:
 * - Analytics dashboard with charts
 * - User management with CRUD operations
 * - Project and design management
 * - Template management
 * - Job monitoring and control
 * - Content moderation queue
 */

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
  HardDrive,
  Activity,
  BarChart3,
  FolderOpen,
  Layers,
  Layout,
  Briefcase,
  TrendingUp,
  Ban,
  UserX,
  X,
  UserCheck,
  Trash2,
  Copy,
  Star,
  StarOff,
  Power,
  PowerOff,
  Plus,
  Pencil,
  RotateCcw,
  XOctagon,
  MoreVertical,
  Globe,
  Lock,
  Undo,
  CreditCard,
  Building2,
  Component,
  Bell,
  FileText,
  Key,
  Server,
} from 'lucide-react';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { useAuth } from '@/contexts/AuthContext';
import type {
  AnalyticsOverview,
  AdminUser,
  AdminProject,
  AdminDesign,
  AdminTemplate,
  AdminJob,
  ModerationItem,
  ModerationStats,
  AdminJobStatus,
  AdminSubscription,
  AdminOrganization,
  AdminComponent,
  AdminNotification,
  AdminFile,
  StorageStats,
  AdminAuditLog,
  AdminAPIKey,
  SystemHealth,
  TimeSeriesAnalytics,
  RecipientType,
} from '@/types/admin';
import { adminApi } from '@/lib/api/admin';

// =============================================================================
// Valid tab types
// =============================================================================

type AdminTabType =
  | 'analytics'
  | 'users'
  | 'projects'
  | 'designs'
  | 'templates'
  | 'jobs'
  | 'moderation'
  | 'subscriptions'
  | 'organizations'
  | 'components'
  | 'notifications'
  | 'storage'
  | 'audit'
  | 'apikeys'
  | 'system';

const VALID_TABS: AdminTabType[] = [
  'analytics', 'users', 'projects', 'designs', 'templates', 'jobs',
  'moderation', 'subscriptions', 'organizations', 'components',
  'notifications', 'storage', 'audit', 'apikeys', 'system'
];

// =============================================================================
// Admin Dashboard Component
// =============================================================================

export function AdminDashboard() {
  const { token: _token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Get active tab from URL, default to 'analytics'
  const tabParam = searchParams.get('tab') || 'analytics';
  const activeTab: AdminTabType = VALID_TABS.includes(tabParam as AdminTabType) 
    ? (tabParam as AdminTabType) 
    : 'analytics';
  
  // Change tab by updating URL
  const setActiveTab = (tab: AdminTabType) => {
    setSearchParams({ tab });
  };

  return (
    <div className="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b dark:border-gray-700 px-6 py-4">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Admin Dashboard</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              System management and monitoring
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4 flex-wrap">
          <TabButton
            active={activeTab === 'analytics'}
            onClick={() => setActiveTab('analytics')}
            icon={<BarChart3 className="w-4 h-4" />}
            label="Analytics"
          />
          <TabButton
            active={activeTab === 'users'}
            onClick={() => setActiveTab('users')}
            icon={<Users className="w-4 h-4" />}
            label="Users"
          />
          <TabButton
            active={activeTab === 'projects'}
            onClick={() => setActiveTab('projects')}
            icon={<FolderOpen className="w-4 h-4" />}
            label="Projects"
          />
          <TabButton
            active={activeTab === 'designs'}
            onClick={() => setActiveTab('designs')}
            icon={<Layers className="w-4 h-4" />}
            label="Designs"
          />
          <TabButton
            active={activeTab === 'templates'}
            onClick={() => setActiveTab('templates')}
            icon={<Layout className="w-4 h-4" />}
            label="Templates"
          />
          <TabButton
            active={activeTab === 'jobs'}
            onClick={() => setActiveTab('jobs')}
            icon={<Briefcase className="w-4 h-4" />}
            label="Jobs"
          />
          <TabButton
            active={activeTab === 'moderation'}
            onClick={() => setActiveTab('moderation')}
            icon={<AlertTriangle className="w-4 h-4" />}
            label="Moderation"
          />
          <TabButton
            active={activeTab === 'subscriptions'}
            onClick={() => setActiveTab('subscriptions')}
            icon={<CreditCard className="w-4 h-4" />}
            label="Subscriptions"
          />
          <TabButton
            active={activeTab === 'organizations'}
            onClick={() => setActiveTab('organizations')}
            icon={<Building2 className="w-4 h-4" />}
            label="Organizations"
          />
          <TabButton
            active={activeTab === 'components'}
            onClick={() => setActiveTab('components')}
            icon={<Component className="w-4 h-4" />}
            label="Components"
          />
          <TabButton
            active={activeTab === 'notifications'}
            onClick={() => setActiveTab('notifications')}
            icon={<Bell className="w-4 h-4" />}
            label="Notifications"
          />
          <TabButton
            active={activeTab === 'storage'}
            onClick={() => setActiveTab('storage')}
            icon={<HardDrive className="w-4 h-4" />}
            label="Storage"
          />
          <TabButton
            active={activeTab === 'audit'}
            onClick={() => setActiveTab('audit')}
            icon={<FileText className="w-4 h-4" />}
            label="Audit Logs"
          />
          <TabButton
            active={activeTab === 'apikeys'}
            onClick={() => setActiveTab('apikeys')}
            icon={<Key className="w-4 h-4" />}
            label="API Keys"
          />
          <TabButton
            active={activeTab === 'system'}
            onClick={() => setActiveTab('system')}
            icon={<Server className="w-4 h-4" />}
            label="System"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {activeTab === 'analytics' && <AnalyticsTab />}
        {activeTab === 'users' && <UsersTab />}
        {activeTab === 'projects' && <ProjectsTab />}
        {activeTab === 'designs' && <DesignsTab />}
        {activeTab === 'templates' && <TemplatesTab />}
        {activeTab === 'jobs' && <JobsTab />}
        {activeTab === 'moderation' && <ModerationTab />}
        {activeTab === 'subscriptions' && <SubscriptionsTab />}
        {activeTab === 'organizations' && <OrganizationsTab />}
        {activeTab === 'components' && <ComponentsTab />}
        {activeTab === 'notifications' && <NotificationsTab />}
        {activeTab === 'storage' && <StorageTab />}
        {activeTab === 'audit' && <AuditTab />}
        {activeTab === 'apikeys' && <APIKeysTab />}
        {activeTab === 'system' && <SystemTab />}
      </div>
    </div>
  );
}

// =============================================================================
// Loading Fallback (exported for use in lazy-loaded admin routes)
// =============================================================================

export function AdminTabLoading() {
  return (
    <div className="flex items-center justify-center h-64">
      <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
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
          ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
          : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

// =============================================================================
// Analytics Tab
// =============================================================================

function AnalyticsTab() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [timeSeriesData, setTimeSeriesData] = useState<TimeSeriesAnalytics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<number>(30);
  const [_searchParams, setSearchParams] = useSearchParams();

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [overviewData, timeSeriesResult] = await Promise.all([
        adminApi.analytics.getOverview(),
        adminApi.analytics.getTimeSeriesAnalytics(dateRange),
      ]);
      setOverview(overviewData);
      setTimeSeriesData(timeSeriesResult);
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setIsLoading(false);
    }
  }, [dateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const storagePercentage = overview
    ? Math.round((overview.storage_used_bytes / overview.storage_limit_bytes) * 100)
    : 0;

  const handleStatClick = (tab: string) => {
    setSearchParams({ tab });
  };

  const exportToCSV = () => {
    if (!timeSeriesData) return;
    
    const headers = ['Date', 'New Users', 'Active Users', 'New Projects', 'New Designs', 'Jobs Completed'];
    const rows = timeSeriesData.new_users.map((_, i) => [
      timeSeriesData.new_users[i].date,
      timeSeriesData.new_users[i].value,
      timeSeriesData.active_users[i].value,
      timeSeriesData.new_projects[i].value,
      timeSeriesData.new_designs[i].value,
      timeSeriesData.jobs_completed[i].value,
    ]);
    
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
        <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-400">{error}</p>
        <button
          onClick={fetchData}
          className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200"
        >
          Retry
        </button>
      </div>
    );
  }

  // Prepare chart data
  const chartData = timeSeriesData?.new_users.map((_, i) => ({
    date: timeSeriesData.new_users[i].date.slice(5), // MM-DD format
    'New Users': timeSeriesData.new_users[i].value,
    'Active Users': timeSeriesData.active_users[i].value,
    'New Designs': timeSeriesData.new_designs[i].value,
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header with date filter, refresh, and export */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <label className="text-sm text-gray-600 dark:text-gray-400">Date Range:</label>
          <select
            value={dateRange}
            onChange={(e) => setDateRange(Number(e.target.value))}
            className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
          >
            <option value={7}>Last 7 Days</option>
            <option value={14}>Last 14 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
            <option value={365}>Last Year</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={exportToCSV}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <FileText className="w-4 h-4" />
            Export CSV
          </button>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Clickable Overview Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <ClickableStatCard
          label="Total Users"
          value={overview?.total_users ?? 0}
          icon={<Users className="w-5 h-5" />}
          color="blue"
          onClick={() => handleStatClick('users')}
        />
        <StatCard
          label="Active Today"
          value={overview?.active_users_today ?? 0}
          icon={<Activity className="w-5 h-5" />}
          color="green"
        />
        <StatCard
          label="Active This Week"
          value={overview?.active_users_week ?? 0}
          icon={<TrendingUp className="w-5 h-5" />}
          color="purple"
        />
        <StatCard
          label="Active This Month"
          value={overview?.active_users_month ?? 0}
          icon={<BarChart3 className="w-5 h-5" />}
          color="yellow"
        />
      </div>

      {/* Content Stats - Clickable */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <ClickableStatCard
          label="Total Projects"
          value={overview?.total_projects ?? 0}
          icon={<FolderOpen className="w-5 h-5" />}
          color="blue"
          onClick={() => handleStatClick('projects')}
        />
        <ClickableStatCard
          label="Total Designs"
          value={overview?.total_designs ?? 0}
          icon={<Layers className="w-5 h-5" />}
          color="green"
          onClick={() => handleStatClick('designs')}
        />
        <ClickableStatCard
          label="Templates"
          value={overview?.total_templates ?? 0}
          icon={<Layout className="w-5 h-5" />}
          color="purple"
          onClick={() => handleStatClick('templates')}
        />
        <ClickableStatCard
          label="Total Jobs"
          value={overview?.total_jobs ?? 0}
          icon={<Briefcase className="w-5 h-5" />}
          color="gray"
          onClick={() => handleStatClick('jobs')}
        />
      </div>

      {/* Trends Chart */}
      {chartData.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold dark:text-gray-100 mb-4">Trends Over Time</h3>
          <div className="h-80">
            <AnalyticsChart data={chartData} />
          </div>
        </div>
      )}

      {/* Job Status */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold dark:text-gray-100 mb-4">Job Queue</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Pending Jobs</span>
              <span className="text-xl font-bold text-yellow-600">
                {overview?.pending_jobs ?? 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-600 dark:text-gray-400">Failed Jobs</span>
              <span className="text-xl font-bold text-red-600">{overview?.failed_jobs ?? 0}</span>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-6">
          <h3 className="text-lg font-semibold dark:text-gray-100 mb-4">Storage</h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Used</span>
              <span className="font-medium dark:text-gray-100">
                {formatBytes(overview?.storage_used_bytes ?? 0)}
              </span>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
              <div
                className={`h-3 rounded-full ${
                  storagePercentage > 90
                    ? 'bg-red-500'
                    : storagePercentage > 70
                    ? 'bg-yellow-500'
                    : 'bg-blue-500'
                }`}
                style={{ width: `${Math.min(storagePercentage, 100)}%` }}
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-600 dark:text-gray-400">Limit</span>
              <span className="font-medium dark:text-gray-100">
                {formatBytes(overview?.storage_limit_bytes ?? 0)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Clickable stat card that navigates to a specific tab.
 */
function ClickableStatCard({
  label,
  value,
  icon,
  color,
  onClick,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'purple' | 'yellow' | 'red' | 'gray';
  onClick: () => void;
}) {
  const colorClasses = {
    blue: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    green: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    purple: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    yellow: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
    red: 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
    gray: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  };

  return (
    <button
      onClick={onClick}
      className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4 hover:shadow-md hover:border-blue-300 dark:hover:border-blue-600 transition-all cursor-pointer text-left w-full"
    >
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>{icon}</div>
        <div>
          <p className="text-2xl font-bold dark:text-gray-100">{value.toLocaleString()}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        </div>
      </div>
    </button>
  );
}

/**
 * Analytics line chart component using Recharts.
 */
function AnalyticsChart({ data }: { data: Array<Record<string, string | number>> }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis 
          dataKey="date" 
          stroke="#9CA3AF"
          tick={{ fill: '#9CA3AF', fontSize: 12 }}
        />
        <YAxis 
          stroke="#9CA3AF"
          tick={{ fill: '#9CA3AF', fontSize: 12 }}
        />
        <Tooltip 
          contentStyle={{ 
            backgroundColor: '#1F2937', 
            border: '1px solid #374151',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#F9FAFB' }}
        />
        <Legend />
        <Line 
          type="monotone" 
          dataKey="New Users" 
          stroke="#3B82F6" 
          strokeWidth={2}
          dot={false}
        />
        <Line 
          type="monotone" 
          dataKey="Active Users" 
          stroke="#10B981" 
          strokeWidth={2}
          dot={false}
        />
        <Line 
          type="monotone" 
          dataKey="New Designs" 
          stroke="#8B5CF6" 
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

// =============================================================================
// Users Tab
// =============================================================================

function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [showActionMenu, setShowActionMenu] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const pageSize = 20;

  const fetchUsers = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await adminApi.users.listUsers({
        search: searchQuery || undefined,
        role: roleFilter || undefined,
        is_active: statusFilter === 'active' ? true : statusFilter === 'inactive' ? false : undefined,
        is_suspended: statusFilter === 'suspended' ? true : undefined,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      setUsers(response.users);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch users:', err);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, roleFilter, statusFilter, page, sortBy, sortOrder]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Toggle sort order or change sort column
  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  // Sortable column header component
  const SortableHeader = ({ column, label }: { column: string; label: string }) => (
    <th 
      onClick={() => handleSort(column)}
      className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 select-none"
    >
      <div className="flex items-center gap-1">
        {label}
        {sortBy === column && (
          <span className="text-blue-500">{sortOrder === 'asc' ? '↑' : '↓'}</span>
        )}
      </div>
    </th>
  );

  const handleSuspend = async (userId: string) => {
    const reason = prompt('Enter suspension reason:');
    if (!reason) return;

    try {
      await adminApi.users.suspendUser(userId, reason);
      fetchUsers();
    } catch (err) {
      console.error('Failed to suspend user:', err);
    }
    setShowActionMenu(null);
  };

  const handleUnsuspend = async (userId: string) => {
    try {
      await adminApi.users.unsuspendUser(userId);
      fetchUsers();
    } catch (err) {
      console.error('Failed to unsuspend user:', err);
    }
    setShowActionMenu(null);
  };

  const handleDelete = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return;
    }
    try {
      await adminApi.users.deleteUser(userId);
      fetchUsers();
    } catch (err) {
      console.error('Failed to delete user:', err);
    }
    setShowActionMenu(null);
  };

  const handleWarn = async (userId: string) => {
    const reason = prompt('Enter warning reason:');
    if (!reason) return;

    try {
      await adminApi.users.warnUser(userId, reason, 'medium');
      fetchUsers();
    } catch (err) {
      console.error('Failed to warn user:', err);
    }
    setShowActionMenu(null);
  };

  const handleChangeRole = async (userId: string, newRole: 'user' | 'admin' | 'super_admin', currentRole: string) => {
    const roleNames: Record<string, string> = {
      user: 'User',
      admin: 'Organization Admin',
      super_admin: 'Platform Admin',
    };
    
    const confirmMessage = `Are you sure you want to change this user's role from ${roleNames[currentRole]} to ${roleNames[newRole]}?`;
    if (!confirm(confirmMessage)) return;

    try {
      await adminApi.users.updateUser(userId, { role: newRole });
      fetchUsers();
    } catch (err) {
      console.error('Failed to change user role:', err);
      alert('Failed to change role. Please try again.');
    }
    setShowActionMenu(null);
  };

  const handleResetPassword = async (userId: string, userEmail: string) => {
    if (!confirm(`Send password reset email to ${userEmail}?`)) return;

    try {
      await adminApi.users.resetPassword(userId);
      alert(`Password reset email sent to ${userEmail}`);
    } catch (err) {
      console.error('Failed to reset password:', err);
      alert('Failed to send password reset email. Please try again.');
    }
    setShowActionMenu(null);
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search by email or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Roles</option>
          <option value="user">User</option>
          <option value="admin">Org Admin</option>
          <option value="super_admin">Platform Admin</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
        </select>
        <button
          onClick={fetchUsers}
          disabled={isLoading}
          className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Users Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden overflow-x-auto">
        <table className="w-full min-w-[900px]">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableHeader column="email" label="User" />
              <SortableHeader column="role" label="Role" />
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Status
              </th>
              <SortableHeader column="subscription_tier" label="Plan" />
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Projects
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Storage
              </th>
              <SortableHeader column="last_login_at" label="Last Login" />
              <SortableHeader column="created_at" label="Joined" />
              <th className="text-right px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y dark:divide-gray-700">
            {isLoading ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-gray-400" />
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                  No users found
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium dark:text-gray-100">{user.email}</p>
                      {user.full_name && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">{user.full_name}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <RoleBadge role={user.role} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge
                      isActive={user.is_active}
                      isSuspended={user.is_suspended}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <PlanBadge tier={user.subscription_tier} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {user.project_count}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {formatBytes(user.storage_used_bytes)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {user.last_login_at 
                      ? new Date(user.last_login_at).toLocaleDateString()
                      : <span className="text-gray-400">Never</span>
                    }
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(user.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right relative">
                    <button
                      onClick={() => setShowActionMenu(showActionMenu === user.id ? null : user.id)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                    >
                      <MoreVertical className="w-4 h-4 text-gray-500" />
                    </button>
                    {showActionMenu === user.id && (
                      <ActionMenu
                        onClose={() => setShowActionMenu(null)}
                        actions={[
                          {
                            icon: <Eye className="w-4 h-4" />,
                            label: 'View Details',
                            onClick: () => setSelectedUser(user),
                          },
                          // Role change actions - show options for roles different from current
                          ...(user.role !== 'super_admin' ? [{
                            icon: <Shield className="w-4 h-4" />,
                            label: 'Promote to Platform Admin',
                            onClick: () => handleChangeRole(user.id, 'super_admin', user.role),
                          }] : []),
                          ...(user.role !== 'admin' ? [{
                            icon: <Users className="w-4 h-4" />,
                            label: user.role === 'super_admin' ? 'Demote to Org Admin' : 'Promote to Org Admin',
                            onClick: () => handleChangeRole(user.id, 'admin', user.role),
                          }] : []),
                          ...(user.role !== 'user' ? [{
                            icon: <UserCheck className="w-4 h-4" />,
                            label: 'Demote to User',
                            onClick: () => handleChangeRole(user.id, 'user', user.role),
                          }] : []),
                          {
                            icon: <Key className="w-4 h-4" />,
                            label: 'Reset Password',
                            onClick: () => handleResetPassword(user.id, user.email),
                          },
                          {
                            icon: <AlertTriangle className="w-4 h-4" />,
                            label: 'Warn User',
                            onClick: () => handleWarn(user.id),
                          },
                          user.is_suspended
                            ? {
                                icon: <UserCheck className="w-4 h-4" />,
                                label: 'Unsuspend',
                                onClick: () => handleUnsuspend(user.id),
                              }
                            : {
                                icon: <UserX className="w-4 h-4" />,
                                label: 'Suspend',
                                onClick: () => handleSuspend(user.id),
                                danger: true,
                              },
                          {
                            icon: <Trash2 className="w-4 h-4" />,
                            label: 'Delete',
                            onClick: () => handleDelete(user.id),
                            danger: true,
                          },
                        ]}
                      />
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
      />

      {/* User Details Modal */}
      {selectedUser && (
        <UserDetailsModal user={selectedUser} onClose={() => setSelectedUser(null)} />
      )}
    </div>
  );
}

// =============================================================================
// Projects Tab
// =============================================================================

function ProjectsTab() {
  const [projects, setProjects] = useState<AdminProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [visibilityFilter, setVisibilityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<string>('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [showActionMenu, setShowActionMenu] = useState<string | null>(null);
  const pageSize = 20;

  const fetchProjects = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await adminApi.projects.listProjects({
        search: searchQuery || undefined,
        is_public: visibilityFilter === 'public' ? true : visibilityFilter === 'private' ? false : undefined,
        page,
        page_size: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      });
      setProjects(response.projects);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, visibilityFilter, page, sortBy, sortOrder]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const SortableHeader = ({ column, label }: { column: string; label: string }) => (
    <th 
      onClick={() => handleSort(column)}
      className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 select-none"
    >
      <div className="flex items-center gap-1">
        {label}
        {sortBy === column && (
          <span className="text-blue-500">{sortOrder === 'asc' ? '↑' : '↓'}</span>
        )}
      </div>
    </th>
  );

  const handleSuspend = async (projectId: string) => {
    const reason = prompt('Enter suspension reason:');
    if (!reason) return;
    try {
      await adminApi.projects.suspendProject(projectId, reason);
      fetchProjects();
    } catch (err) {
      console.error('Failed to suspend project:', err);
      alert('Failed to suspend project');
    }
    setShowActionMenu(null);
  };

  const handleUnsuspend = async (projectId: string) => {
    try {
      await adminApi.projects.unsuspendProject(projectId);
      fetchProjects();
    } catch (err) {
      console.error('Failed to unsuspend project:', err);
      alert('Failed to unsuspend project');
    }
    setShowActionMenu(null);
  };

  const handleDelete = async (projectId: string) => {
    if (!confirm('Are you sure you want to delete this project? This action cannot be undone.')) {
      return;
    }
    try {
      await adminApi.projects.deleteProject(projectId);
      fetchProjects();
    } catch (err) {
      console.error('Failed to delete project:', err);
    }
    setShowActionMenu(null);
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
        <select
          value={visibilityFilter}
          onChange={(e) => setVisibilityFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Visibility</option>
          <option value="public">Public</option>
          <option value="private">Private</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
        </select>
        <button
          onClick={fetchProjects}
          disabled={isLoading}
          className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Projects Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden overflow-x-auto">
        <table className="w-full min-w-[900px]">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableHeader column="name" label="Project" />
              <SortableHeader column="owner_email" label="Owner" />
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Visibility
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Status
              </th>
              <SortableHeader column="design_count" label="Designs" />
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Storage
              </th>
              <SortableHeader column="created_at" label="Created" />
              <th className="text-right px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y dark:divide-gray-700">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-gray-400" />
                </td>
              </tr>
            ) : projects.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                  No projects found
                </td>
              </tr>
            ) : (
              projects.map((project) => (
                <tr key={project.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium dark:text-gray-100">{project.name}</p>
                      {project.description && (
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                          {project.description}
                        </p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {project.owner_email}
                  </td>
                  <td className="px-4 py-3">
                    {project.is_public ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs">
                        <Globe className="w-3 h-3" />
                        Public
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
                        <Lock className="w-3 h-3" />
                        Private
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {project.status === 'suspended' ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded text-xs">
                        <Ban className="w-3 h-3" />
                        Suspended
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs">
                        <CheckCircle className="w-3 h-3" />
                        Active
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {project.design_count}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {formatBytes(project.storage_used_bytes)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(project.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right relative">
                    <button
                      onClick={() => setShowActionMenu(showActionMenu === project.id ? null : project.id)}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                    >
                      <MoreVertical className="w-4 h-4 text-gray-500" />
                    </button>
                    {showActionMenu === project.id && (
                      <ActionMenu
                        onClose={() => setShowActionMenu(null)}
                        actions={[
                          {
                            icon: <Eye className="w-4 h-4" />,
                            label: 'View Details',
                            onClick: () => {
                              // TODO: Open project details modal
                              setShowActionMenu(null);
                            },
                          },
                          project.status === 'suspended'
                            ? {
                                icon: <Power className="w-4 h-4" />,
                                label: 'Unsuspend',
                                onClick: () => handleUnsuspend(project.id),
                              }
                            : {
                                icon: <PowerOff className="w-4 h-4" />,
                                label: 'Suspend',
                                onClick: () => handleSuspend(project.id),
                                danger: true,
                              },
                          {
                            icon: <Trash2 className="w-4 h-4" />,
                            label: 'Delete',
                            onClick: () => handleDelete(project.id),
                            danger: true,
                          },
                        ]}
                      />
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
      />
    </div>
  );
}

// =============================================================================
// Designs Tab
// =============================================================================

function DesignsTab() {
  const [designs, setDesigns] = useState<AdminDesign[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [visibilityFilter, setVisibilityFilter] = useState<string>('');
  const [sourceTypeFilter, setSourceTypeFilter] = useState<string>('');
  const [showDeleted, setShowDeleted] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [sortField, setSortField] = useState<string>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [previewDesign, setPreviewDesign] = useState<AdminDesign | null>(null);
  const pageSize = 20;

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const fetchDesigns = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await adminApi.designs.listDesigns({
        search: searchQuery || undefined,
        is_public: visibilityFilter === 'public' ? true : visibilityFilter === 'private' ? false : undefined,
        is_deleted: showDeleted ? true : undefined,
        page,
        page_size: pageSize,
      });
      setDesigns(response.designs);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch designs:', err);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, visibilityFilter, showDeleted, page]);

  useEffect(() => {
    fetchDesigns();
  }, [fetchDesigns]);

  const handleDelete = async (designId: string) => {
    if (!confirm('Are you sure you want to delete this design?')) {
      return;
    }
    try {
      await adminApi.designs.deleteDesign(designId);
      fetchDesigns();
    } catch (err) {
      console.error('Failed to delete design:', err);
    }
  };

  const handleRestore = async (designId: string) => {
    try {
      await adminApi.designs.restoreDesign(designId);
      fetchDesigns();
    } catch (err) {
      console.error('Failed to restore design:', err);
    }
  };

  const handleToggleVisibility = async (designId: string, currentVisibility: boolean) => {
    try {
      await adminApi.designs.setVisibility(designId, !currentVisibility);
      fetchDesigns();
    } catch (err) {
      console.error('Failed to update visibility:', err);
    }
  };

  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Sortable column header component for DesignsTab
  const SortableHeader = ({ 
    field, 
    label, 
    currentField, 
    direction, 
    onSort 
  }: { 
    field: string; 
    label: string; 
    currentField: string; 
    direction: 'asc' | 'desc'; 
    onSort: (field: string) => void; 
  }) => (
    <th 
      onClick={() => onSort(field)}
      className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600 select-none"
    >
      <div className="flex items-center gap-1">
        {label}
        {currentField === field && (
          <span className="text-blue-500">{direction === 'asc' ? '↑' : '↓'}</span>
        )}
      </div>
    </th>
  );

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search designs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
        <select
          value={visibilityFilter}
          onChange={(e) => setVisibilityFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Visibility</option>
          <option value="public">Public</option>
          <option value="private">Private</option>
        </select>
        <select
          value={sourceTypeFilter}
          onChange={(e) => setSourceTypeFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Sources</option>
          <option value="ai_generated">AI Generated</option>
          <option value="template">From Template</option>
          <option value="uploaded">Uploaded</option>
          <option value="manual">Manual</option>
        </select>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showDeleted}
            onChange={(e) => setShowDeleted(e.target.checked)}
            className="rounded border-gray-300 dark:border-gray-600"
          />
          <span className="text-sm text-gray-600 dark:text-gray-400">Show Deleted</span>
        </label>
        <button
          onClick={fetchDesigns}
          disabled={isLoading}
          className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Designs Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <SortableHeader
                field="name"
                label="Design"
                currentField={sortField}
                direction={sortDirection}
                onSort={handleSort}
              />
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Owner
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Project
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Source
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Visibility
              </th>
              <SortableHeader
                field="file_size_bytes"
                label="Size"
                currentField={sortField}
                direction={sortDirection}
                onSort={handleSort}
              />
              <SortableHeader
                field="created_at"
                label="Created"
                currentField={sortField}
                direction={sortDirection}
                onSort={handleSort}
              />
              <th className="text-right px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y dark:divide-gray-700">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-gray-400" />
                </td>
              </tr>
            ) : designs.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                  No designs found
                </td>
              </tr>
            ) : (
              designs.map((design) => (
                <tr
                  key={design.id}
                  className={`hover:bg-gray-50 dark:hover:bg-gray-700/50 ${
                    design.is_deleted ? 'opacity-60' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {design.is_deleted && (
                        <Trash2 className="w-4 h-4 text-red-500" />
                      )}
                      <button
                        onClick={() => setPreviewDesign(design)}
                        className="text-left hover:text-blue-600 dark:hover:text-blue-400"
                        title="Preview Design"
                      >
                        <p className="font-medium dark:text-gray-100">{design.name}</p>
                        {design.file_format && (
                          <p className="text-xs text-gray-500 dark:text-gray-400">
                            {design.file_format.toUpperCase()}
                          </p>
                        )}
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {design.owner_email}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {design.project_name || '-'}
                  </td>
                  <td className="px-4 py-3">
                    <SourceTypeBadge sourceType={design.source_type} />
                  </td>
                  <td className="px-4 py-3">
                    {design.is_public ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs">
                        <Globe className="w-3 h-3" />
                        Public
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
                        <Lock className="w-3 h-3" />
                        Private
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {formatBytes(design.file_size_bytes)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(design.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => setPreviewDesign(design)}
                        className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                        title="Preview Design"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleToggleVisibility(design.id, design.is_public)}
                        className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                        title={design.is_public ? 'Make Private' : 'Make Public'}
                      >
                        {design.is_public ? (
                          <Lock className="w-4 h-4" />
                        ) : (
                          <Globe className="w-4 h-4" />
                        )}
                      </button>
                      {design.is_deleted ? (
                        <button
                          onClick={() => handleRestore(design.id)}
                          className="p-2 text-green-500 hover:bg-green-50 dark:hover:bg-green-900/30 rounded-lg"
                          title="Restore Design"
                        >
                          <Undo className="w-4 h-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleDelete(design.id)}
                          className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
                          title="Delete Design"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
      />

      {/* Preview Modal */}
      {previewDesign && (
        <div
          className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewDesign(null)}
        >
          <div
            className="bg-white dark:bg-gray-800 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
              <h3 className="text-lg font-semibold dark:text-gray-100">
                Design Details
              </h3>
              <button
                onClick={() => setPreviewDesign(null)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Name</p>
                  <p className="font-medium dark:text-gray-100">{previewDesign.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">ID</p>
                  <p className="font-mono text-sm dark:text-gray-300">{previewDesign.id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Owner</p>
                  <p className="dark:text-gray-100">{previewDesign.owner_email}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Project</p>
                  <p className="dark:text-gray-100">{previewDesign.project_name || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Source Type</p>
                  <SourceTypeBadge sourceType={previewDesign.source_type} />
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Visibility</p>
                  <p className="dark:text-gray-100">{previewDesign.is_public ? 'Public' : 'Private'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">File Format</p>
                  <p className="dark:text-gray-100">{previewDesign.file_format?.toUpperCase() || '-'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">File Size</p>
                  <p className="dark:text-gray-100">{formatBytes(previewDesign.file_size_bytes)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Created</p>
                  <p className="dark:text-gray-100">{new Date(previewDesign.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Updated</p>
                  <p className="dark:text-gray-100">{previewDesign.updated_at ? new Date(previewDesign.updated_at).toLocaleString() : '-'}</p>
                </div>
              </div>
              {previewDesign.description && (
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Description</p>
                  <p className="dark:text-gray-100">{previewDesign.description}</p>
                </div>
              )}
              {previewDesign.is_deleted && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <p className="text-sm text-red-600 dark:text-red-400">
                    This design has been deleted.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Badge component for design source type.
 */
function SourceTypeBadge({ sourceType }: { sourceType: string }) {
  const config: Record<string, { label: string; className: string }> = {
    ai_generated: {
      label: 'AI Generated',
      className: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
    },
    template: {
      label: 'Template',
      className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    },
    uploaded: {
      label: 'Uploaded',
      className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    },
    manual: {
      label: 'Manual',
      className: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-400',
    },
  };

  const { label, className } = config[sourceType] || config.manual;

  return (
    <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}

// =============================================================================
// Templates Tab
// =============================================================================

function TemplatesTab() {
  const [templates, setTemplates] = useState<AdminTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<AdminTemplate | null>(null);
  const pageSize = 20;

  const fetchTemplates = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await adminApi.templates.listTemplates({
        search: searchQuery || undefined,
        category: categoryFilter || undefined,
        is_enabled: statusFilter === 'enabled' ? true : statusFilter === 'disabled' ? false : undefined,
        is_featured: statusFilter === 'featured' ? true : undefined,
        page,
        page_size: pageSize,
      });
      setTemplates(response.templates);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch templates:', err);
    } finally {
      setIsLoading(false);
    }
  }, [searchQuery, categoryFilter, statusFilter, page]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleToggleEnabled = async (templateId: string, isEnabled: boolean) => {
    try {
      if (isEnabled) {
        await adminApi.templates.disableTemplate(templateId);
      } else {
        await adminApi.templates.enableTemplate(templateId);
      }
      fetchTemplates();
    } catch (err) {
      console.error('Failed to toggle template status:', err);
    }
  };

  const handleToggleFeatured = async (templateId: string, isFeatured: boolean) => {
    try {
      if (isFeatured) {
        await adminApi.templates.unfeatureTemplate(templateId);
      } else {
        await adminApi.templates.featureTemplate(templateId);
      }
      fetchTemplates();
    } catch (err) {
      console.error('Failed to toggle featured status:', err);
    }
  };

  const handleClone = async (templateId: string, name: string) => {
    const newName = prompt('Enter name for cloned template:', `${name} (Copy)`);
    if (!newName) return;
    try {
      await adminApi.templates.cloneTemplate(templateId, newName);
      fetchTemplates();
    } catch (err) {
      console.error('Failed to clone template:', err);
    }
  };

  const handleDelete = async (templateId: string) => {
    if (!confirm('Are you sure you want to delete this template?')) {
      return;
    }
    try {
      await adminApi.templates.deleteTemplate(templateId);
      fetchTemplates();
    } catch (err) {
      console.error('Failed to delete template:', err);
    }
  };

  const handleCreateTemplate = async (data: TemplateFormData) => {
    try {
      // Generate a slug from the name
      const slug = data.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
      
      await adminApi.templates.createTemplate({
        name: data.name,
        slug: slug,
        description: data.description,
        category: data.category,
        min_tier: data.min_tier,
        is_active: data.is_active,
        is_featured: data.is_featured,
        parameters: data.parameterSchema || {},
        default_values: {},
        cadquery_script: '# Empty template\nimport cadquery as cq\nresult = cq.Workplane("XY").box(10, 10, 10)',
      });
      setShowCreateModal(false);
      fetchTemplates();
    } catch (err) {
      console.error('Failed to create template:', err);
      throw err;
    }
  };

  const handleUpdateTemplate = async (data: TemplateFormData) => {
    if (!editingTemplate) return;
    try {
      await adminApi.templates.updateTemplate(editingTemplate.id, {
        name: data.name,
        description: data.description,
        category: data.category,
        min_tier: data.min_tier,
        is_active: data.is_active,
        is_featured: data.is_featured,
      });
      setEditingTemplate(null);
      fetchTemplates();
    } catch (err) {
      console.error('Failed to update template:', err);
      throw err;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with Create Button */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Categories</option>
          <option value="enclosure">Enclosure</option>
          <option value="bracket">Bracket</option>
          <option value="housing">Housing</option>
          <option value="custom">Custom</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Status</option>
          <option value="enabled">Enabled</option>
          <option value="disabled">Disabled</option>
          <option value="featured">Featured</option>
        </select>
        <button
          onClick={fetchTemplates}
          disabled={isLoading}
          className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium"
        >
          <Plus className="w-4 h-4" />
          Create Template
        </button>
      </div>

      {/* Templates Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Template
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Category
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Tier
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Creator
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Status
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Uses
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Created
              </th>
              <th className="text-right px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y dark:divide-gray-700">
            {isLoading ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-gray-400" />
                </td>
              </tr>
            ) : templates.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                  No templates found
                </td>
              </tr>
            ) : (
              templates.map((template) => (
                <tr key={template.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {template.is_featured && <Star className="w-4 h-4 text-yellow-500" />}
                      <div>
                        <p className="font-medium dark:text-gray-100">{template.name}</p>
                        {template.description && (
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                            {template.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 rounded text-xs capitalize">
                      {template.category}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <TierBadge tier={template.min_tier || 'free'} />
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {template.creator_email || 'System'}
                  </td>
                  <td className="px-4 py-3">
                    {template.is_active ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs">
                        <Power className="w-3 h-3" />
                        Enabled
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
                        <PowerOff className="w-3 h-3" />
                        Disabled
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                    {template.use_count}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(template.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleToggleFeatured(template.id, template.is_featured)}
                        className={`p-2 rounded-lg ${
                          template.is_featured
                            ? 'text-yellow-500 hover:bg-yellow-50 dark:hover:bg-yellow-900/30'
                            : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600'
                        }`}
                        title={template.is_featured ? 'Unfeature' : 'Feature'}
                      >
                        {template.is_featured ? (
                          <Star className="w-4 h-4 fill-current" />
                        ) : (
                          <StarOff className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => handleToggleEnabled(template.id, template.is_active)}
                        className={`p-2 rounded-lg ${
                          template.is_active
                            ? 'text-green-500 hover:bg-green-50 dark:hover:bg-green-900/30'
                            : 'text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600'
                        }`}
                        title={template.is_active ? 'Disable' : 'Enable'}
                      >
                        {template.is_active ? (
                          <Power className="w-4 h-4" />
                        ) : (
                          <PowerOff className="w-4 h-4" />
                        )}
                      </button>
                      <button
                        onClick={() => setEditingTemplate(template)}
                        className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                        title="Edit Template"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleClone(template.id, template.name)}
                        className="p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                        title="Clone Template"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(template.id)}
                        className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
                        title="Delete Template"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
      />

      {/* Create/Edit Modal */}
      {(showCreateModal || editingTemplate) && (
        <TemplateFormModal
          template={editingTemplate}
          onClose={() => {
            setShowCreateModal(false);
            setEditingTemplate(null);
          }}
          onSubmit={editingTemplate ? handleUpdateTemplate : handleCreateTemplate}
        />
      )}
    </div>
  );
}

/**
 * Template form data interface.
 */
interface TemplateFormData {
  name: string;
  description: string;
  category: string;
  min_tier: string;
  is_active: boolean;
  is_featured: boolean;
  parameterSchema: Record<string, unknown>;
}

/**
 * Template Create/Edit Modal.
 */
function TemplateFormModal({
  template,
  onClose,
  onSubmit,
}: {
  template: AdminTemplate | null;
  onClose: () => void;
  onSubmit: (data: TemplateFormData) => Promise<void>;
}) {
  const [name, setName] = useState(template?.name || '');
  const [description, setDescription] = useState(template?.description || '');
  const [category, setCategory] = useState(template?.category || 'enclosure');
  const [tier, setTier] = useState(template?.min_tier || 'free');
  const [isActive, setIsActive] = useState(template?.is_active ?? true);
  const [isFeatured, setIsFeatured] = useState(template?.is_featured ?? false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        name,
        description,
        category,
        min_tier: tier,
        is_active: isActive,
        is_featured: isFeatured,
        parameterSchema: template?.parameter_schema || {},
      });
    } catch {
      setError('Failed to save template');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white dark:bg-gray-800 rounded-xl max-w-lg w-full max-h-[80vh] overflow-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <h3 className="text-lg font-semibold dark:text-gray-100">
            {template ? 'Edit Template' : 'Create Template'}
          </h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg text-sm">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Category *
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100"
              >
                <option value="enclosure">Enclosure</option>
                <option value="bracket">Bracket</option>
                <option value="housing">Housing</option>
                <option value="custom">Custom</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Tier *
              </label>
              <select
                value={tier}
                onChange={(e) => setTier(e.target.value as 'free' | 'starter' | 'professional' | 'enterprise')}
                className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 dark:text-gray-100"
              >
                <option value="free">Free</option>
                <option value="starter">Starter</option>
                <option value="professional">Professional</option>
                <option value="enterprise">Enterprise</option>
              </select>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Active</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isFeatured}
                onChange={(e) => setIsFeatured(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Featured</span>
            </label>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
            >
              {isSubmitting ? 'Saving...' : template ? 'Update Template' : 'Create Template'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/**
 * Badge component for template tier.
 */
function TierBadge({ tier }: { tier: string }) {
  const config: Record<string, { label: string; className: string }> = {
    free: {
      label: 'Free',
      className: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-400',
    },
    starter: {
      label: 'Starter',
      className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
    },
    professional: {
      label: 'Pro',
      className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    },
    enterprise: {
      label: 'Enterprise',
      className: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
    },
  };

  const { label, className } = config[tier] || config.free;

  return (
    <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}

// =============================================================================
// Jobs Tab
// =============================================================================

function JobsTab() {
  const [jobs, setJobs] = useState<AdminJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 20;

  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await adminApi.jobs.listJobs({
        status: (statusFilter as AdminJobStatus) || undefined,
        type: typeFilter as 'cad_generation' | 'export' | 'ai_processing' | 'file_conversion' || undefined,
        page,
        page_size: pageSize,
      });
      setJobs(response.jobs);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, typeFilter, page]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Auto-refresh for active jobs
  useEffect(() => {
    const hasActiveJobs = jobs.some(
      (job) => job.status === 'pending' || job.status === 'processing'
    );
    if (hasActiveJobs) {
      const interval = setInterval(fetchJobs, 5000);
      return () => clearInterval(interval);
    }
  }, [jobs, fetchJobs]);

  const handleCancel = async (jobId: string) => {
    if (!confirm('Are you sure you want to cancel this job?')) {
      return;
    }
    try {
      await adminApi.jobs.cancelJob(jobId);
      fetchJobs();
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
  };

  const handleRetry = async (jobId: string) => {
    try {
      await adminApi.jobs.retryJob(jobId);
      fetchJobs();
    } catch (err) {
      console.error('Failed to retry job:', err);
    }
  };

  const getStatusBadge = (status: AdminJobStatus) => {
    const styles: Record<AdminJobStatus, string> = {
      pending: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400',
      processing: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
      completed: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
      failed: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
      cancelled: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
    };
    const icons: Record<AdminJobStatus, React.ReactNode> = {
      pending: <Clock className="w-3 h-3" />,
      processing: <RefreshCw className="w-3 h-3 animate-spin" />,
      completed: <CheckCircle className="w-3 h-3" />,
      failed: <XCircle className="w-3 h-3" />,
      cancelled: <XOctagon className="w-3 h-3" />,
    };

    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs capitalize ${styles[status]}`}
      >
        {icons[status]}
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Types</option>
          <option value="cad_generation">CAD Generation</option>
          <option value="export">Export</option>
          <option value="ai_processing">AI Processing</option>
          <option value="file_conversion">File Conversion</option>
        </select>
        <button
          onClick={fetchJobs}
          disabled={isLoading}
          className="flex items-center gap-2 p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Jobs Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Job ID
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Type
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Status
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                User
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Progress
              </th>
              <th className="text-left px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Created
              </th>
              <th className="text-right px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-300">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y dark:divide-gray-700">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-gray-400" />
                </td>
              </tr>
            ) : jobs.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                  No jobs found
                </td>
              </tr>
            ) : (
              jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-4 py-3">
                    <code className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded font-mono">
                      {job.id.slice(0, 8)}...
                    </code>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-gray-600 dark:text-gray-400 capitalize">
                      {job.type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3">{getStatusBadge(job.status)}</td>
                  <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-400">
                    {job.user_email || job.user_id.slice(0, 8)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-20 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="h-2 rounded-full bg-blue-500"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{job.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(job.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {(job.status === 'pending' || job.status === 'processing') && (
                        <button
                          onClick={() => handleCancel(job.id)}
                          className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg"
                          title="Cancel Job"
                        >
                          <XOctagon className="w-4 h-4" />
                        </button>
                      )}
                      {job.status === 'failed' && (
                        <button
                          onClick={() => handleRetry(job.id)}
                          className="p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg"
                          title="Retry Job"
                        >
                          <RotateCcw className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <Pagination
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
      />
    </div>
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
      const [queueData, statsData] = await Promise.all([
        adminApi.moderation.getQueue(filter),
        adminApi.moderation.getStats(),
      ]);
      setItems(queueData.items);
      setStats(statsData);
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
    try {
      await adminApi.moderation.approveItem(itemId);
      fetchData();
      setSelectedItem(null);
    } catch (error) {
      console.error('Failed to approve:', error);
    }
  };

  const handleReject = async (itemId: string, reason: string) => {
    try {
      await adminApi.moderation.rejectItem(itemId, reason);
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
        <h2 className="text-lg font-semibold dark:text-gray-100">Moderation Queue</h2>
        <div className="flex items-center gap-2">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="px-3 py-2 border dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-800 dark:text-gray-100"
          >
            <option value="pending_review">Pending Review</option>
            <option value="escalated">Escalated</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>
          <button
            onClick={fetchData}
            disabled={isLoading}
            className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 rounded-lg"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Queue List */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 divide-y dark:divide-gray-700">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
            Loading...
          </div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-gray-400">
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
    <div className="p-4 hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-4">
      {/* Severity indicator */}
      <div className={`px-2 py-1 rounded text-xs font-medium ${severityColors[severity]}`}>
        {Math.round(confidence * 100)}%
      </div>

      {/* Content info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-gray-100">{item.content_type}</span>
          {item.is_appealed && (
            <span className="text-xs px-1.5 py-0.5 bg-purple-100 dark:bg-purple-900 text-purple-700 dark:text-purple-300 rounded">
              Appealed
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
          {item.user_email || item.user_id}
        </p>
        {item.content_text && (
          <p className="text-sm text-gray-600 dark:text-gray-400 truncate mt-1">
            &quot;{item.content_text}&quot;
          </p>
        )}
      </div>

      {/* Reason */}
      {item.reason && (
        <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded">
          {item.reason}
        </span>
      )}

      {/* Actions */}
      <div className="flex items-center gap-1">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onApprove();
          }}
          className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
          title="Approve"
        >
          <CheckCircle className="w-4 h-4" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onReject();
          }}
          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
          title="Reject"
        >
          <XCircle className="w-4 h-4" />
        </button>
        <button
          onClick={onSelect}
          className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
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
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-auto">
        <div className="p-6">
          <h3 className="text-lg font-semibold dark:text-gray-100 mb-4">Review Content</h3>

          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Content Type</dt>
              <dd className="font-medium dark:text-gray-100">{item.content_type}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">User</dt>
              <dd className="font-medium dark:text-gray-100">{item.user_email || item.user_id}</dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Confidence</dt>
              <dd className="font-medium dark:text-gray-100">
                {Math.round((item.confidence_score ?? 0) * 100)}%
              </dd>
            </div>
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Created</dt>
              <dd className="font-medium dark:text-gray-100">
                {new Date(item.created_at).toLocaleString()}
              </dd>
            </div>
          </dl>

          {item.content_text && (
            <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
              <p className="text-sm text-gray-600 dark:text-gray-300">{item.content_text}</p>
            </div>
          )}

          {Object.keys(item.details).length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Details</h4>
              <pre className="text-xs bg-gray-50 dark:bg-gray-700 dark:text-gray-300 p-3 rounded-lg overflow-auto">
                {JSON.stringify(item.details, null, 2)}
              </pre>
            </div>
          )}

          {/* Reject reason input */}
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Rejection Reason (if rejecting)
            </label>
            <select
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg text-sm bg-white dark:bg-gray-700 dark:text-gray-100"
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
              className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
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
// Shared Components
// =============================================================================

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'gray';
}

function StatCard({ label, value, icon, color }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    green: 'bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    yellow: 'bg-yellow-50 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
    red: 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400',
    purple: 'bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    gray: 'bg-gray-50 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>{icon}</div>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{value}</p>
          <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        </div>
      </div>
    </div>
  );
}

interface RoleBadgeProps {
  role: 'user' | 'admin' | 'super_admin';
}

function RoleBadge({ role }: RoleBadgeProps) {
  const styles: Record<string, string> = {
    user: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
    admin: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    super_admin: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
  };

  // Display names - rename Super Admin to Platform Admin
  const displayNames: Record<string, string> = {
    user: 'User',
    admin: 'Org Admin',
    super_admin: 'Platform Admin',
  };

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${styles[role]}`}>
      {displayNames[role] || role}
    </span>
  );
}

interface StatusBadgeProps {
  isActive: boolean;
  isSuspended: boolean;
}

function StatusBadge({ isActive, isSuspended }: StatusBadgeProps) {
  if (isSuspended) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded text-xs">
        <Ban className="w-3 h-3" />
        Suspended
      </span>
    );
  }
  if (!isActive) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded text-xs">
        <XCircle className="w-3 h-3" />
        Inactive
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded text-xs">
      <CheckCircle className="w-3 h-3" />
      Active
    </span>
  );
}

interface PlanBadgeProps {
  tier: string | null;
}

function PlanBadge({ tier }: PlanBadgeProps) {
  const styles: Record<string, string> = {
    free: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400',
    basic: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400',
    pro: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400',
    enterprise: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
  };

  const displayTier = tier || 'free';
  const style = styles[displayTier.toLowerCase()] || styles.free;

  return (
    <span className={`px-2 py-1 rounded text-xs font-medium capitalize ${style}`}>
      {displayTier}
    </span>
  );
}

interface ActionMenuProps {
  onClose: () => void;
  actions: Array<{
    icon: React.ReactNode;
    label: string;
    onClick: () => void;
    danger?: boolean;
  }>;
}

function ActionMenu({ onClose, actions }: ActionMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null);
  const [flipUp, setFlipUp] = useState(false);

  // Check if menu would go off-screen and flip direction
  useEffect(() => {
    if (menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      const viewportHeight = window.innerHeight;
      // If bottom of menu would be below viewport, flip up
      if (rect.bottom > viewportHeight - 20) {
        setFlipUp(true);
      }
    }
  }, []);

  return (
    <>
      <div className="fixed inset-0" onClick={onClose} />
      <div 
        ref={menuRef}
        className={`absolute right-0 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-1 z-10 ${
          flipUp ? 'bottom-full mb-1' : 'top-full mt-1'
        }`}
      >
        {actions.map((action, i) => (
          <button
            key={i}
            onClick={(e) => {
              e.stopPropagation();
              action.onClick();
            }}
            className={`w-full flex items-center gap-2 px-4 py-2 text-sm hover:bg-gray-50 dark:hover:bg-gray-700 ${
              action.danger
                ? 'text-red-600 dark:text-red-400'
                : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>
    </>
  );
}

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.ceil(total / pageSize);

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center justify-between">
      <p className="text-sm text-gray-500 dark:text-gray-400">
        Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total}
      </p>
      <div className="flex items-center gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
          className="px-3 py-1 rounded border dark:border-gray-600 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Previous
        </button>
        <span className="text-sm text-gray-600 dark:text-gray-400">
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
          className="px-3 py-1 rounded border dark:border-gray-600 text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Next
        </button>
      </div>
    </div>
  );
}

interface UserDetailsModalProps {
  user: AdminUser;
  onClose: () => void;
}

function UserDetailsModal({ user, onClose }: UserDetailsModalProps) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-lg font-semibold dark:text-gray-100">User Details</h3>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <XCircle className="w-5 h-5 text-gray-500" />
            </button>
          </div>

          <div className="space-y-6">
            {/* Basic Info */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm text-gray-500 dark:text-gray-400">Email</dt>
                <dd className="font-medium dark:text-gray-100">{user.email}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500 dark:text-gray-400">Full Name</dt>
                <dd className="font-medium dark:text-gray-100">{user.full_name || '-'}</dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500 dark:text-gray-400">Role</dt>
                <dd>
                  <RoleBadge role={user.role} />
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500 dark:text-gray-400">Status</dt>
                <dd>
                  <StatusBadge isActive={user.is_active} isSuspended={user.is_suspended} />
                </dd>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t dark:border-gray-700">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {user.project_count}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Projects</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {user.design_count}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Designs</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {user.warning_count}
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">Warnings</p>
              </div>
            </div>

            {/* Dates */}
            <div className="grid grid-cols-2 gap-4 pt-4 border-t dark:border-gray-700">
              <div>
                <dt className="text-sm text-gray-500 dark:text-gray-400">Joined</dt>
                <dd className="font-medium dark:text-gray-100">
                  {new Date(user.created_at).toLocaleDateString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-gray-500 dark:text-gray-400">Last Login</dt>
                <dd className="font-medium dark:text-gray-100">
                  {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : 'Never'}
                </dd>
              </div>
            </div>

            {/* Suspension Info */}
            {user.is_suspended && (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                <h4 className="font-medium text-red-700 dark:text-red-400 mb-2">Suspended</h4>
                <p className="text-sm text-red-600 dark:text-red-400">
                  Reason: {user.suspension_reason || 'Not specified'}
                </p>
                {user.suspended_until && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Until: {new Date(user.suspended_until).toLocaleDateString()}
                  </p>
                )}
              </div>
            )}
          </div>

          <div className="mt-6 flex justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Subscriptions Tab
// =============================================================================

function SubscriptionsTab() {
  const [subscriptions, setSubscriptions] = useState<AdminSubscription[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [tierFilter, setTierFilter] = useState<string>('');
  const [showChangeTierModal, setShowChangeTierModal] = useState(false);
  const [showExtendModal, setShowExtendModal] = useState(false);
  const [selectedSubscription, setSelectedSubscription] = useState<AdminSubscription | null>(null);
  const [newTier, setNewTier] = useState('');
  const [extendDays, setExtendDays] = useState(30);
  const [actionReason, setActionReason] = useState('');
  const pageSize = 20;
  
  const tiers = ['free', 'starter', 'pro', 'enterprise'];
  const statuses = ['active', 'cancelled', 'past_due', 'trialing'];

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminApi.subscriptions.listSubscriptions({
        page,
        page_size: pageSize,
        status_filter: statusFilter || undefined,
        tier_filter: tierFilter || undefined,
      });
      setSubscriptions(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch subscriptions:', err);
      setError('Failed to load subscriptions');
    } finally {
      setIsLoading(false);
    }
  }, [page, statusFilter, tierFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (successMessage) {
      const timeout = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timeout);
    }
  }, [successMessage]);

  const handleChangeTier = async () => {
    if (!selectedSubscription || !newTier) return;
    try {
      await adminApi.subscriptions.changeTier(selectedSubscription.id, newTier, actionReason);
      setSuccessMessage(`Subscription tier changed to ${newTier}`);
      setShowChangeTierModal(false);
      setSelectedSubscription(null);
      setNewTier('');
      setActionReason('');
      fetchData();
    } catch (err) {
      console.error('Failed to change tier:', err);
      setError('Failed to change subscription tier');
    }
  };

  const handleExtend = async () => {
    if (!selectedSubscription || extendDays <= 0) return;
    try {
      await adminApi.subscriptions.extendSubscription(selectedSubscription.id, extendDays, actionReason);
      setSuccessMessage(`Subscription extended by ${extendDays} days`);
      setShowExtendModal(false);
      setSelectedSubscription(null);
      setExtendDays(30);
      setActionReason('');
      fetchData();
    } catch (err) {
      console.error('Failed to extend subscription:', err);
      setError('Failed to extend subscription');
    }
  };

  const handleCancel = async (sub: AdminSubscription) => {
    if (!confirm('Are you sure you want to cancel this subscription?')) return;
    try {
      await adminApi.subscriptions.cancelSubscription(sub.id);
      setSuccessMessage('Subscription cancelled');
      fetchData();
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      setError('Failed to cancel subscription');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success Toast */}
      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-100 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-4 shadow-lg z-50 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          <span className="text-green-700 dark:text-green-400">{successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="ml-2">
            <X className="w-4 h-4 text-green-600 dark:text-green-400" />
          </button>
        </div>
      )}

      {/* Error Toast */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center gap-2">
          <XCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700 dark:text-red-400">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4 text-red-500" />
          </button>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-gray-100">Subscriptions</h2>
        <button
          onClick={fetchData}
          className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Statuses</option>
          {statuses.map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1).replace('_', ' ')}</option>
          ))}
        </select>
        <select
          value={tierFilter}
          onChange={(e) => { setTierFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Tiers</option>
          {tiers.map((t) => (
            <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
          ))}
        </select>
        <span className="self-center text-sm text-gray-500 dark:text-gray-400">{total} subscriptions</span>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Total</p>
          <p className="text-2xl font-bold dark:text-gray-100">{total.toLocaleString()}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Active</p>
          <p className="text-2xl font-bold text-green-600">
            {subscriptions.filter((s) => s.status === 'active').length}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Cancelled</p>
          <p className="text-2xl font-bold text-red-600">
            {subscriptions.filter((s) => s.status === 'cancelled').length}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Expiring Soon</p>
          <p className="text-2xl font-bold text-yellow-600">
            {subscriptions.filter((s) => s.cancel_at_period_end).length}
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Tier</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Period End</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {subscriptions.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  No subscriptions found
                </td>
              </tr>
            ) : (
              subscriptions.map((sub) => (
                <tr key={sub.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 text-sm dark:text-gray-100">
                    {sub.user_email || sub.user_id}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <TierBadge tier={sub.tier_slug} />
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <SubscriptionStatusBadge status={sub.status} cancelAtPeriodEnd={sub.cancel_at_period_end} />
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => { setSelectedSubscription(sub); setNewTier(sub.tier_slug); setShowChangeTierModal(true); }}
                        className="text-blue-600 hover:text-blue-800 dark:text-blue-400 text-xs"
                        title="Change Tier"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => { setSelectedSubscription(sub); setShowExtendModal(true); }}
                        className="text-green-600 hover:text-green-800 dark:text-green-400 text-xs"
                        title="Extend"
                      >
                        <Clock className="w-4 h-4" />
                      </button>
                      {sub.status === 'active' && (
                        <button
                          onClick={() => handleCancel(sub)}
                          className="text-red-600 hover:text-red-800 dark:text-red-400 text-xs"
                          title="Cancel"
                        >
                          <XCircle className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />

      {/* Change Tier Modal */}
      {showChangeTierModal && selectedSubscription && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold dark:text-gray-100">Change Subscription Tier</h3>
              <button onClick={() => setShowChangeTierModal(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              User: {selectedSubscription.user_email || selectedSubscription.user_id}
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">New Tier</label>
              <select
                value={newTier}
                onChange={(e) => setNewTier(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              >
                {tiers.map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Reason (optional)</label>
              <input
                type="text"
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                placeholder="Enter reason for change"
                className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowChangeTierModal(false)}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleChangeTier}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Change Tier
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Extend Subscription Modal */}
      {showExtendModal && selectedSubscription && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold dark:text-gray-100">Extend Subscription</h3>
              <button onClick={() => setShowExtendModal(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              User: {selectedSubscription.user_email || selectedSubscription.user_id}
            </p>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Days to Extend</label>
              <input
                type="number"
                value={extendDays}
                onChange={(e) => setExtendDays(Math.max(1, parseInt(e.target.value) || 1))}
                min={1}
                max={365}
                className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Reason (optional)</label>
              <input
                type="text"
                value={actionReason}
                onChange={(e) => setActionReason(e.target.value)}
                placeholder="Enter reason for extension"
                className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowExtendModal(false)}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleExtend}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
              >
                Extend Subscription
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Badge component for subscription status.
 */
function SubscriptionStatusBadge({ status, cancelAtPeriodEnd }: { status: string; cancelAtPeriodEnd: boolean }) {
  const getStyle = () => {
    if (cancelAtPeriodEnd) return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'cancelled':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      case 'past_due':
        return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
      case 'trialing':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const getLabel = () => {
    if (cancelAtPeriodEnd) return 'Cancelling';
    return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStyle()}`}>
      {getLabel()}
    </span>
  );
}

// =============================================================================
// Organizations Tab
// =============================================================================

function OrganizationsTab() {
  const [organizations, setOrganizations] = useState<AdminOrganization[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminApi.organizations.listOrganizations({ page, page_size: pageSize });
      setOrganizations(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch organizations:', err);
      setError('Failed to load organizations');
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><RefreshCw className="w-8 h-8 animate-spin text-gray-400" /></div>;
  }

  if (error) {
    return (<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center"><XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" /><p className="text-red-700 dark:text-red-400">{error}</p><button onClick={fetchData} className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200">Retry</button></div>);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-gray-100">Organizations</h2>
        <span className="text-sm text-gray-500">{total} total</span>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Slug</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Members</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Created</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {organizations.map((org) => (
              <tr key={org.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4 text-sm font-medium dark:text-gray-100">{org.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{org.slug}</td>
                <td className="px-6 py-4 text-sm dark:text-gray-100">{org.member_count}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{org.owner_email || '-'}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {new Date(org.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-sm">
                  <button className="text-blue-600 hover:text-blue-800 dark:text-blue-400 mr-2">
                    View
                  </button>
                  <button className="text-red-600 hover:text-red-800 dark:text-red-400">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
    </div>
  );
}

// =============================================================================
// Components Tab
// =============================================================================

function ComponentsTab() {
  const [components, setComponents] = useState<AdminComponent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminApi.components.listComponents({ page, page_size: pageSize });
      setComponents(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch components:', err);
      setError('Failed to load components');
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleVerify = async (componentId: string) => {
    try {
      await adminApi.components.verifyComponent(componentId);
      fetchData();
    } catch (err) {
      console.error('Failed to verify component:', err);
    }
  };

  const handleFeature = async (componentId: string) => {
    try {
      await adminApi.components.featureComponent(componentId);
      fetchData();
    } catch (err) {
      console.error('Failed to feature component:', err);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><RefreshCw className="w-8 h-8 animate-spin text-gray-400" /></div>;
  }

  if (error) {
    return (<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center"><XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" /><p className="text-red-700 dark:text-red-400">{error}</p><button onClick={fetchData} className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200">Retry</button></div>);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-gray-100">Component Library</h2>
        <span className="text-sm text-gray-500">{total} total</span>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Manufacturer</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {components.map((comp) => (
              <tr key={comp.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4 text-sm font-medium dark:text-gray-100">{comp.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{comp.manufacturer || '-'}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{comp.category || '-'}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {comp.is_library ? 'Library' : comp.user_email || '-'}
                </td>
                <td className="px-6 py-4 text-sm">
                  <div className="flex gap-2">
                    {comp.is_verified && (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                        Verified
                      </span>
                    )}
                    {comp.is_featured && (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300">
                        Featured
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm space-x-2">
                  {!comp.is_verified && (
                    <button
                      onClick={() => handleVerify(comp.id)}
                      className="text-green-600 hover:text-green-800 dark:text-green-400"
                    >
                      Verify
                    </button>
                  )}
                  {!comp.is_featured && (
                    <button
                      onClick={() => handleFeature(comp.id)}
                      className="text-yellow-600 hover:text-yellow-800 dark:text-yellow-400"
                    >
                      Feature
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
    </div>
  );
}

// =============================================================================
// Notifications Tab
// =============================================================================

function NotificationsTab() {
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);
  const [organizations, setOrganizations] = useState<AdminOrganization[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showAnnouncement, setShowAnnouncement] = useState(false);
  const [isSending, setIsSending] = useState(false);
  
  // Announcement form state
  const [announcementTitle, setAnnouncementTitle] = useState('');
  const [announcementMessage, setAnnouncementMessage] = useState('');
  const [recipientType, setRecipientType] = useState<RecipientType>('all');
  const [targetTier, setTargetTier] = useState('');
  const [targetOrganizationId, setTargetOrganizationId] = useState('');
  const [targetUserEmails, setTargetUserEmails] = useState('');
  
  const pageSize = 20;
  const tiers = ['free', 'starter', 'pro', 'enterprise'];

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [notifData, orgsData] = await Promise.all([
        adminApi.notifications.listNotifications({ page, page_size: pageSize }),
        adminApi.organizations.listOrganizations({ page: 1, page_size: 100 }),
      ]);
      setNotifications(notifData.items);
      setTotal(notifData.total);
      setOrganizations(orgsData.items);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
      setError('Failed to load notifications');
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (successMessage) {
      const timeout = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timeout);
    }
  }, [successMessage]);

  const resetForm = () => {
    setAnnouncementTitle('');
    setAnnouncementMessage('');
    setRecipientType('all');
    setTargetTier('');
    setTargetOrganizationId('');
    setTargetUserEmails('');
    setShowAnnouncement(false);
  };

  const handleCreateAnnouncement = async () => {
    if (!announcementTitle.trim() || !announcementMessage.trim()) {
      setError('Title and message are required');
      return;
    }

    setIsSending(true);
    setError(null);
    
    try {
      const request: {
        title: string;
        message: string;
        recipient_type: RecipientType;
        target_tier?: string;
        target_organization_id?: string;
        target_user_ids?: string[];
      } = {
        title: announcementTitle,
        message: announcementMessage,
        recipient_type: recipientType,
      };

      if (recipientType === 'tier' && targetTier) {
        request.target_tier = targetTier;
      } else if (recipientType === 'organization' && targetOrganizationId) {
        request.target_organization_id = targetOrganizationId;
      } else if (recipientType === 'users' && targetUserEmails.trim()) {
        // Note: In a real implementation, you'd look up user IDs from emails
        // For now, we'll pass them as-is (assuming backend handles lookup)
        request.target_user_ids = targetUserEmails.split(',').map((e) => e.trim());
      }

      const result = await adminApi.notifications.createAnnouncement(request);
      setSuccessMessage(result.message);
      resetForm();
      fetchData();
    } catch (err) {
      console.error('Failed to create announcement:', err);
      setError('Failed to send announcement');
    } finally {
      setIsSending(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success Toast */}
      {successMessage && (
        <div className="fixed top-4 right-4 bg-green-100 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg p-4 shadow-lg z-50 flex items-center gap-2">
          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
          <span className="text-green-700 dark:text-green-400">{successMessage}</span>
          <button onClick={() => setSuccessMessage(null)} className="ml-2">
            <X className="w-4 h-4 text-green-600 dark:text-green-400" />
          </button>
        </div>
      )}

      {/* Error Toast */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-center gap-2">
          <XCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-700 dark:text-red-400">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4 text-red-500" />
          </button>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-gray-100">Notifications</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => setShowAnnouncement(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
          >
            <Bell className="w-4 h-4" />
            New Announcement
          </button>
        </div>
      </div>

      {/* Create Announcement Modal */}
      {showAnnouncement && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold dark:text-gray-100">Create Announcement</h3>
              <button onClick={resetForm} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Title <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={announcementTitle}
                onChange={(e) => setAnnouncementTitle(e.target.value)}
                placeholder="Announcement title"
                className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                maxLength={200}
              />
            </div>

            {/* Message */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Message <span className="text-red-500">*</span>
              </label>
              <textarea
                value={announcementMessage}
                onChange={(e) => setAnnouncementMessage(e.target.value)}
                placeholder="Enter your announcement message..."
                rows={4}
                className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                maxLength={2000}
              />
              <p className="text-xs text-gray-500 mt-1">{announcementMessage.length}/2000</p>
            </div>

            {/* Recipient Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Send To
              </label>
              <select
                value={recipientType}
                onChange={(e) => setRecipientType(e.target.value as RecipientType)}
                className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              >
                <option value="all">All Users</option>
                <option value="tier">Specific Tier</option>
                <option value="organization">Specific Organization</option>
                <option value="users">Specific Users</option>
              </select>
            </div>

            {/* Tier Selection */}
            {recipientType === 'tier' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Select Tier
                </label>
                <select
                  value={targetTier}
                  onChange={(e) => setTargetTier(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                >
                  <option value="">Select a tier...</option>
                  {tiers.map((tier) => (
                    <option key={tier} value={tier}>
                      {tier.charAt(0).toUpperCase() + tier.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Organization Selection */}
            {recipientType === 'organization' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Select Organization
                </label>
                <select
                  value={targetOrganizationId}
                  onChange={(e) => setTargetOrganizationId(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                >
                  <option value="">Select an organization...</option>
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* User Emails */}
            {recipientType === 'users' && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  User IDs (comma-separated)
                </label>
                <textarea
                  value={targetUserEmails}
                  onChange={(e) => setTargetUserEmails(e.target.value)}
                  placeholder="user-id-1, user-id-2, user-id-3"
                  rows={2}
                  className="w-full px-4 py-2 border rounded-lg dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
                />
                <p className="text-xs text-gray-500 mt-1">Enter user IDs separated by commas</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-4 border-t dark:border-gray-700">
              <button
                onClick={resetForm}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateAnnouncement}
                disabled={isSending || !announcementTitle.trim() || !announcementMessage.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Bell className="w-4 h-4" />
                    Send Announcement
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Total Notifications</p>
          <p className="text-2xl font-bold dark:text-gray-100">{total.toLocaleString()}</p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Read</p>
          <p className="text-2xl font-bold text-green-600">
            {notifications.filter((n) => n.is_read).length}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Unread</p>
          <p className="text-2xl font-bold text-yellow-600">
            {notifications.filter((n) => !n.is_read).length}
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
          <p className="text-sm text-gray-500 dark:text-gray-400">Announcements</p>
          <p className="text-2xl font-bold text-blue-600">
            {notifications.filter((n) => n.notification_type === 'system_announcement').length}
          </p>
        </div>
      </div>

      {/* Notification History Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
        <div className="px-6 py-4 border-b dark:border-gray-700">
          <h3 className="font-semibold dark:text-gray-100">Notification History</h3>
        </div>
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                User
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Type
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                Created
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {notifications.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  No notifications found
                </td>
              </tr>
            ) : (
              notifications.map((notif) => (
                <tr key={notif.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 text-sm dark:text-gray-100">
                    {notif.user_email || notif.user_id}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <NotificationTypeBadge type={notif.notification_type} />
                  </td>
                  <td className="px-6 py-4 text-sm dark:text-gray-100 max-w-xs truncate">
                    {notif.title}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {notif.is_read ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400">
                        <CheckCircle className="w-3 h-3" /> Read
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
                        <Clock className="w-3 h-3" /> Unread
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {new Date(notif.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
    </div>
  );
}

/**
 * Badge component for notification types.
 */
function NotificationTypeBadge({ type }: { type: string }) {
  const getStyle = () => {
    switch (type) {
      case 'system_announcement':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
      case 'admin_message':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
      case 'job_completed':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'job_failed':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  const getLabel = () => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStyle()}`}>
      {getLabel()}
    </span>
  );
}

// =============================================================================
// Storage Tab
// =============================================================================

function StorageTab() {
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [files, setFiles] = useState<AdminFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [statsData, filesData] = await Promise.all([
        adminApi.storage.getStats(),
        adminApi.storage.listFiles({ page, page_size: pageSize }),
      ]);
      setStats(statsData);
      setFiles(filesData.items);
      setTotal(filesData.total);
    } catch (err) {
      console.error('Failed to fetch storage data:', err);
      setError('Failed to load storage data');
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><RefreshCw className="w-8 h-8 animate-spin text-gray-400" /></div>;
  }

  if (error) {
    return (<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center"><XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" /><p className="text-red-700 dark:text-red-400">{error}</p><button onClick={fetchData} className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200">Retry</button></div>);
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold dark:text-gray-100">Storage Management</h2>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">Total Files</p>
            <p className="text-2xl font-bold dark:text-gray-100">{stats.total_files.toLocaleString()}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">Total Size</p>
            <p className="text-2xl font-bold dark:text-gray-100">{stats.total_size_gb} GB</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">File Types</p>
            <p className="text-2xl font-bold dark:text-gray-100">{Object.keys(stats.files_by_type).length}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-6">
            <p className="text-sm text-gray-500 dark:text-gray-400">Top Users</p>
            <p className="text-2xl font-bold dark:text-gray-100">{stats.top_users.length}</p>
          </div>
        </div>
      )}

      {/* Files Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Filename</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Type</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Size</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Created</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {files.map((file) => (
              <tr key={file.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4 text-sm font-medium dark:text-gray-100">{file.original_filename}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{file.user_email || file.user_id}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{file.mime_type}</td>
                <td className="px-6 py-4 text-sm dark:text-gray-100">{formatBytes(file.size_bytes)}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {new Date(file.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4 text-sm">
                  <button className="text-red-600 hover:text-red-800 dark:text-red-400">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
    </div>
  );
}

// =============================================================================
// Audit Tab
// =============================================================================

function AuditTab() {
  const [logs, setLogs] = useState<AdminAuditLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [actionFilter, setActionFilter] = useState<string>('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [selectedLog, setSelectedLog] = useState<AdminAuditLog | null>(null);
  const pageSize = 50;

  // Common action types in audit logs
  const actionTypes = [
    'create', 'update', 'delete', 'login', 'logout', 'view', 
    'export', 'import', 'suspend', 'unsuspend', 'approve', 'reject'
  ];
  
  // Common resource types
  const resourceTypes = [
    'user', 'project', 'design', 'template', 'job', 'organization',
    'subscription', 'notification', 'api_key', 'file'
  ];

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminApi.audit.getLogs({
        page,
        page_size: pageSize,
        action: actionFilter || undefined,
        resource_type: resourceTypeFilter || undefined,
      });
      setLogs(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
      setError('Failed to load audit logs');
    } finally {
      setIsLoading(false);
    }
  }, [page, actionFilter, resourceTypeFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Filter logs by search query (client-side filtering for immediate feedback)
  const filteredLogs = logs.filter((log) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (log.user_email?.toLowerCase().includes(query) || false) ||
      log.action.toLowerCase().includes(query) ||
      log.resource_type.toLowerCase().includes(query) ||
      (log.ip_address?.toLowerCase().includes(query) || false)
    );
  });

  const handleExportCSV = () => {
    const headers = ['Time', 'User', 'Actor Type', 'Action', 'Resource Type', 'Resource ID', 'IP Address'];
    const rows = filteredLogs.map((log) => [
      new Date(log.created_at).toISOString(),
      log.user_email || log.actor_type,
      log.actor_type,
      log.action,
      log.resource_type,
      log.resource_id || '',
      log.ip_address || '',
    ]);
    
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getActionBadgeStyle = (action: string) => {
    if (action.includes('create') || action.includes('approve')) {
      return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    }
    if (action.includes('delete') || action.includes('reject') || action.includes('suspend')) {
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
    }
    if (action.includes('update') || action.includes('modify')) {
      return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
    }
    if (action.includes('login') || action.includes('logout')) {
      return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
    }
    return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
        <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-400">{error}</p>
        <button
          onClick={fetchData}
          className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-gray-100">Audit Logs</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportCSV}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <FileText className="w-4 h-4" />
            Export CSV
          </button>
          <button
            onClick={fetchData}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search logs..."
              className="w-full pl-10 pr-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
            />
          </div>
        </div>
        <select
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Actions</option>
          {actionTypes.map((a) => (
            <option key={a} value={a}>{a.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
          ))}
        </select>
        <select
          value={resourceTypeFilter}
          onChange={(e) => { setResourceTypeFilter(e.target.value); setPage(1); }}
          className="px-4 py-2 border dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 dark:text-gray-100"
        >
          <option value="">All Resources</option>
          {resourceTypes.map((r) => (
            <option key={r} value={r}>{r.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</option>
          ))}
        </select>
        <span className="self-center text-sm text-gray-500 dark:text-gray-400">
          {filteredLogs.length} of {total} logs
        </span>
      </div>

      {/* Logs Table */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Time</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">User</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Action</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Resource</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">IP Address</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                  No audit logs found
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-sm dark:text-gray-100">
                    <div className="flex flex-col">
                      <span>{log.user_email || 'System'}</span>
                      <span className="text-xs text-gray-400">{log.actor_type}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionBadgeStyle(log.action)}`}>
                      {log.action.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    <div className="flex flex-col">
                      <span className="font-medium dark:text-gray-300">{log.resource_type}</span>
                      {log.resource_id && (
                        <span className="text-xs font-mono">{log.resource_id.slice(0, 8)}...</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 font-mono">
                    {log.ip_address || '-'}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <button
                      onClick={() => { setSelectedLog(log); setShowDetailsModal(true); }}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />

      {/* Details Modal */}
      {showDetailsModal && selectedLog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold dark:text-gray-100">Audit Log Details</h3>
              <button onClick={() => setShowDetailsModal(false)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">ID:</span>
                <span className="col-span-2 dark:text-gray-100 font-mono text-xs">{selectedLog.id}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">Time:</span>
                <span className="col-span-2 dark:text-gray-100">{new Date(selectedLog.created_at).toLocaleString()}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">User:</span>
                <span className="col-span-2 dark:text-gray-100">{selectedLog.user_email || 'N/A'}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">User ID:</span>
                <span className="col-span-2 dark:text-gray-100 font-mono text-xs">{selectedLog.user_id || 'N/A'}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">Actor Type:</span>
                <span className="col-span-2 dark:text-gray-100">{selectedLog.actor_type}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">Action:</span>
                <span className="col-span-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionBadgeStyle(selectedLog.action)}`}>
                    {selectedLog.action}
                  </span>
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">Resource:</span>
                <span className="col-span-2 dark:text-gray-100">{selectedLog.resource_type}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">Resource ID:</span>
                <span className="col-span-2 dark:text-gray-100 font-mono text-xs">{selectedLog.resource_id || 'N/A'}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <span className="text-gray-500 dark:text-gray-400">IP Address:</span>
                <span className="col-span-2 dark:text-gray-100 font-mono">{selectedLog.ip_address || 'N/A'}</span>
              </div>
            </div>
            <div className="flex justify-end pt-4 border-t dark:border-gray-700">
              <button
                onClick={() => setShowDetailsModal(false)}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// API Keys Tab
// =============================================================================

function APIKeysTab() {
  const [keys, setKeys] = useState<AdminAPIKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminApi.apiKeys.listKeys({ page, page_size: pageSize });
      setKeys(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch API keys:', err);
      setError('Failed to load API keys');
    } finally {
      setIsLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleRevoke = async (keyId: string) => {
    if (!confirm('Are you sure you want to revoke this API key?')) return;
    try {
      await adminApi.apiKeys.revokeKey(keyId);
      fetchData();
    } catch (err) {
      console.error('Failed to revoke API key:', err);
    }
  };

  if (isLoading) {
    return <div className="flex items-center justify-center h-64"><RefreshCw className="w-8 h-8 animate-spin text-gray-400" /></div>;
  }

  if (error) {
    return (<div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center"><XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" /><p className="text-red-700 dark:text-red-400">{error}</p><button onClick={fetchData} className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200">Retry</button></div>);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-gray-100">API Keys</h2>
        <span className="text-sm text-gray-500">{total} total</span>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-700">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Key Prefix</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Last Used</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {keys.map((key) => (
              <tr key={key.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                <td className="px-6 py-4 text-sm font-medium dark:text-gray-100">{key.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">{key.user_email || key.user_id}</td>
                <td className="px-6 py-4 text-sm font-mono text-gray-500 dark:text-gray-400">{key.key_prefix}...</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    key.is_active 
                      ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                      : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                  }`}>
                    {key.is_active ? 'Active' : 'Revoked'}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                  {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : 'Never'}
                </td>
                <td className="px-6 py-4 text-sm">
                  {key.is_active && (
                    <button
                      onClick={() => handleRevoke(key.id)}
                      className="text-red-600 hover:text-red-800 dark:text-red-400"
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Pagination page={page} pageSize={pageSize} total={total} onPageChange={setPage} />
    </div>
  );
}

// =============================================================================
// System Tab
// =============================================================================

function SystemTab() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const fetchData = useCallback(async () => {
    if (!autoRefresh) {
      setIsLoading(true);
    }
    setError(null);
    try {
      const data = await adminApi.system.getHealth();
      setHealth(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch system health:', err);
      setError('Failed to load system health');
    } finally {
      setIsLoading(false);
    }
  }, [autoRefresh]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    if (autoRefresh) {
      const interval = setInterval(fetchData, 30000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, fetchData]);

  const getServiceIcon = (name: string) => {
    switch (name) {
      case 'api':
        return <Server className="w-5 h-5" />;
      case 'database':
        return <HardDrive className="w-5 h-5" />;
      case 'redis':
        return <Activity className="w-5 h-5" />;
      case 'celery':
        return <Clock className="w-5 h-5" />;
      case 'storage':
        return <FolderOpen className="w-5 h-5" />;
      case 'ai':
        return <Component className="w-5 h-5" />;
      default:
        return <Server className="w-5 h-5" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'text-green-500';
      case 'degraded':
        return 'text-yellow-500';
      case 'unhealthy':
        return 'text-red-500';
      default:
        return 'text-gray-500';
    }
  };

  const getStatusBgColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
      case 'degraded':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'unhealthy':
        return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
        <XCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-400">{error}</p>
        <button
          onClick={fetchData}
          className="mt-4 px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg hover:bg-red-200"
        >
          Retry
        </button>
      </div>
    );
  }

  const healthyCount = health?.services.filter((s) => s.status === 'healthy').length || 0;
  const totalCount = health?.services.length || 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold dark:text-gray-100">System Health</h2>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            Auto-refresh (30s)
          </label>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
          >
            <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {health && (
        <>
          {/* Overall Status Card */}
          <div className={`rounded-xl shadow p-6 ${
            health.overall_status === 'healthy' 
              ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800' 
              : health.overall_status === 'degraded'
              ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
              : 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className={`w-6 h-6 rounded-full ${
                  health.overall_status === 'healthy' ? 'bg-green-500' :
                  health.overall_status === 'degraded' ? 'bg-yellow-500' :
                  'bg-red-500'
                } animate-pulse`} />
                <div>
                  <p className={`text-2xl font-bold capitalize ${getStatusColor(health.overall_status)}`}>
                    {health.overall_status === 'healthy' ? 'All Systems Operational' :
                     health.overall_status === 'degraded' ? 'Some Systems Degraded' :
                     'System Issues Detected'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {healthyCount} of {totalCount} services healthy
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500 dark:text-gray-400">Version: {health.version}</p>
                {lastUpdated && (
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Last updated: {lastUpdated.toLocaleTimeString()}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Services Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {health.services.map((service) => (
              <div 
                key={service.name} 
                className="bg-white dark:bg-gray-800 rounded-xl shadow p-6 border dark:border-gray-700"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${getStatusBgColor(service.status)}`}>
                      {getServiceIcon(service.name)}
                    </div>
                    <div>
                      <p className="font-semibold dark:text-gray-100 capitalize">{service.name}</p>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${getStatusBgColor(service.status)}`}>
                        {service.status}
                      </span>
                    </div>
                  </div>
                  <div className={`w-3 h-3 rounded-full ${
                    service.status === 'healthy' ? 'bg-green-500' :
                    service.status === 'degraded' ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`} />
                </div>
                {service.latency_ms !== undefined && service.latency_ms !== null && (
                  <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-2">
                    <Clock className="w-4 h-4" />
                    <span>Response time: {service.latency_ms}ms</span>
                  </div>
                )}
                {service.message && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">{service.message}</p>
                )}
              </div>
            ))}
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Healthy Services</p>
              <p className="text-2xl font-bold text-green-600">{healthyCount}</p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Degraded</p>
              <p className="text-2xl font-bold text-yellow-600">
                {health.services.filter((s) => s.status === 'degraded').length}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Unhealthy</p>
              <p className="text-2xl font-bold text-red-600">
                {health.services.filter((s) => s.status === 'unhealthy').length}
              </p>
            </div>
            <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Services</p>
              <p className="text-2xl font-bold dark:text-gray-100">{totalCount}</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default AdminDashboard;