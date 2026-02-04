/**
 * Dashboard page component.
 * 
 * Shows user statistics, recent designs, and quick actions.
 */

import { Box, Plus, Clock, TrendingUp, Folder, Loader2, AlertCircle } from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface DashboardStats {
  total_projects: number;
  total_designs: number;
  designs_this_month: number;
  generations_this_month: number;
  exports_this_month: number;
}

interface RecentDesign {
  id: string;
  name: string;
  project_id: string;
  project_name: string;
  thumbnail_url: string | null;
  source_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

interface RecentActivity {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

interface DashboardData {
  stats: DashboardStats;
  recent_designs: RecentDesign[];
  recent_activity: RecentActivity[];
}

// =============================================================================
// Component
// =============================================================================

export function DashboardPage() {
  const { user, token } = useAuth();
  
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch dashboard data
  const fetchDashboard = useCallback(async () => {
    if (!token) return;

    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`${API_BASE}/dashboard`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to load dashboard data');
      }

      const dashboardData = await response.json();
      setData(dashboardData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Format relative time
  const formatTimeAgo = (dateString: string): string => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} minutes ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
    return date.toLocaleDateString();
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <AlertCircle className="w-12 h-12 text-red-500" />
        <p className="text-gray-600 dark:text-gray-400">{error}</p>
        <button
          onClick={fetchDashboard}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  const stats = data?.stats || {
    total_projects: 0,
    total_designs: 0,
    designs_this_month: 0,
    generations_this_month: 0,
    exports_this_month: 0,
  };

  const recentDesigns = data?.recent_designs || [];

  return (
    <div>
      {/* Welcome Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Welcome back, {user?.display_name || user?.email?.split('@')[0]}!
        </h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Here&apos;s what&apos;s happening with your projects.
        </p>
      </div>

      {/* Quick Actions */}
      <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <Link
          to="/create"
          className="flex items-center gap-4 p-4 bg-primary-50 dark:bg-primary-900/30 rounded-lg border border-primary-100 dark:border-primary-800 hover:bg-primary-100 dark:hover:bg-primary-900/50 transition-colors"
        >
          <div className="h-12 w-12 bg-primary-600 rounded-lg flex items-center justify-center">
            <Plus className="h-6 w-6 text-white" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-gray-100">New Part</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Generate from description</p>
          </div>
        </Link>

        <Link
          to="/templates"
          className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
        >
          <div className="h-12 w-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
            <Box className="h-6 w-6 text-gray-600 dark:text-gray-400" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-gray-100">Templates</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Browse part templates</p>
          </div>
        </Link>

        <Link
          to="/projects"
          className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
        >
          <div className="h-12 w-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
            <Folder className="h-6 w-6 text-gray-600 dark:text-gray-400" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-gray-100">Projects</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">Manage your projects</p>
          </div>
        </Link>

        <Link
          to="/files"
          className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600 transition-colors"
        >
          <div className="h-12 w-12 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
            <Clock className="h-6 w-6 text-gray-600 dark:text-gray-400" />
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-gray-100">Recent Files</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">View your files</p>
          </div>
        </Link>
      </div>

      {/* Stats - Clickable cards */}
      <div className="grid md:grid-cols-4 gap-4 mb-8">
        <Link
          to="/projects"
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md transition-all cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Folder className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total_projects}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Projects</p>
            </div>
          </div>
        </Link>

        <Link
          to="/designs"
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:border-green-300 dark:hover:border-green-600 hover:shadow-md transition-all cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <Box className="h-5 w-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.total_designs}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Designs</p>
            </div>
          </div>
        </Link>

        <Link
          to="/activity?filter=generations"
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-md transition-all cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.generations_this_month}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Generations</p>
            </div>
          </div>
        </Link>

        <Link
          to="/activity?filter=exports"
          className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:border-orange-300 dark:hover:border-orange-600 hover:shadow-md transition-all cursor-pointer"
        >
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
              <Clock className="h-5 w-5 text-orange-600 dark:text-orange-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.exports_this_month}</p>
              <p className="text-sm text-gray-600 dark:text-gray-400">Exports</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Recent Designs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Recent Designs</h2>
          <Link
            to="/projects"
            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
          >
            View all →
          </Link>
        </div>
        
        {recentDesigns.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <Box className="w-12 h-12 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
            <p className="text-gray-500 dark:text-gray-400">No designs yet</p>
            <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">
              Create your first design using AI generation or templates
            </p>
            <Link
              to="/create"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="w-4 h-4" />
              Generate Part
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-gray-100 dark:divide-gray-700">
            {recentDesigns.map((design) => (
              <Link
                key={design.id}
                to={`/projects/${design.project_id}`}
                className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <div className="flex items-center gap-3">
                  {design.thumbnail_url ? (
                    <img
                      src={design.thumbnail_url}
                      alt={design.name}
                      className="h-10 w-10 rounded-lg object-cover bg-gray-100 dark:bg-gray-700"
                    />
                  ) : (
                    <div className="h-10 w-10 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                      <Box className="h-5 w-5 text-gray-500 dark:text-gray-400" />
                    </div>
                  )}
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">{design.name}</p>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      in {design.project_name} • {formatTimeAgo(design.updated_at)}
                    </p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  design.source_type === 'ai_generated' 
                    ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
                    : design.source_type === 'template'
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                    : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300'
                }`}>
                  {design.source_type === 'ai_generated' ? 'AI Generated' : 
                   design.source_type === 'template' ? 'From Template' : 
                   design.source_type}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;
