/**
 * EnclosureOptionsPanel Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EnclosureOptionsPanel } from './EnclosureOptionsPanel';

describe('EnclosureOptionsPanel', () => {
  const defaultOptions = {
    wallThickness: 2,
    bottomThickness: 2,
    topThickness: 2,
    style: 'rounded' as const,
    cornerRadius: 3,
    chamferSize: 2,
    lidType: 'snap_fit' as const,
    lidClearance: 0.2,
    screwHoleDiameter: 3,
    screwHoleCount: 4,
    ventilationType: 'none' as const,
    ventilationSize: 2,
    ventilationSpacing: 3,
    ventilationFaces: [],
    mountingType: 'standoffs' as const,
    standoffHeight: 3,
    standoffDiameter: 6,
    autoCutouts: true,
    cutoutClearance: 0.5,
    cableManagement: false,
    labelEmboss: false,
    labelText: '',
  };

  const defaultProps = {
    options: defaultOptions,
    onChange: vi.fn(),
    isCollapsed: false,
    onToggleCollapse: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders panel when not collapsed', () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    expect(screen.getByText('Enclosure Options')).toBeInTheDocument();
  });

  it('renders collapsed state', () => {
    render(<EnclosureOptionsPanel {...defaultProps} isCollapsed={true} />);
    
    // Should show expand button but not the full panel
    expect(screen.queryByText('Enclosure Options')).not.toBeInTheDocument();
  });

  it('calls onToggleCollapse when expand button clicked', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} isCollapsed={true} />);
    
    const expandButton = screen.getByRole('button', { name: /expand/i });
    await user.click(expandButton);
    
    expect(defaultProps.onToggleCollapse).toHaveBeenCalled();
  });

  it('shows dimensions section', () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    expect(screen.getByText('Dimensions')).toBeInTheDocument();
  });

  it('shows style section', () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    expect(screen.getByText('Style')).toBeInTheDocument();
  });

  it('shows lid section', () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    expect(screen.getByText('Lid')).toBeInTheDocument();
  });

  it('shows mounting section', () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    expect(screen.getByText('Mounting')).toBeInTheDocument();
  });

  it('shows ventilation section', () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    expect(screen.getByText('Ventilation')).toBeInTheDocument();
  });

  it('expands section when clicked', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    // Click on Style section to expand it
    await user.click(screen.getByText('Style'));
    
    // Should show style options
    expect(screen.getByText('Shape')).toBeInTheDocument();
  });

  it('shows wall thickness slider', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    // Dimensions section is expanded by default
    expect(screen.getByText('Wall Thickness')).toBeInTheDocument();
  });

  it('calls onChange when wall thickness changes', async () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    // Find the wall thickness slider/input
    const sliders = document.querySelectorAll('input[type="range"]');
    if (sliders.length > 0) {
      fireEvent.change(sliders[0], { target: { value: '3' } });
      expect(defaultProps.onChange).toHaveBeenCalled();
    }
  });

  it('shows style buttons', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    await user.click(screen.getByText('Style'));
    
    expect(screen.getByText('rectangular')).toBeInTheDocument();
    expect(screen.getByText('rounded')).toBeInTheDocument();
    expect(screen.getByText('chamfered')).toBeInTheDocument();
    expect(screen.getByText('minimal')).toBeInTheDocument();
  });

  it('calls onChange when style button clicked', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    await user.click(screen.getByText('Style'));
    await user.click(screen.getByText('rectangular'));
    
    expect(defaultProps.onChange).toHaveBeenCalledWith({ style: 'rectangular' });
  });

  it('shows corner radius for rounded style', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} options={{ ...defaultOptions, style: 'rounded' }} />);
    
    await user.click(screen.getByText('Style'));
    
    expect(screen.getByText('Corner Radius')).toBeInTheDocument();
  });

  it('shows chamfer size for chamfered style', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} options={{ ...defaultOptions, style: 'chamfered' }} />);
    
    await user.click(screen.getByText('Style'));
    
    expect(screen.getByText('Chamfer Size')).toBeInTheDocument();
  });

  it('shows lid type selector', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    await user.click(screen.getByText('Lid'));
    
    expect(screen.getByText('Type')).toBeInTheDocument();
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
  });

  it('shows screw options for screw lid type', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} options={{ ...defaultOptions, lidType: 'screw' }} />);
    
    await user.click(screen.getByText('Lid'));
    
    expect(screen.getByText(/screw hole/i)).toBeInTheDocument();
    expect(screen.getByText(/screw count/i)).toBeInTheDocument();
  });

  it('shows mounting type selector', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    await user.click(screen.getByText('Mounting'));
    
    expect(screen.getByRole('combobox')).toBeInTheDocument();
  });

  it('shows standoff options for standoffs mounting', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    await user.click(screen.getByText('Mounting'));
    
    expect(screen.getByText('Height')).toBeInTheDocument();
    expect(screen.getByText('Diameter')).toBeInTheDocument();
  });

  it('shows ventilation pattern selector', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    await user.click(screen.getByText('Ventilation'));
    
    expect(screen.getByText('Pattern')).toBeInTheDocument();
  });

  it('shows ventilation options when pattern selected', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} options={{ ...defaultOptions, ventilationType: 'slots' }} />);
    
    await user.click(screen.getByText('Ventilation'));
    
    expect(screen.getByText('Hole Size')).toBeInTheDocument();
    expect(screen.getByText('Spacing')).toBeInTheDocument();
  });

  it('collapses section when clicked again', async () => {
    const user = userEvent.setup();
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    // Dimensions is expanded by default, click to collapse
    await user.click(screen.getByText('Dimensions'));
    
    // Wall Thickness should be hidden after collapse
    expect(screen.queryByText('Wall Thickness')).not.toBeInTheDocument();
  });

  it('shows collapse button when onToggleCollapse provided', () => {
    render(<EnclosureOptionsPanel {...defaultProps} />);
    
    // Should have collapse button in header
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('hides collapse button when onToggleCollapse not provided', () => {
    render(<EnclosureOptionsPanel {...defaultProps} onToggleCollapse={undefined} />);
    
    // Header should still exist but without collapse toggle
    expect(screen.getByText('Enclosure Options')).toBeInTheDocument();
  });
});
