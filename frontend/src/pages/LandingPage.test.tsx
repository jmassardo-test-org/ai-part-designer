/**
 * Tests for LandingPage component.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { LandingPage } from './LandingPage';

// Mock brand components
vi.mock('@/components/brand', () => ({
  LogoLight: () => <div data-testid="logo-light">Logo</div>,
  LogoIcon: () => <div data-testid="logo-icon">Icon</div>,
}));

const renderLandingPage = () => {
  return render(
    <BrowserRouter>
      <LandingPage />
    </BrowserRouter>
  );
};

describe('LandingPage', () => {
  it('renders the landing page', () => {
    renderLandingPage();

    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
  });

  it('displays the main headline', () => {
    renderLandingPage();

    expect(screen.getByText(/design 3d parts/i)).toBeInTheDocument();
    // "natural language" appears in heading and feature description
    expect(screen.getAllByText(/natural language/i).length).toBeGreaterThanOrEqual(1);
  });

  it('shows sign in link in header', () => {
    renderLandingPage();

    expect(screen.getByRole('link', { name: /sign in/i })).toHaveAttribute('href', '/login');
  });

  it('shows get started button in header', () => {
    renderLandingPage();

    const getStartedLinks = screen.getAllByRole('link', { name: /get started/i });
    expect(getStartedLinks[0]).toHaveAttribute('href', '/register');
  });

  it('displays hero section with CTA', () => {
    renderLandingPage();

    expect(screen.getByRole('link', { name: /start designing free/i })).toHaveAttribute('href', '/register');
  });

  it('shows watch demo button', () => {
    renderLandingPage();

    expect(screen.getByRole('button', { name: /watch demo/i })).toBeInTheDocument();
  });

  it('displays how it works section', () => {
    renderLandingPage();

    expect(screen.getByRole('heading', { name: /how it works/i })).toBeInTheDocument();
  });

  it('shows the three feature steps', () => {
    renderLandingPage();

    expect(screen.getByText(/describe your part/i)).toBeInTheDocument();
    expect(screen.getByText(/preview & customize/i)).toBeInTheDocument();
    expect(screen.getByText(/export & manufacture/i)).toBeInTheDocument();
  });

  it('displays feature descriptions', () => {
    renderLandingPage();

    expect(screen.getByText(/natural language to describe dimensions/i)).toBeInTheDocument();
    expect(screen.getByText(/rendered in 3d/i)).toBeInTheDocument();
    expect(screen.getByText(/step files for cnc/i)).toBeInTheDocument();
  });

  it('shows CTA section', () => {
    renderLandingPage();

    expect(screen.getByRole('heading', { name: /ready to start designing/i })).toBeInTheDocument();
  });

  it('displays create free account button in CTA', () => {
    renderLandingPage();

    expect(screen.getByRole('link', { name: /create free account/i })).toHaveAttribute('href', '/register');
  });

  it('shows footer with company name', () => {
    renderLandingPage();

    // "AssemblematicAI" appears in footer name and copyright
    expect(screen.getAllByText(/assemblematicai/i).length).toBeGreaterThanOrEqual(1);
  });

  it('displays footer links', () => {
    renderLandingPage();

    expect(screen.getByRole('link', { name: /terms/i })).toHaveAttribute('href', '/terms');
    expect(screen.getByRole('link', { name: /privacy/i })).toHaveAttribute('href', '/privacy');
    expect(screen.getByRole('link', { name: /documentation/i })).toHaveAttribute('href', '/docs');
    expect(screen.getByRole('link', { name: /contact/i })).toHaveAttribute('href', '/contact');
  });

  it('shows copyright notice', () => {
    renderLandingPage();

    expect(screen.getByText(/© 2026 assemblematicai/i)).toBeInTheDocument();
  });

  it('displays logo in header', () => {
    renderLandingPage();

    expect(screen.getByTestId('logo-light')).toBeInTheDocument();
  });

  it('displays logo in footer', () => {
    renderLandingPage();

    expect(screen.getByTestId('logo-icon')).toBeInTheDocument();
  });

  it('has proper heading hierarchy', () => {
    renderLandingPage();

    const headings = screen.getAllByRole('heading');
    expect(headings.length).toBeGreaterThan(0);

    // First heading should be h1
    expect(headings[0].tagName).toBe('H1');
  });

  it('renders feature icons', () => {
    renderLandingPage();

    // Feature section should have cards with icons
    const featureCards = document.querySelectorAll('.bg-white.rounded-xl');
    expect(featureCards.length).toBeGreaterThanOrEqual(3);
  });

  it('has accessible navigation', () => {
    renderLandingPage();

    const header = screen.getByRole('banner');
    expect(header).toBeInTheDocument();
  });
});
