/**
 * AlignmentToolbar Component Tests
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { AlignmentSettings } from '../../hooks/useAlignmentGuides';
import { AlignmentToolbar } from './AlignmentToolbar';

// =============================================================================
// Test Setup
// =============================================================================

const defaultSettings: AlignmentSettings = {
  enableEdgeAlignment: true,
  enableCenterAlignment: true,
  enableFaceAlignment: true,
  snapDistance: 10,
  snapThreshold: 5,
  maxGuides: 6,
};

const defaultProps = {
  enabled: true,
  onToggle: vi.fn(),
  settings: defaultSettings,
  onSettingsChange: vi.fn(),
};

function renderToolbar(overrides?: Partial<typeof defaultProps>) {
  return render(<AlignmentToolbar {...defaultProps} {...overrides} />);
}

// =============================================================================
// Tests
// =============================================================================

describe('AlignmentToolbar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------------------------------------------------------------------------
  // Rendering
  // ---------------------------------------------------------------------------

  describe('rendering', () => {
    it('renders magnet button', () => {
      renderToolbar();
      
      const button = screen.getByRole('button', { name: /alignment guides/i });
      expect(button).toBeInTheDocument();
    });

    it('applies active styling when enabled', () => {
      renderToolbar({ enabled: true });
      
      const button = screen.getByRole('button', { name: /disable alignment guides/i });
      expect(button).toHaveClass('bg-primary-600');
    });

    it('applies inactive styling when disabled', () => {
      renderToolbar({ enabled: false });
      
      const button = screen.getByRole('button', { name: /enable alignment guides/i });
      expect(button).toHaveClass('text-gray-700');
    });

    it('renders settings button', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      expect(settingsButton).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Toggle Behavior
  // ---------------------------------------------------------------------------

  describe('toggle behavior', () => {
    it('calls onToggle when button is clicked', () => {
      const onToggle = vi.fn();
      renderToolbar({ onToggle });
      
      const button = screen.getByRole('button', { name: /alignment guides/i });
      fireEvent.click(button);
      
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it('has correct aria-pressed attribute when enabled', () => {
      renderToolbar({ enabled: true });
      
      const button = screen.getByRole('button', { name: /disable alignment guides/i });
      expect(button).toHaveAttribute('aria-pressed', 'true');
    });

    it('has correct aria-pressed attribute when disabled', () => {
      renderToolbar({ enabled: false });
      
      const button = screen.getByRole('button', { name: /enable alignment guides/i });
      expect(button).toHaveAttribute('aria-pressed', 'false');
    });
  });

  // ---------------------------------------------------------------------------
  // Settings Popover
  // ---------------------------------------------------------------------------

  describe('settings popover', () => {
    it('opens popover when settings button is clicked', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Alignment Guides')).toBeInTheDocument();
    });

    it('closes popover when settings button is clicked again', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      
      fireEvent.click(settingsButton);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('displays all alignment type checkboxes', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByLabelText(/edge alignment/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/center alignment/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/face alignment/i)).toBeInTheDocument();
    });

    it('checkboxes reflect settings state', () => {
      const settings: AlignmentSettings = {
        ...defaultSettings,
        enableEdgeAlignment: false,
        enableCenterAlignment: true,
        enableFaceAlignment: false,
      };
      renderToolbar({ settings });
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByLabelText(/edge alignment/i)).not.toBeChecked();
      expect(screen.getByLabelText(/center alignment/i)).toBeChecked();
      expect(screen.getByLabelText(/face alignment/i)).not.toBeChecked();
    });

    it('calls onSettingsChange when checkbox is toggled', () => {
      const onSettingsChange = vi.fn();
      renderToolbar({ onSettingsChange });
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      // Toggle edge alignment off
      const edgeCheckbox = screen.getByLabelText(/edge alignment/i);
      fireEvent.click(edgeCheckbox);
      
      expect(onSettingsChange).toHaveBeenCalledWith({ enableEdgeAlignment: false });
    });
  });

  // ---------------------------------------------------------------------------
  // Snap Distance Slider
  // ---------------------------------------------------------------------------

  describe('snap distance slider', () => {
    it('displays snap distance slider', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByRole('slider', { name: /snap distance/i })).toBeInTheDocument();
    });

    it('slider shows current value', () => {
      renderToolbar({ settings: { ...defaultSettings, snapDistance: 15 } });
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByText('15 units')).toBeInTheDocument();
    });

    it('calls onSettingsChange when slider changes', () => {
      const onSettingsChange = vi.fn();
      renderToolbar({ onSettingsChange });
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      // Change slider
      const slider = screen.getByRole('slider', { name: /snap distance/i });
      fireEvent.change(slider, { target: { value: '20' } });
      
      expect(onSettingsChange).toHaveBeenCalledWith({ snapDistance: 20 });
    });
  });

  // ---------------------------------------------------------------------------
  // Grid Snap Slider
  // ---------------------------------------------------------------------------

  describe('grid snap slider', () => {
    it('displays grid snap slider', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByRole('slider', { name: /grid snap increment/i })).toBeInTheDocument();
    });

    it('calls onSettingsChange when slider changes', () => {
      const onSettingsChange = vi.fn();
      renderToolbar({ onSettingsChange });
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      // Change slider
      const slider = screen.getByRole('slider', { name: /grid snap increment/i });
      fireEvent.change(slider, { target: { value: '10' } });
      
      expect(onSettingsChange).toHaveBeenCalledWith({ snapThreshold: 10 });
    });
  });

  // ---------------------------------------------------------------------------
  // Click Outside
  // ---------------------------------------------------------------------------

  describe('click outside', () => {
    it('closes popover when clicking outside', () => {
      renderToolbar();
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      
      // Click outside
      fireEvent.mouseDown(document.body);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('does not close popover when clicking inside', () => {
      renderToolbar();
      
      // Open popover
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      // Click inside popover
      const dialog = screen.getByRole('dialog');
      fireEvent.mouseDown(dialog);
      
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Accessibility
  // ---------------------------------------------------------------------------

  describe('accessibility', () => {
    it('has correct aria-haspopup on settings button', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      expect(settingsButton).toHaveAttribute('aria-haspopup', 'dialog');
    });

    it('has correct aria-expanded on settings button', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      expect(settingsButton).toHaveAttribute('aria-expanded', 'false');
      
      fireEvent.click(settingsButton);
      expect(settingsButton).toHaveAttribute('aria-expanded', 'true');
    });

    it('displays hint about Alt key', () => {
      renderToolbar();
      
      const settingsButton = screen.getByRole('button', { name: /alignment settings/i });
      fireEvent.click(settingsButton);
      
      expect(screen.getByText(/hold alt/i)).toBeInTheDocument();
    });
  });
});
