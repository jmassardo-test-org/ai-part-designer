/**
 * AuthLayout Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AuthLayout } from './AuthLayout';

// Mock Logo component
vi.mock('@/components/brand', () => ({
  LogoLight: ({ size }: { size: string }) => (
    <div data-testid="logo" data-size={size}>Logo</div>
  ),
}));

describe('AuthLayout', () => {
  const renderWithRouter = (initialRoute = '/login') => {
    return render(
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route element={<AuthLayout />}>
            <Route path="/login" element={<div data-testid="login-content">Login Form</div>} />
            <Route path="/register" element={<div data-testid="register-content">Register Form</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );
  };

  it('renders outlet content', () => {
    renderWithRouter('/login');
    
    expect(screen.getByTestId('login-content')).toBeInTheDocument();
  });

  it('renders logo', () => {
    renderWithRouter();
    
    expect(screen.getByTestId('logo')).toBeInTheDocument();
  });

  it('logo links to home', () => {
    renderWithRouter();
    
    const logoLink = screen.getByTestId('logo').closest('a');
    expect(logoLink).toHaveAttribute('href', '/');
  });

  it('renders logo with large size', () => {
    renderWithRouter();
    
    expect(screen.getByTestId('logo')).toHaveAttribute('data-size', 'lg');
  });

  it('centers content vertically', () => {
    const { container } = renderWithRouter();
    
    const mainWrapper = container.firstChild;
    expect(mainWrapper).toHaveClass('min-h-screen');
    expect(mainWrapper).toHaveClass('flex');
    expect(mainWrapper).toHaveClass('flex-col');
    expect(mainWrapper).toHaveClass('justify-center');
  });

  it('has gray background', () => {
    const { container } = renderWithRouter();
    
    const mainWrapper = container.firstChild;
    expect(mainWrapper).toHaveClass('bg-gray-50');
  });

  it('renders card container', () => {
    const { container } = renderWithRouter();
    
    const card = container.querySelector('.bg-white');
    expect(card).toBeInTheDocument();
  });

  it('card has shadow', () => {
    const { container } = renderWithRouter();
    
    const card = container.querySelector('.shadow-sm');
    expect(card).toBeInTheDocument();
  });

  it('card has border', () => {
    const { container } = renderWithRouter();
    
    const card = container.querySelector('.border');
    expect(card).toBeInTheDocument();
  });

  it('card is rounded on larger screens', () => {
    const { container } = renderWithRouter();
    
    const card = container.querySelector('.sm\\:rounded-lg');
    expect(card).toBeInTheDocument();
  });

  it('renders different routes', () => {
    renderWithRouter('/register');
    
    expect(screen.getByTestId('register-content')).toBeInTheDocument();
  });

  it('has responsive padding', () => {
    const { container } = renderWithRouter();
    
    const outerWrapper = container.querySelector('.py-12');
    expect(outerWrapper).toBeInTheDocument();
  });

  it('constrains content width', () => {
    const { container } = renderWithRouter();
    
    const constrainedSection = container.querySelector('.sm\\:max-w-md');
    expect(constrainedSection).toBeInTheDocument();
  });
});
