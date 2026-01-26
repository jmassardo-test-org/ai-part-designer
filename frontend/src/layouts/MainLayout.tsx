/**
 * Main layout component.
 *
 * Layout for authenticated pages with header and navigation.
 */

import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom';
import { User, LogOut, Settings, Shield, Plus, Trash2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { LogoLight, LogoIcon } from '@/components/brand';
import { JobQueue } from '@/components/jobs';
import { MobileNav } from '@/components/navigation';
import { SkipLink } from '@/components/ui';
import { useState, useRef, useEffect } from 'react';

export function MainLayout() {
  const { user, logout } = useAuth();
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
    <div className="min-h-screen bg-gray-50">
      {/* Skip Link for accessibility */}
      <SkipLink />

      {/* Header */}
      <header className="bg-white border-b border-gray-200">
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
                className={`font-medium ${isActive('/dashboard') ? 'text-primary-600' : 'text-gray-600 hover:text-gray-900'}`}
              >
                Dashboard
              </Link>
              <Link
                to="/templates"
                className={`font-medium ${isActive('/templates') ? 'text-primary-600' : 'text-gray-600 hover:text-gray-900'}`}
                data-tour="templates"
              >
                Templates
              </Link>
              <Link
                to="/files"
                className={`font-medium ${isActive('/files') ? 'text-primary-600' : 'text-gray-600 hover:text-gray-900'}`}
              >
                Files
              </Link>
              <Link
                to="/projects"
                className={`font-medium ${isActive('/projects') ? 'text-primary-600' : 'text-gray-600 hover:text-gray-900'}`}
              >
                Projects
              </Link>
              <Link
                to="/shared"
                className={`font-medium ${isActive('/shared') ? 'text-primary-600' : 'text-gray-600 hover:text-gray-900'}`}
                data-tour="shared"
              >
                Shared
              </Link>
            </nav>

            {/* Right side: Create, Jobs, User */}
            <div className="flex items-center gap-3">
              {/* Create Button */}
              <button
                onClick={() => navigate('/create')}
                className="hidden sm:flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
                data-tour="create"
              >
                <Plus className="w-4 h-4" />
                Create
              </button>

              {/* Job Queue */}
              <JobQueue />

              {/* User Menu */}
              <div className="relative" ref={menuRef}>
                <button
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                  className="flex items-center gap-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded-full"
                  aria-expanded={isMenuOpen}
                  aria-haspopup="true"
                  data-tour="user-menu"
                >
                  <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                    <User className="h-5 w-5 text-primary-600" />
                  </div>
                  <span className="hidden sm:block font-medium">
                    {user?.display_name || 'User'}
                  </span>
                </button>

                {/* Dropdown Menu */}
                {isMenuOpen && (
                  <div 
                    className="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg border border-gray-100 py-1 z-50"
                    role="menu"
                    aria-orientation="vertical"
                  >
                    <div className="px-4 py-2 border-b border-gray-100">
                      <p className="text-sm font-medium text-gray-900">{user?.display_name}</p>
                      <p className="text-sm text-gray-500 truncate">{user?.email}</p>
                    </div>
                    <Link
                      to="/settings"
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:bg-gray-100 focus:outline-none"
                      onClick={() => setIsMenuOpen(false)}
                      role="menuitem"
                    >
                      <Settings className="h-4 w-4" />
                      Settings
                    </Link>
                    <Link
                      to="/trash"
                      className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:bg-gray-100 focus:outline-none"
                      onClick={() => setIsMenuOpen(false)}
                      role="menuitem"
                    >
                      <Trash2 className="h-4 w-4" />
                      Trash
                    </Link>
                    {isAdmin && (
                      <Link
                        to="/admin"
                        className="flex items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:bg-gray-100 focus:outline-none"
                        onClick={() => setIsMenuOpen(false)}
                        role="menuitem"
                      >
                        <Shield className="h-4 w-4" />
                        Admin
                      </Link>
                    )}
                    <button
                      onClick={handleLogout}
                      className="flex items-center gap-2 w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:bg-gray-100 focus:outline-none"
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
