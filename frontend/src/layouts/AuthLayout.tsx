/**
 * Auth layout component.
 *
 * Centered card layout for authentication pages.
 */

import { Outlet, Link } from 'react-router-dom';
import { LogoLight } from '@/components/brand';

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      {/* Logo */}
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <Link to="/" className="flex items-center justify-center">
          <LogoLight size="lg" />
        </Link>
      </div>

      {/* Card */}
      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10 border border-gray-100">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
