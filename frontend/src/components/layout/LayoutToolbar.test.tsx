/**
 * LayoutToolbar Component Tests
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LayoutToolbar } from './LayoutToolbar';

describe('LayoutToolbar', () => {
  const defaultProps = {
    zoom: 1,
    onZoomIn: vi.fn(),
    onZoomOut: vi.fn(),
    onZoomReset: vi.fn(),
    onRotateSelected: vi.fn(),
    onDeleteSelected: vi.fn(),
    onToggleLock: vi.fn(),
    onAutoLayout: vi.fn(),
    onValidate: vi.fn(),
    hasSelection: false,
    isLocked: false,
    isValidating: false,
    isAutoLayouting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders toolbar', () => {
    render(<LayoutToolbar {...defaultProps} />);
    expect(screen.getByText('100%')).toBeInTheDocument(); // Zoom display
  });

  it('displays current zoom level', () => {
    render(<LayoutToolbar {...defaultProps} zoom={1.5} />);
    expect(screen.getByText('150%')).toBeInTheDocument();
  });

  it('calls onZoomIn when zoom in clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    const zoomInButton = screen.getByTitle('Zoom in');
    await user.click(zoomInButton);
    
    expect(defaultProps.onZoomIn).toHaveBeenCalled();
  });

  it('calls onZoomOut when zoom out clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    const zoomOutButton = screen.getByTitle('Zoom out');
    await user.click(zoomOutButton);
    
    expect(defaultProps.onZoomOut).toHaveBeenCalled();
  });

  it('calls onZoomReset when zoom display clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('100%'));
    
    expect(defaultProps.onZoomReset).toHaveBeenCalled();
  });

  it('disables rotate button when no selection', () => {
    render(<LayoutToolbar {...defaultProps} hasSelection={false} />);
    
    const rotateButton = screen.getByTitle(/rotate/i);
    expect(rotateButton).toBeDisabled();
  });

  it('enables rotate button when has selection', () => {
    render(<LayoutToolbar {...defaultProps} hasSelection={true} />);
    
    const rotateButton = screen.getByTitle(/rotate/i);
    expect(rotateButton).not.toBeDisabled();
  });

  it('calls onRotateSelected when rotate clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} hasSelection={true} />);
    
    const rotateButton = screen.getByTitle(/rotate/i);
    await user.click(rotateButton);
    
    expect(defaultProps.onRotateSelected).toHaveBeenCalled();
  });

  it('disables delete button when no selection', () => {
    render(<LayoutToolbar {...defaultProps} hasSelection={false} />);
    
    const deleteButton = screen.getByTitle(/remove|delete/i);
    expect(deleteButton).toBeDisabled();
  });

  it('calls onDeleteSelected when delete clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} hasSelection={true} />);
    
    const deleteButton = screen.getByTitle(/remove|delete/i);
    await user.click(deleteButton);
    
    expect(defaultProps.onDeleteSelected).toHaveBeenCalled();
  });

  it('disables lock button when no selection', () => {
    render(<LayoutToolbar {...defaultProps} hasSelection={false} />);
    
    const lockButton = screen.getByTitle(/lock/i);
    expect(lockButton).toBeDisabled();
  });

  it('calls onToggleLock when lock clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} hasSelection={true} />);
    
    const lockButton = screen.getByTitle(/lock/i);
    await user.click(lockButton);
    
    expect(defaultProps.onToggleLock).toHaveBeenCalled();
  });

  it('shows locked icon when isLocked is true', () => {
    render(<LayoutToolbar {...defaultProps} hasSelection={true} isLocked={true} />);
    
    const lockButton = screen.getByTitle(/unlock/i);
    expect(lockButton).toBeInTheDocument();
  });

  it('shows auto layout button', () => {
    render(<LayoutToolbar {...defaultProps} />);
    expect(screen.getByText('Auto Layout')).toBeInTheDocument();
  });

  it('shows auto layout dropdown on click', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    
    expect(screen.getByText('Packed')).toBeInTheDocument();
    expect(screen.getByText('Grid')).toBeInTheDocument();
    expect(screen.getByText('Thermal')).toBeInTheDocument();
    expect(screen.getByText('Connector Access')).toBeInTheDocument();
  });

  it('calls onAutoLayout with correct algorithm', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    await user.click(screen.getByText('Packed'));
    
    expect(defaultProps.onAutoLayout).toHaveBeenCalledWith('packed');
  });

  it('calls onAutoLayout with grid algorithm', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    await user.click(screen.getByText('Grid'));
    
    expect(defaultProps.onAutoLayout).toHaveBeenCalledWith('grid');
  });

  it('calls onAutoLayout with thermal algorithm', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    await user.click(screen.getByText('Thermal'));
    
    expect(defaultProps.onAutoLayout).toHaveBeenCalledWith('thermal');
  });

  it('calls onAutoLayout with connector algorithm', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    await user.click(screen.getByText('Connector Access'));
    
    expect(defaultProps.onAutoLayout).toHaveBeenCalledWith('connector');
  });

  it('shows arranging state when isAutoLayouting', () => {
    render(<LayoutToolbar {...defaultProps} isAutoLayouting={true} />);
    
    expect(screen.getByText('Arranging...')).toBeInTheDocument();
  });

  it('disables auto layout button when isAutoLayouting', () => {
    render(<LayoutToolbar {...defaultProps} isAutoLayouting={true} />);
    
    const button = screen.getByText('Arranging...').closest('button');
    expect(button).toBeDisabled();
  });

  it('shows validate button', () => {
    render(<LayoutToolbar {...defaultProps} />);
    expect(screen.getByText('Validate')).toBeInTheDocument();
  });

  it('calls onValidate when validate clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Validate'));
    
    expect(defaultProps.onValidate).toHaveBeenCalled();
  });

  it('shows validating state when isValidating', () => {
    render(<LayoutToolbar {...defaultProps} isValidating={true} />);
    
    expect(screen.getByText('Validating...')).toBeInTheDocument();
  });

  it('disables validate button when isValidating', () => {
    render(<LayoutToolbar {...defaultProps} isValidating={true} />);
    
    const button = screen.getByText('Validating...').closest('button');
    expect(button).toBeDisabled();
  });

  it('closes auto layout dropdown when option selected', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    expect(screen.getByText('Packed')).toBeInTheDocument();
    
    await user.click(screen.getByText('Packed'));
    
    // Dropdown should close
    expect(screen.queryByText('Dense shelf packing')).not.toBeInTheDocument();
  });

  it('closes dropdown when clicking outside', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    expect(screen.getByText('Packed')).toBeInTheDocument();
    
    // Click outside
    const backdrop = document.querySelector('.fixed.inset-0');
    if (backdrop) {
      await user.click(backdrop);
    }
    
    // Dropdown should close
    await waitFor(() => {
      expect(screen.queryByText('Dense shelf packing')).not.toBeInTheDocument();
    });
  });

  it('shows algorithm descriptions', async () => {
    const user = userEvent.setup();
    render(<LayoutToolbar {...defaultProps} />);
    
    await user.click(screen.getByText('Auto Layout'));
    
    expect(screen.getByText('Dense shelf packing')).toBeInTheDocument();
    expect(screen.getByText('Uniform grid layout')).toBeInTheDocument();
    expect(screen.getByText('Spread heat sources')).toBeInTheDocument();
    expect(screen.getByText('Connectors at edges')).toBeInTheDocument();
  });
});
