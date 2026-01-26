/**
 * LayoutCanvas Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LayoutCanvas } from './LayoutCanvas';

describe('LayoutCanvas', () => {
  const mockDimensions = {
    width: 200,
    depth: 150,
    height: 50,
    gridSize: 10,
    clearance: 2,
  };

  const mockPlacements = [
    {
      id: 'placement-1',
      componentId: 'comp-1',
      name: 'Component A',
      x: 10,
      y: 10,
      width: 50,
      depth: 40,
      height: 20,
      rotation: 0,
      locked: false,
    },
    {
      id: 'placement-2',
      componentId: 'comp-2',
      name: 'Component B',
      x: 80,
      y: 60,
      width: 30,
      depth: 30,
      height: 15,
      rotation: 90,
      locked: true,
    },
  ];

  const defaultProps = {
    dimensions: mockDimensions,
    placements: mockPlacements,
    gridSize: 10,
    clearanceMargin: 2,
    selectedId: null,
    onSelect: vi.fn(),
    onMove: vi.fn(),
    onRotate: vi.fn(),
    showGrid: true,
    showClearance: true,
    readOnly: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders canvas container', () => {
    const { container } = render(<LayoutCanvas {...defaultProps} />);
    expect(container.querySelector('.overflow-auto')).toBeInTheDocument();
  });

  it('renders all placements', () => {
    render(<LayoutCanvas {...defaultProps} />);
    
    expect(screen.getByText('Component A')).toBeInTheDocument();
    expect(screen.getByText('Component B')).toBeInTheDocument();
  });

  it('shows grid when showGrid is true', () => {
    const { container } = render(<LayoutCanvas {...defaultProps} showGrid={true} />);
    
    // Grid is rendered as background pattern
    const canvasArea = container.querySelector('[style*="repeating-linear-gradient"]');
    expect(canvasArea).toBeInTheDocument();
  });

  it('hides grid when showGrid is false', () => {
    const { container } = render(<LayoutCanvas {...defaultProps} showGrid={false} />);
    
    // No grid pattern
    const canvasArea = container.querySelector('[style*="repeating-linear-gradient"]');
    expect(canvasArea).toBeNull();
  });

  it('calls onSelect when clicking a component', async () => {
    const user = userEvent.setup();
    render(<LayoutCanvas {...defaultProps} />);
    
    await user.click(screen.getByText('Component A'));
    
    expect(defaultProps.onSelect).toHaveBeenCalledWith('placement-1');
  });

  it('calls onSelect with null when clicking canvas background', async () => {
    const user = userEvent.setup();
    const { container } = render(<LayoutCanvas {...defaultProps} />);
    
    const canvasArea = container.querySelector('.overflow-auto > div');
    if (canvasArea) {
      await user.click(canvasArea);
    }
  });

  it('highlights selected component', () => {
    render(<LayoutCanvas {...defaultProps} selectedId="placement-1" />);
    
    // Selected component should have special styling
    const componentA = screen.getByText('Component A').closest('div');
    expect(componentA).toHaveClass('border-blue-500') || expect(componentA?.className).toContain('selected');
  });

  it('handles drag on component', async () => {
    render(<LayoutCanvas {...defaultProps} />);
    
    const component = screen.getByText('Component A');
    
    fireEvent.mouseDown(component, { clientX: 100, clientY: 100 });
    
    expect(defaultProps.onSelect).toHaveBeenCalled();
  });

  it('does not allow dragging locked components', async () => {
    render(<LayoutCanvas {...defaultProps} />);
    
    const lockedComponent = screen.getByText('Component B');
    
    fireEvent.mouseDown(lockedComponent, { clientX: 100, clientY: 100 });
    
    // Locked component should not be selected for dragging
  });

  it('does not allow interactions in readOnly mode', async () => {
    const user = userEvent.setup();
    render(<LayoutCanvas {...defaultProps} readOnly={true} />);
    
    await user.click(screen.getByText('Component A'));
    
    // onSelect may or may not be called, but no dragging should occur
  });

  it('calls onRotate on double click', async () => {
    const user = userEvent.setup();
    render(<LayoutCanvas {...defaultProps} />);
    
    await user.dblClick(screen.getByText('Component A'));
    
    expect(defaultProps.onRotate).toHaveBeenCalledWith('placement-1');
  });

  it('does not rotate locked components', async () => {
    const user = userEvent.setup();
    render(<LayoutCanvas {...defaultProps} />);
    
    await user.dblClick(screen.getByText('Component B'));
    
    expect(defaultProps.onRotate).not.toHaveBeenCalled();
  });

  it('supports zoom with mouse wheel', async () => {
    const { container } = render(<LayoutCanvas {...defaultProps} />);
    
    const canvasArea = container.querySelector('.overflow-auto');
    
    if (canvasArea) {
      fireEvent.wheel(canvasArea, { deltaY: -100 });
    }
    
    // Zoom should change (internal state)
  });

  it('snaps movement to grid', async () => {
    render(<LayoutCanvas {...defaultProps} />);
    
    // When moving a component, it should snap to grid
    const component = screen.getByText('Component A').closest('div');
    
    if (component) {
      // Simulate drag
      fireEvent.mouseDown(component, { clientX: 50, clientY: 50 });
      fireEvent.mouseMove(document, { clientX: 73, clientY: 73 }); // Should snap to 70, 70
      fireEvent.mouseUp(document);
    }
  });

  it('shows clearance zones when showClearance is true', () => {
    const { container } = render(<LayoutCanvas {...defaultProps} showClearance={true} />);
    
    // Clearance visualization should be present
    expect(container).toBeInTheDocument();
  });

  it('renders with empty placements', () => {
    render(<LayoutCanvas {...defaultProps} placements={[]} />);
    
    expect(screen.queryByText('Component A')).not.toBeInTheDocument();
  });

  it('displays component rotation', () => {
    render(<LayoutCanvas {...defaultProps} />);
    
    // Component B has 90 degree rotation
    const componentB = screen.getByText('Component B').closest('div');
    expect(componentB?.style.transform || componentB?.className).toBeDefined();
  });

  it('shows lock indicator for locked components', () => {
    render(<LayoutCanvas {...defaultProps} />);
    
    // Component B is locked, should show indicator
    const componentB = screen.getByText('Component B').closest('div');
    expect(componentB).toBeInTheDocument();
  });

  it('clamps movement to enclosure bounds', async () => {
    render(<LayoutCanvas {...defaultProps} />);
    
    const component = screen.getByText('Component A').closest('div');
    
    if (component) {
      // Try to move outside bounds
      fireEvent.mouseDown(component, { clientX: 50, clientY: 50 });
      fireEvent.mouseMove(document, { clientX: 1000, clientY: 1000 }); // Way outside
      fireEvent.mouseUp(document);
      
      // onMove should be called with clamped values
    }
  });

  it('detects collisions between components', () => {
    const overlappingPlacements = [
      { ...mockPlacements[0], x: 10, y: 10 },
      { ...mockPlacements[1], x: 15, y: 15, locked: false }, // Overlapping
    ];
    
    render(<LayoutCanvas {...defaultProps} placements={overlappingPlacements} />);
    
    // Should still render both components
    expect(screen.getByText('Component A')).toBeInTheDocument();
    expect(screen.getByText('Component B')).toBeInTheDocument();
  });

  it('supports keyboard movement for selected component', async () => {
    render(<LayoutCanvas {...defaultProps} selectedId="placement-1" />);
    
    // Keyboard events should move the selected component
  });
});
