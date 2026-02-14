/**
 * ExplodeToolbar Component Tests
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ExplodeState } from '../../hooks/useExplodedView';
import { ExplodeToolbar } from './ExplodeToolbar';

// =============================================================================
// Test Setup
// =============================================================================

const defaultProps = {
  state: 'collapsed' as ExplodeState,
  isAnimating: false,
  distanceMultiplier: 1.0,
  onToggle: vi.fn(),
  onDistanceChange: vi.fn(),
};

function renderToolbar(overrides?: Partial<typeof defaultProps>) {
  return render(<ExplodeToolbar {...defaultProps} {...overrides} />);
}

// =============================================================================
// Tests
// =============================================================================

describe('ExplodeToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  describe('rendering', () => {
    it('renders expand icon when collapsed', () => {
      renderToolbar({ state: 'collapsed' });
      
      // The button should have "Exploded view" in title
      const button = screen.getByRole('button', { name: /exploded view/i });
      expect(button).toBeInTheDocument();
    });

    it('renders shrink icon when exploded', () => {
      renderToolbar({ state: 'exploded' });
      
      // The button should have "Collapse view" in title
      const button = screen.getByRole('button', { name: /collapse view/i });
      expect(button).toBeInTheDocument();
    });

    it('renders shrink icon when exploding (animating)', () => {
      renderToolbar({ state: 'exploding', isAnimating: true });
      
      const button = screen.getByRole('button', { name: /collapse view/i });
      expect(button).toBeInTheDocument();
    });

    it('applies active styling when exploded', () => {
      renderToolbar({ state: 'exploded' });
      
      const button = screen.getByRole('button', { name: /collapse view/i });
      expect(button).toHaveClass('bg-primary-600');
    });

    it('applies inactive styling when collapsed', () => {
      renderToolbar({ state: 'collapsed' });
      
      const button = screen.getByRole('button', { name: /exploded view/i });
      expect(button).toHaveClass('text-gray-700');
    });

    it('disables button when animating', () => {
      renderToolbar({ state: 'exploding', isAnimating: true });
      
      const button = screen.getByRole('button', { name: /collapse view/i });
      expect(button).toBeDisabled();
    });
  });

  // ---------------------------------------------------------------------------
  // Toggle Behavior
  // ---------------------------------------------------------------------------

  describe('toggle behavior', () => {
    it('calls onToggle when button is clicked', () => {
      const onToggle = vi.fn();
      renderToolbar({ onToggle });
      
      const button = screen.getByRole('button', { name: /exploded view/i });
      fireEvent.click(button);
      
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('does not call onToggle when disabled', () => {
      const onToggle = vi.fn();
      renderToolbar({ onToggle, isAnimating: true, state: 'exploding' });
      
      const button = screen.getByRole('button', { name: /collapse view/i });
      fireEvent.click(button);
      
      expect(onToggle).not.toHaveBeenCalled();
    });

    it('has correct aria-pressed attribute when collapsed', () => {
      renderToolbar({ state: 'collapsed' });
      
      const button = screen.getByRole('button', { name: /exploded view/i });
      expect(button).toHaveAttribute('aria-pressed', 'false');
    });

    it('has correct aria-pressed attribute when exploded', () => {
      renderToolbar({ state: 'exploded' });
      
      const button = screen.getByRole('button', { name: /collapse view/i });
      expect(button).toHaveAttribute('aria-pressed', 'true');
    });
  });

  // ---------------------------------------------------------------------------
  // Settings Popover
  // ---------------------------------------------------------------------------

  describe('settings popover', () => {
    it('opens popover when settings button is clicked', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Explosion Distance')).toBeInTheDocument();
    });

    it('closes popover when settings button is clicked again', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      
      fireEvent.click(settingsButton);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('displays slider with correct value', () => {
      renderToolbar({ distanceMultiplier: 1.5 });
      
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      
      const slider = screen.getByRole('slider');
      expect(slider).toHaveValue('1.5');
    });

    it('calls onDistanceChange when slider is moved', () => {
      const onDistanceChange = vi.fn();
      renderToolbar({ onDistanceChange, distanceMultiplier: 1.0 });
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      
      // Change slider
      const slider = screen.getByRole('slider');
      fireEvent.change(slider, { target: { value: '2.0' } });
      
      expect(onDistanceChange).toHaveBeenCalledWith(2.0);
    });

    it('displays formatted multiplier value', () => {
      renderToolbar({ distanceMultiplier: 1.5 });
      
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByText('1.50x')).toBeInTheDocument();
    });

    it('displays min and max labels', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByText('0.50x')).toBeInTheDocument();
      expect(screen.getByText('3.00x')).toBeInTheDocument();
    });

    it('has correct aria attributes on settings button', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      expect(settingsButton).toHaveAttribute('aria-haspopup', 'dialog');
      expect(settingsButton).toHaveAttribute('aria-expanded', 'false');
      
      fireEvent.click(settingsButton);
      expect(settingsButton).toHaveAttribute('aria-expanded', 'true');
    });

    it('slider has correct accessibility attributes', () => {
      renderToolbar({ distanceMultiplier: 2.0 });
      
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      
      const slider = screen.getByRole('slider');
      expect(slider).toHaveAttribute('aria-valuenow', '2');
      expect(slider).toHaveAttribute('aria-valuemin', '0.5');
      expect(slider).toHaveAttribute('aria-valuemax', '3');
    });
  });

  // ---------------------------------------------------------------------------
  // Click Outside
  // ---------------------------------------------------------------------------

  describe('click outside', () => {
    it('closes popover when clicking outside', () => {
      renderToolbar();
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      
      // Click outside
      fireEvent.mouseDown(document.body);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('does not close popover when clicking inside', () => {
      renderToolbar();
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /explosion settings/i });
      fireEvent.click(settingsButton);
      
      // Click inside popover
      const dialog = screen.getByRole('dialog');
      fireEvent.mouseDown(dialog);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // State Variations
  // ---------------------------------------------------------------------------

  describe('state variations', () => {
    const states: ExplodeState[] = ['collapsed', 'exploding', 'exploded', 'collapsing'];

    states.forEach((state) => {
      it(`renders correctly in ${state} state`, () => {
        expect(() => renderToolbar({ state })).not.toThrow();
      });
    });

    it('shows active styling during collapsing', () => {
      renderToolbar({ state: 'collapsing', isAnimating: true });
      
      // Collapsing should show shrink icon (going to collapsed)
      const button = screen.getByRole('button', { name: /exploded view/i });
      expect(button).toBeInTheDocument();
    });
  });
});
