/**
 * Main layout component.
 *
 * Layout for authenticated pages with header and navigation.
 */

import { User, LogOut, Settings, Shield, Plus, Trash2, WifiOff, RefreshCw } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { LogoLight, LogoIcon } from '@/components/brand';
import { JobQueue } from '@/components/jobs';
import { MobileNav } from '@/components/navigation';
import { NotificationCenter } from '@/components/notifications';
import { SkipLink } from '@/components/ui';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { useAuth } from '@/contexts/AuthContext';
import { useWebSocket } from '@/contexts/WebSocketContext';

export function MainLayout() {
  const { user, logout } = useAuth();
  const { connected, fallbackMode, reconnect } = useWebSocket();
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsMenuOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Check if user is admin
  const isAdmin = user?.role === 'admin' || user?.is_admin;

  // Check if a nav link is active
  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-industrial-bg-primary">
      {/* Skip Link for accessibility */}
      <SkipLink />

      {/* Header */}
      <header className="bg-white dark:bg-industrial-bg-secondary border-b border-gray-200 dark:border-industrial-border-DEFAULT">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Mobile Nav (hamburger menu) */}
            <div className="md:hidden">
              <MobileNav />
            </div>

            {/* Logo */}
            <Link to="/dashboard" className="flex items-center gap-2" data-tour="logo">
              <LogoLight size="md" showText className="hidden sm:flex" />
              <LogoIcon size={32} className="sm:hidden" />
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-6" data-tour="navigation">
              <Link
                to="/dashboard"
                className={`font-medium ${isActive('/dashboard') ? 'text-primary-600 dark:text-accent-400' : 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'}`}
              >
                Dashboard
              </Link>
              <Link
                to="/marketplace"
                className={`font-medium ${isActive('/marketplace') ? 'text-primary-600 dark:text-accent-400' : 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'}`}
                data-tour="marketplace"
              >
                Marketplace
              </Link>
              <Link
                to="/starters"
                className={`font-medium ${isActive('/starters') ? 'text-primary-600 dark:text-accent-400' : 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'}`}
                data-tour="starters"
              >
                Starters
              </Link>
              <Link
                to="/projects"
                className={`font-medium ${isActive('/projects') ? 'text-primary-600 dark:text-accent-400' : 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'}`}
              >
                Projects
              </Link>
              <Link
                to="/lists"
                className={`font-medium ${isActive('/lists') ? 'text-primary-600 dark:text-accent-400' : 'text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white'}`}
                data-tour="lists"
              >
                My Lists
              </Link>
            </nav>

            {/* Right side: Theme, Notifications, Jobs, User */}
            <div className="flex items-center gap-3">
              {/* Connection Status (only show when disconnected/fallback) */}
              {fallbackMode && (
                <button
                  onClick={reconnect}
                  className="flex items-center gap-1.5 px-2 py-1 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-full hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors"
                  title="Real-time updates unavailable. Click to retry."
                >
                  <WifiOff className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Offline</span>
                  <RefreshCw className="h-3 w-3" />
                </button>
              )}

              {/* Theme Toggle */}
              <ThemeToggle showDropdown size="sm" />

              {/* Notifications */}
              <NotificationCenter />

              {/* Job Queue */}
              <JobQueue />

              {/* User Menu */}
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                  className="flex items-center gap-2 text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 rounded-full"
                  aria-expanded={isMenuOpen}
                  aria-haspopup="true"
                  data-tour="user-menu"
                >
                  <div className="h-8 w-8 rounded-full bg-primary-100 dark:bg-primary-900 flex items-center justify-center">
                    <User className="h-5 w-5 text-primary-600 dark:text-primary-400" />
                  </div>
                  <span className="hidden sm:block font-medium">
                    {user?.display_name || 'User'}
                  </span>
                </button>

                {/* Dropdown Menu */}
                {isMenuOpen && (
                  <div 
                    className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-100 dark:border-gray-700 py-1 z-50"
                    role="menu"
                    aria-orientation="vertical"
                  >
                    <div className="px-4 py-2 border-b border-gray-100 dark:border-gray-700">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">{user?.display_name}</p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{user?.email}</p>
                    </div>
                    <Link
                      to="/settings"
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 focus:outline-none"
                      onClick={() => setIsMenuOpen(false)}
                      role="menuitem"
                    >
                      <Settings className="h-4 w-4" />
                      Settings
                    </Link>
                    <Link
                      to="/trash"
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 focus:outline-none"
                      onClick={() => setIsMenuOpen(false)}
                      role="menuitem"
                    >
                      <Trash2 className="h-4 w-4" />
                      Trash
                    </Link>
                    {isAdmin && (
                      <Link
                        to="/admin"
                        className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 focus:outline-none"
                        onClick={() => setIsMenuOpen(false)}
                        role="menuitem"
                      >
                        <Shield className="h-4 w-4" />
                        Admin
                      </Link>
                    )}
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:bg-gray-100 dark:focus:bg-gray-700 focus:outline-none"
                      role="menuitem"
                    >
                      <LogOut className="h-4 w-4" />
                      Log out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main id="main-content" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
