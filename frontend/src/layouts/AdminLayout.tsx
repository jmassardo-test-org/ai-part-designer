/**
 * Admin Layout Component.
 *
 * Provides consistent navigation and structure for all admin pages.
 * Each section is a separate route for better performance.
 */

import {
  Shield,
  Users,
  AlertTriangle,
  BarChart3,
  FolderOpen,
  Layers,
  Layout,
  Briefcase,
  CreditCard,
  Building2,
  Component,
  Bell,
  HardDrive,
  FileText,
  Key,
  Server,
} from 'lucide-react';
import { Suspense } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';

// =============================================================================
// Admin Navigation Items
// =============================================================================

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavItem[] = [
  { path: '/admin', label: 'Analytics', icon: <BarChart3 className="w-4 h-4" /> },
  { path: '/admin/users', label: 'Users', icon: <Users className="w-4 h-4" /> },
  { path: '/admin/projects', label: 'Projects', icon: <FolderOpen className="w-4 h-4" /> },
  { path: '/admin/designs', label: 'Designs', icon: <Layers className="w-4 h-4" /> },
  { path: '/admin/templates', label: 'Templates', icon: <Layout className="w-4 h-4" /> },
  { path: '/admin/jobs', label: 'Jobs', icon: <Briefcase className="w-4 h-4" /> },
  { path: '/admin/moderation', label: 'Moderation', icon: <AlertTriangle className="w-4 h-4" /> },
  { path: '/admin/subscriptions', label: 'Subscriptions', icon: <CreditCard className="w-4 h-4" /> },
  { path: '/admin/organizations', label: 'Organizations', icon: <Building2 className="w-4 h-4" /> },
  { path: '/admin/components', label: 'Components', icon: <Component className="w-4 h-4" /> },
  { path: '/admin/notifications', label: 'Notifications', icon: <Bell className="w-4 h-4" /> },
  { path: '/admin/storage', label: 'Storage', icon: <HardDrive className="w-4 h-4" /> },
  { path: '/admin/audit', label: 'Audit Logs', icon: <FileText className="w-4 h-4" /> },
  { path: '/admin/api-keys', label: 'API Keys', icon: <Key className="w-4 h-4" /> },
  { path: '/admin/system', label: 'System', icon: <Server className="w-4 h-4" /> },
];

// =============================================================================
// Loading Fallback
// =============================================================================

function AdminLoadingFallback() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  );
}

// =============================================================================
// Admin Layout Component
// =============================================================================

export function AdminLayout() {
  const location = useLocation();

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

        {/* Navigation Tabs */}
        <nav className="flex gap-1 mt-4 flex-wrap" aria-label="Admin navigation">
          {NAV_ITEMS.map((item) => {
            // For the root admin path, we need exact matching
            const isActive = item.path === '/admin' 
              ? location.pathname === '/admin'
              : location.pathname.startsWith(item.path);
            
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === '/admin'}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                {item.icon}
                {item.label}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        <Suspense fallback={<AdminLoadingFallback />}>
          <Outlet />
        </Suspense>
      </div>
    </div>
  );
}

export default AdminLayout;
