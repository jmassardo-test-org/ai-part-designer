/**
 * Auth layout component.
 *
 * Centered card layout for authentication pages.
 * Supports both light and dark themes.
 */

import { Outlet, Link } from 'react-router-dom';
import { LogoLight } from '@/components/brand';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-industrial-bg-primary flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative">
      {/* Theme Toggle - Top Right */}
      <div className="absolute top-4 right-4">
        <ThemeToggle size="sm" showDropdown />
      </div>
      
      {/* Logo */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link to="/" className="flex items-center justify-center">
          <LogoLight size="lg" />
        </Link>
      </div>

      {/* Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white dark:bg-industrial-bg-secondary py-8 px-4 shadow-sm sm:rounded-lg sm:px-10 border border-gray-100 dark:border-industrial-border-DEFAULT">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
