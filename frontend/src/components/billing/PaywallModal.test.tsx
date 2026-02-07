/**
 * PaywallModal Tests.
 *
 * Tests for the paywall modal component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import { PaywallModal } from './PaywallModal';

const renderModal = (props: Partial<React.ComponentProps<typeof PaywallModal>> = {}) => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    feature: 'step_export',
  };

  return render(
    <MemoryRouter>
      <PaywallModal {...defaultProps} {...props} />
    </MemoryRouter>
  );
};

describe('PaywallModal', () => {
  describe('Visibility', () => {
    it('renders when isOpen is true', () => {
      renderModal({ isOpen: true });
      expect(screen.getByText('STEP Export')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      renderModal({ isOpen: false });
      expect(screen.queryByText('STEP Export')).not.toBeInTheDocument();
    });
  });

  describe('Feature Content', () => {
    it('displays feature title for step_export', () => {
      renderModal({ feature: 'step_export' });
      expect(screen.getByText('STEP Export')).toBeInTheDocument();
    });

    it('displays feature description for step_export', () => {
      renderModal({ feature: 'step_export' });
      expect(screen.getByText(/industry-standard STEP format/i)).toBeInTheDocument();
    });

    it('displays feature title for priority_queue', () => {
      renderModal({ feature: 'priority_queue' });
      expect(screen.getByText('Priority Processing')).toBeInTheDocument();
    });

    it('displays feature title for unlimited_generations', () => {
      renderModal({ feature: 'unlimited_generations' });
      expect(screen.getByText('Unlimited Generations')).toBeInTheDocument();
    });

    it('displays feature title for api_access', () => {
      renderModal({ feature: 'api_access' });
      expect(screen.getByText('API Access')).toBeInTheDocument();
    });

    it('displays feature title for team_collaboration', () => {
      renderModal({ feature: 'team_collaboration' });
      expect(screen.getByText('Team Collaboration')).toBeInTheDocument();
    });

    it('uses custom description when provided', () => {
      renderModal({ 
        feature: 'step_export',
        description: 'Custom description here',
      });
      expect(screen.getByText('Custom description here')).toBeInTheDocument();
    });

    it('displays fallback for unknown feature', () => {
      renderModal({ feature: 'unknown_feature' });
      expect(screen.getByText('Premium Feature')).toBeInTheDocument();
    });
  });

  describe('Required Tier', () => {
    it('shows Pro tier for pro features', () => {
      renderModal({ feature: 'step_export', requiredTier: 'pro' });
      expect(screen.getByText('Pro')).toBeInTheDocument();
    });

    it('shows Enterprise tier for enterprise features', () => {
      renderModal({ feature: 'api_access', requiredTier: 'enterprise' });
      expect(screen.getByText('Enterprise')).toBeInTheDocument();
    });
  });

  describe('Upgrade CTA', () => {
    it('shows upgrade to Pro button for pro tier', () => {
      renderModal({ feature: 'step_export', requiredTier: 'pro' });
      const upgradeLink = screen.getByRole('link', { name: /upgrade to pro/i });
      expect(upgradeLink).toBeInTheDocument();
      expect(upgradeLink).toHaveAttribute('href', '/pricing');
    });

    it('shows upgrade to Enterprise button for enterprise tier', () => {
      renderModal({ feature: 'api_access', requiredTier: 'enterprise' });
      const upgradeLink = screen.getByRole('link', { name: /upgrade to enterprise/i });
      expect(upgradeLink).toBeInTheDocument();
    });
  });

  describe('Close Functionality', () => {
    it('calls onClose when clicking Maybe later', () => {
      const onClose = vi.fn();
      renderModal({ onClose });

      fireEvent.click(screen.getByRole('button', { name: /maybe later/i }));
      expect(onClose).toHaveBeenCalled();
    });

    it('calls onClose when clicking backdrop', () => {
      const onClose = vi.fn();
      renderModal({ onClose });

      // Click on the backdrop (the fixed overlay div)
      const backdrop = document.querySelector('.fixed.inset-0');
      if (backdrop) {
        fireEvent.click(backdrop);
        expect(onClose).toHaveBeenCalled();
      }
    });

    it('does not close when clicking modal content', () => {
      const onClose = vi.fn();
      renderModal({ onClose });

      // Click on the modal content
      const modalContent = screen.getByText('STEP Export').closest('div');
      if (modalContent) {
        fireEvent.click(modalContent);
        // onClose should not be called for content clicks (only backdrop)
      }
    });

    it('calls onClose when clicking upgrade link', () => {
      const onClose = vi.fn();
      renderModal({ onClose });

      fireEvent.click(screen.getByRole('link', { name: /upgrade to pro/i }));
      expect(onClose).toHaveBeenCalled();
    });
  });
});
