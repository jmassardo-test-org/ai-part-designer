/**
 * CheckoutCancelPage Tests.
 *
 * Tests for the checkout cancel page.
 */

import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect } from 'vitest';
import { CheckoutCancelPage } from './CheckoutCancelPage';

const renderPage = () => {
  return render(
    <MemoryRouter>
      <CheckoutCancelPage />
    </MemoryRouter>
  );
};

describe('CheckoutCancelPage', () => {
  describe('Cancel Message', () => {
    it('renders checkout canceled heading', () => {
      renderPage();
      expect(screen.getByText('Checkout Canceled')).toBeInTheDocument();
    });

    it('shows reassuring message about not being charged', () => {
      renderPage();
      expect(screen.getByText(/no worries/i)).toBeInTheDocument();
      expect(screen.getByText(/haven't been charged/i)).toBeInTheDocument();
    });

    it('mentions account remains on free plan', () => {
      renderPage();
      expect(screen.getByText(/free plan/i)).toBeInTheDocument();
    });
  });

  describe('Ready When You Are Section', () => {
    it('displays info about upgrading later', () => {
      renderPage();
      expect(screen.getByText('Ready when you are')).toBeInTheDocument();
    });

    it('mentions premium features', () => {
      renderPage();
      expect(screen.getByText(/unlimited generations/i)).toBeInTheDocument();
      expect(screen.getByText(/priority processing/i)).toBeInTheDocument();
      expect(screen.getByText(/STEP exports/i)).toBeInTheDocument();
    });
  });

  describe('Navigation CTAs', () => {
    it('shows View Plans Again button', () => {
      renderPage();
      const pricingLink = screen.getByRole('link', { name: /view plans again/i });
      expect(pricingLink).toBeInTheDocument();
      expect(pricingLink).toHaveAttribute('href', '/pricing');
    });

    it('shows Back to Dashboard button', () => {
      renderPage();
      const dashboardLink = screen.getByRole('link', { name: /back to dashboard/i });
      expect(dashboardLink).toBeInTheDocument();
      expect(dashboardLink).toHaveAttribute('href', '/dashboard');
    });
  });

  describe('Support Link', () => {
    it('displays contact support link', () => {
      renderPage();
      const supportLink = screen.getByRole('link', { name: /contact support/i });
      expect(supportLink).toBeInTheDocument();
      expect(supportLink).toHaveAttribute('href', 'mailto:support@aipartdesigner.com');
    });
  });
});
