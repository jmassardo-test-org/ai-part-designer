/**
 * Mobile Navigation Component - Hamburger menu for mobile devices.
 *
 * Features:
 * - Hamburger menu toggle
 * - Full-screen overlay
 * - Touch-friendly
 * - Accessible
 */

import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Menu,
  X,
  Home,
  LayoutTemplate,
  FileBox,
  FolderOpen,
  Users,
  Settings,
  LogOut,
  Shield,
  Wand2,
  Trash2,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { LogoIcon } from '@/components/brand';

// =============================================================================
// Types
// =============================================================================

interface NavItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
}

// =============================================================================
// Navigation Items
// =============================================================================

const NAV_ITEMS: NavItem[] = [
  { path: '/dashboard', label: 'Dashboard', icon: Home },
  { path: '/templates', label: 'Templates', icon: LayoutTemplate },
  { path: '/files', label: 'Files', icon: FileBox },
  { path: '/projects', label: 'Projects', icon: FolderOpen },
  { path: '/shared', label: 'Shared', icon: Users },
  { path: '/trash', label: 'Trash', icon: Trash2 },
];

const SECONDARY_ITEMS: NavItem[] = [
  { path: '/settings', label: 'Settings', icon: Settings },
  { path: '/admin', label: 'Admin', icon: Shield, adminOnly: true },
];

// =============================================================================
// Mobile Navigation Component
// =============================================================================

export function MobileNav() {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  // Close menu on route change
  useEffect(() => {
    setIsOpen(false);
  }, [location.pathname]);

  // Prevent body scroll when menu is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  // Check if user is admin
  const isAdmin = user?.role === 'admin' || user?.is_admin;

  // Handle logout
  const handleLogout = async () => {
    await logout();
    navigate('/login');
    setIsOpen(false);
  };

  // Check if path is active
  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <>
      {/* Hamburger Button */}
      <button
        onClick={() => setIsOpen(true)}
        className="md:hidden p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
        aria-label="Open menu"
        aria-expanded={isOpen}
      >
        <Menu className="w-6 h-6" />
      </button>

      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Slide-out Menu */}
      <div
        className={`
          fixed inset-y-0 right-0 w-80 max-w-full bg-white z-50 transform transition-transform duration-300 ease-in-out md:hidden
          ${isOpen ? 'translate-x-0' : 'translate-x-full'}
        `}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile navigation"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <LogoIcon size={24} />
            <span className="font-bold">AssemblematicAI</span>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg"
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* User Info */}
        <div className="p-4 border-b bg-gray-50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
              <span className="text-primary-600 font-medium">
                {user?.display_name?.charAt(0) || user?.email?.charAt(0) || 'U'}
              </span>
            </div>
            <div>
              <p className="font-medium text-gray-900">{user?.display_name || 'User'}</p>
              <p className="text-sm text-gray-500 truncate">{user?.email}</p>
            </div>
          </div>
        </div>

        {/* Create Button */}
        <div className="p-4 border-b">
          <button
            onClick={() => {
              navigate('/generate');
              setIsOpen(false);
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 font-medium"
          >
            <Wand2 className="w-5 h-5" />
            Create New Design
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 overflow-y-auto py-4">
          <ul className="space-y-1 px-2">
            {NAV_ITEMS.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg text-base font-medium transition-colors
                    ${isActive(item.path)
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100'
                    }
                  `}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>

          {/* Divider */}
          <div className="my-4 border-t" />

          {/* Secondary Items */}
          <ul className="space-y-1 px-2">
            {SECONDARY_ITEMS.filter(item => !item.adminOnly || isAdmin).map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`
                    flex items-center gap-3 px-4 py-3 rounded-lg text-base font-medium transition-colors
                    ${isActive(item.path)
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-100'
                    }
                  `}
                >
                  <item.icon className="w-5 h-5" />
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t">
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 w-full px-4 py-3 text-gray-700 hover:bg-gray-100 rounded-lg font-medium"
          >
            <LogOut className="w-5 h-5" />
            Log out
          </button>
        </div>
      </div>
    </>
  );
}
