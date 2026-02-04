/**
 * AdminRoute Component Tests
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AdminRoute } from './AdminRoute';

// Mock AuthContext
const mockUseAuth = vi.fn();
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

describe('AdminRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithRouter = (initialRoute = '/admin') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/admin" element={<AdminRoute />}>
            <Route index element={<div data-testid="admin-content">Admin Content</div>} />
          </Route>
          <Route path="/login" element={<div data-testid="login-page">Login Page</div>} />
          <Route path="/dashboard" element={<div data-testid="dashboard-page">Dashboard</div>} />
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders loading state while checking auth', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isLoading: true,
      isAuthenticated: false,
    });

    renderWithRouter();
    
    // Should show loading spinner (has animate-spin class)
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('redirects to login when not authenticated', () => {
    mockUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      isAuthenticated: false,
    });

    renderWithRouter();
    
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  it('shows access denied for non-admin users and redirects to dashboard', async () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'user@example.com', role: 'user', is_admin: false },
      isLoading: false,
      isAuthenticated: true,
    });

    renderWithRouter();
    
    // When non-admin tries to access, they get redirected to dashboard
    // The Navigate component will redirect before showing access denied
    expect(screen.getByTestId('dashboard-page')).toBeInTheDocument();
  });

  it('renders outlet for admin users with role=admin', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'admin@example.com', role: 'admin', is_admin: false },
      isLoading: false,
      isAuthenticated: true,
    });

    renderWithRouter();
    
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });

  it('renders outlet for admin users with is_admin=true', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'admin@example.com', role: 'user', is_admin: true },
      isLoading: false,
      isAuthenticated: true,
    });

    renderWithRouter();
    
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });

  it('handles both admin indicators', () => {
    mockUseAuth.mockReturnValue({
      user: { id: '1', email: 'admin@example.com', role: 'admin', is_admin: true },
      isLoading: false,
      isAuthenticated: true,
    });

    renderWithRouter();
    
    expect(screen.getByTestId('admin-content')).toBeInTheDocument();
  });
});
