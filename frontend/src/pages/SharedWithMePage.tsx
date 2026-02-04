/**
 * Shared With Me Page - View designs shared by other users.
 * 
 * DEPRECATED: This page is being replaced by the Lists feature.
 * Users should migrate to using /lists for managing saved and shared designs.
 */

import {
  Users,
  FileBox,
  Clock,
  User,
  Eye,
  MessageSquare,
  Edit3,
  Search,
  Grid3X3,
  List,
  Filter,
  AlertCircle,
  ArrowRight,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface SharedDesign {
  id: string;
  design_id: string;
  design_name: string;
  design_thumbnail_url: string | null;
  shared_by_id: string;
  shared_by_name: string;
  shared_by_email: string;
  permission: 'view' | 'comment' | 'edit';
  shared_at: string;
}

// =============================================================================
// Shared With Me Page Component
// =============================================================================

export function SharedWithMePage() {
  const navigate = useNavigate();
  const { token } = useAuth();

  // State
  const [shares, setShares] = useState<SharedDesign[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [permissionFilter, setPermissionFilter] = useState<'all' | 'view' | 'comment' | 'edit'>('all');

  // Fetch shared designs
  const fetchSharedDesigns = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/shares/shared-with-me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch shared designs');

      const data = await response.json();
      setShares(data.items || data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load shared designs');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  // Load on mount
  useEffect(() => {
    fetchSharedDesigns();
  }, [fetchSharedDesigns]);

  // Filter shares
  const filteredShares = shares.filter(share => {
    const matchesSearch = 
      share.design_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      share.shared_by_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      share.shared_by_email.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesPermission = permissionFilter === 'all' || share.permission === permissionFilter;
    
    return matchesSearch && matchesPermission;
  });

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  // Get permission badge
  const getPermissionBadge = (permission: 'view' | 'comment' | 'edit') => {
    const config = {
      view: { icon: Eye, label: 'View', color: 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300' },
      comment: { icon: MessageSquare, label: 'Comment', color: 'bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300' },
      edit: { icon: Edit3, label: 'Edit', color: 'bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-300' },
    };
    const { icon: Icon, label, color } = config[permission];
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${color}`}>
        <Icon className="w-3 h-3" />
        {label}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Deprecation Notice */}
      <div className="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
              This page is being replaced
            </h3>
            <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
              We've introduced a new way to save and organize designs using Lists. 
              This page will be removed in a future update.
            </p>
            <Link
              to="/lists"
              className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-200 hover:text-amber-900 dark:hover:text-amber-100"
            >
              Go to My Lists
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary-100 dark:bg-primary-900 rounded-lg">
            <Users className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Shared With Me</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {shares.length} design{shares.length !== 1 ? 's' : ''} shared with you
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
            <input
              type="text"
              placeholder="Search designs..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500"
            />
          </div>

          {/* Permission Filter */}
          <div className="relative">
            <select
              value={permissionFilter}
              onChange={(e) => setPermissionFilter(e.target.value as typeof permissionFilter)}
              className="pl-8 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 appearance-none bg-white dark:bg-gray-800 text-gray-900 dark:text-white"
            >
              <option value="all">All permissions</option>
              <option value="view">View only</option>
              <option value="comment">Can comment</option>
              <option value="edit">Can edit</option>
            </select>
            <Filter className="absolute left-2.5 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-gray-500" />
          </div>

          {/* View Toggle */}
          <div className="flex bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-white dark:bg-gray-700 shadow' : ''}`}
            >
              <Grid3X3 className="w-4 h-4 text-gray-600 dark:text-gray-300" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-white dark:bg-gray-700 shadow' : ''}`}
            >
              <List className="w-4 h-4 text-gray-600 dark:text-gray-300" />
            </button>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-3 rounded-lg">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : filteredShares.length === 0 ? (
        /* Empty State */
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <Users className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-gray-400">
            {searchQuery || permissionFilter !== 'all'
              ? 'No designs match your filters'
              : 'No designs have been shared with you yet'}
          </p>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid View */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredShares.map(share => (
            <div
              key={share.id}
              onClick={() => navigate(`/designs/${share.design_id}`)}
              className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer group"
            >
              <div className="aspect-square bg-gray-100 dark:bg-gray-700 rounded-t-lg flex items-center justify-center relative">
                {share.design_thumbnail_url ? (
                  <img
                    src={share.design_thumbnail_url}
                    alt={share.design_name}
                    className="w-full h-full object-cover rounded-t-lg"
                  />
                ) : (
                  <FileBox className="w-12 h-12 text-gray-300 dark:text-gray-600" />
                )}
                <div className="absolute top-2 right-2">
                  {getPermissionBadge(share.permission)}
                </div>
              </div>
              <div className="p-3">
                <h3 className="font-medium text-gray-900 dark:text-white truncate">{share.design_name}</h3>
                <div className="flex items-center gap-2 mt-2 text-sm text-gray-500 dark:text-gray-400">
                  <div className="w-5 h-5 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                    <User className="w-3 h-3 text-gray-500 dark:text-gray-400" />
                  </div>
                  <span className="truncate">{share.shared_by_name}</span>
                </div>
                <p className="text-xs text-gray-400 dark:text-gray-500 mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDate(share.shared_at)}
                </p>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* List View */
        <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 divide-y divide-gray-200 dark:divide-gray-700">
          {filteredShares.map(share => (
            <div
              key={share.id}
              onClick={() => navigate(`/designs/${share.design_id}`)}
              className="flex items-center gap-4 p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
            >
              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center flex-shrink-0">
                {share.design_thumbnail_url ? (
                  <img
                    src={share.design_thumbnail_url}
                    alt={share.design_name}
                    className="w-full h-full object-cover rounded-lg"
                  />
                ) : (
                  <FileBox className="w-8 h-8 text-gray-300 dark:text-gray-600" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium text-gray-900 dark:text-white truncate">{share.design_name}</h3>
                <div className="flex items-center gap-2 mt-1 text-sm text-gray-500 dark:text-gray-400">
                  <div className="w-4 h-4 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                    <User className="w-2.5 h-2.5 text-gray-500 dark:text-gray-400" />
                  </div>
                  <span>{share.shared_by_name}</span>
                  <span className="text-gray-300 dark:text-gray-600">•</span>
                  <span>{share.shared_by_email}</span>
                </div>
              </div>
              <div className="flex items-center gap-4">
                {getPermissionBadge(share.permission)}
                <span className="text-sm text-gray-400 dark:text-gray-500 whitespace-nowrap">
                  {formatDate(share.shared_at)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
