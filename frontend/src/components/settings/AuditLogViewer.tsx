/**
 * Audit Log Viewer Component
 *
 * Displays audit logs for the current user with pagination and filtering.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Filter,
  Loader2,
  XCircle,
} from 'lucide-react';

import { auditLogsApi, type AuditLog, type AuditLogsFilters } from '@/lib/api/auditLogs';

const ITEMS_PER_PAGE = 20;

/**
 * Format action name for display
 */
function formatAction(action: string): string {
  return action
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Format resource type for display
 */
function formatResourceType(resourceType: string): string {
  return resourceType.charAt(0).toUpperCase() + resourceType.slice(1);
}

/**
 * Format date/time for display
 */
function formatDateTime(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

/**
 * Get status icon and color
 */
function getStatusDisplay(status: string): { icon: JSX.Element; color: string } {
  switch (status) {
    case 'success':
      return {
        icon: <CheckCircle className="w-4 h-4" />,
        color: 'text-green-600 dark:text-green-400',
      };
    case 'failure':
      return {
        icon: <XCircle className="w-4 h-4" />,
        color: 'text-red-600 dark:text-red-400',
      };
    case 'error':
      return {
        icon: <AlertCircle className="w-4 h-4" />,
        color: 'text-orange-600 dark:text-orange-400',
      };
    default:
      return {
        icon: <Clock className="w-4 h-4" />,
        color: 'text-gray-600 dark:text-gray-400',
      };
  }
}

export default function AuditLogViewer() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [startDateFilter, setStartDateFilter] = useState<string>('');
  const [endDateFilter, setEndDateFilter] = useState<string>('');

  /**
   * Fetch audit logs
   */
  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const filters: AuditLogsFilters = {
        skip: (currentPage - 1) * ITEMS_PER_PAGE,
        limit: ITEMS_PER_PAGE,
      };

      if (actionFilter) filters.action = actionFilter;
      if (resourceTypeFilter) filters.resource_type = resourceTypeFilter;
      if (statusFilter) filters.status = statusFilter;
      if (startDateFilter) filters.start_date = new Date(startDateFilter).toISOString();
      if (endDateFilter) filters.end_date = new Date(endDateFilter).toISOString();

      const response = await auditLogsApi.getUserAuditLogs(filters);
      setLogs(response.logs);
      setTotal(response.total);
    } catch (err) {
      console.error('Failed to fetch audit logs:', err);
      setError(err instanceof Error ? err.message : 'Failed to load audit logs');
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, actionFilter, resourceTypeFilter, statusFilter, startDateFilter, endDateFilter]);

  /**
   * Load logs on mount and when filters/page changes
   */
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  /**
   * Reset filters
   */
  const handleResetFilters = () => {
    setActionFilter('');
    setResourceTypeFilter('');
    setStatusFilter('');
    setStartDateFilter('');
    setEndDateFilter('');
    setCurrentPage(1);
  };

  /**
   * Handle page change
   */
  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
  const hasFilters = actionFilter || resourceTypeFilter || statusFilter || startDateFilter || endDateFilter;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Audit Log</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            View all actions performed in your account
          </p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            showFilters || hasFilters
              ? 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300'
              : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
          }`}
        >
          <Filter className="w-4 h-4" />
          Filters
          {hasFilters && <span className="px-1.5 py-0.5 bg-cyan-600 text-white rounded text-xs">•</span>}
        </button>
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-lg p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Action filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Action
              </label>
              <select
                value={actionFilter}
                onChange={(e) => {
                  setActionFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">All actions</option>
                <option value="login">Login</option>
                <option value="logout">Logout</option>
                <option value="create">Create</option>
                <option value="update">Update</option>
                <option value="delete">Delete</option>
                <option value="export">Export</option>
                <option value="share">Share</option>
              </select>
            </div>

            {/* Resource Type filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Resource Type
              </label>
              <select
                value={resourceTypeFilter}
                onChange={(e) => {
                  setResourceTypeFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">All types</option>
                <option value="user">User</option>
                <option value="design">Design</option>
                <option value="project">Project</option>
                <option value="template">Template</option>
              </select>
            </div>

            {/* Status filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Status
              </label>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              >
                <option value="">All statuses</option>
                <option value="success">Success</option>
                <option value="failure">Failure</option>
                <option value="error">Error</option>
              </select>
            </div>

            {/* Start date filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Start Date
              </label>
              <input
                type="date"
                value={startDateFilter}
                onChange={(e) => {
                  setStartDateFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>

            {/* End date filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                End Date
              </label>
              <input
                type="date"
                value={endDateFilter}
                onChange={(e) => {
                  setEndDateFilter(e.target.value);
                  setCurrentPage(1);
                }}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          {/* Reset button */}
          {hasFilters && (
            <div className="flex justify-end">
              <button
                onClick={handleResetFilters}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100"
              >
                Reset Filters
              </button>
            </div>
          )}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <div className="flex items-center gap-2 text-red-800 dark:text-red-200">
            <AlertCircle className="w-5 h-5" />
            <p className="font-medium">{error}</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && logs.length === 0 && (
        <div className="text-center py-12">
          <Clock className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
            No audit logs found
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            {hasFilters ? 'Try adjusting your filters' : 'Your activity will appear here'}
          </p>
        </div>
      )}

      {/* Audit logs table */}
      {!isLoading && !error && logs.length > 0 && (
        <div className="border dark:border-gray-700 rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Date & Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Resource
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    IP Address
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {logs.map((log) => {
                  const statusDisplay = getStatusDisplay(log.status);
                  return (
                    <tr key={log.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {formatDateTime(log.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {formatAction(log.action)}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400">
                        {formatResourceType(log.resource_type)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`flex items-center gap-1.5 ${statusDisplay.color}`}>
                          {statusDisplay.icon}
                          <span className="text-sm font-medium capitalize">{log.status}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 dark:text-gray-400 font-mono">
                        {log.ip_address || '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="bg-gray-50 dark:bg-gray-800 px-6 py-4 flex items-center justify-between border-t dark:border-gray-700">
              <div className="text-sm text-gray-700 dark:text-gray-300">
                Showing {(currentPage - 1) * ITEMS_PER_PAGE + 1} to{' '}
                {Math.min(currentPage * ITEMS_PER_PAGE, total)} of {total} logs
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-sm text-gray-700 dark:text-gray-300">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
