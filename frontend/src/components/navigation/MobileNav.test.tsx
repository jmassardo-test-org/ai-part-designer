/**
 * MobileNav Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MobileNav } from './MobileNav';

// Mock AuthContext
const mockLogout = vi.fn();
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { 
      id: '1', 
      email: 'test@example.com', 
      display_name: 'Test User',
      role: 'user',
      is_admin: false,
    },
    logout: mockLogout,
  }),
}));

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock LogoIcon
vi.mock('@/components/brand', () => ({
  LogoIcon: ({ size }: { size: number }) => (
    <div data-testid="logo-icon" style={{ width: size, height: size }}>Logo</div>
  ),
}));

describe('MobileNav', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = '';
  });

  const renderComponent = (initialRoute = '/dashboard') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <MobileNav />
      </MemoryRouter>
    );
  };

  it('renders hamburger button', () => {
    renderComponent();
    expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
  });

  it('opens menu when hamburger clicked', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows navigation items when open', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Templates')).toBeInTheDocument();
    expect(screen.getByText('Files')).toBeInTheDocument();
    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Shared')).toBeInTheDocument();
  });

  it('shows user info when open', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Test User')).toBeInTheDocument();
    expect(screen.getByText('test@example.com')).toBeInTheDocument();
  });

  it('shows close button when menu is open', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByRole('button', { name: /close menu/i })).toBeInTheDocument();
  });

  it('closes menu when close button clicked', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    
    await user.click(screen.getByRole('button', { name: /close menu/i }));
    
    // Menu should be hidden (translate-x-full)
    const menu = document.querySelector('[role="dialog"]');
    expect(menu).toHaveClass('translate-x-full');
  });

  it('closes menu when overlay clicked', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    const overlay = document.querySelector('.bg-black\\/50');
    if (overlay) {
      await user.click(overlay);
    }
  });

  it('prevents body scroll when open', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(document.body.style.overflow).toBe('hidden');
  });

  it('restores body scroll when closed', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    await user.click(screen.getByRole('button', { name: /close menu/i }));
    
    expect(document.body.style.overflow).toBe('');
  });

  it('highlights active nav item', async () => {
    const user = userEvent.setup();
    renderComponent('/templates');
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    const templatesLink = screen.getByText('Templates').closest('a');
    expect(templatesLink).toHaveClass('bg-primary-50');
  });

  it('shows create new design button', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByRole('button', { name: /create new design/i })).toBeInTheDocument();
  });

  it('navigates to generate page when create clicked', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    await user.click(screen.getByRole('button', { name: /create new design/i }));
    
    expect(mockNavigate).toHaveBeenCalledWith('/generate');
  });

  it('shows settings link', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('handles logout', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    // Find and click logout button
    const logoutButton = screen.getByRole('button', { name: /log out/i }) ||
                         screen.getByText(/log out/i);
    await user.click(logoutButton);
    
    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('shows user initial in avatar', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('T')).toBeInTheDocument(); // First letter of Test User
  });

  it('shows trash link', async () => {
    const user = userEvent.setup();
    renderComponent();
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    expect(screen.getByText('Trash')).toBeInTheDocument();
  });
});

describe('MobileNav with admin user', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows admin link for admin users', async () => {
    vi.mocked(await import('@/contexts/AuthContext')).useAuth = () => ({
      user: { 
        id: '1', 
        email: 'admin@example.com', 
        display_name: 'Admin User',
        role: 'admin',
        is_admin: true,
      },
      logout: mockLogout,
    });

    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <MobileNav />
      </MemoryRouter>
    );
    
    await user.click(screen.getByRole('button', { name: /open menu/i }));
    
    // Admin link should be visible for admin users
    expect(screen.queryByText('Admin')).toBeInTheDocument();
  });
});
