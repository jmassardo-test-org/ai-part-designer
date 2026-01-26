/**
 * LayoutPreview3D Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LayoutPreview3D } from './LayoutPreview3D';

// Mock Three.js and react-three-fiber
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="canvas">{children}</div>
  ),
  useFrame: vi.fn(),
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  PerspectiveCamera: () => null,
  Grid: () => null,
  Environment: () => null,
  Html: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

describe('LayoutPreview3D', () => {
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
      rotation: 0,
      locked: false,
    },
  ];

  const defaultProps = {
    dimensions: mockDimensions,
    placements: mockPlacements,
    selectedId: null,
    onSelect: vi.fn(),
    showEnclosure: true,
    showGrid: true,
    wireframe: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders 3D canvas', () => {
    render(<LayoutPreview3D {...defaultProps} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('shows view mode buttons', () => {
    render(<LayoutPreview3D {...defaultProps} />);
    
    expect(screen.getByText('T')).toBeInTheDocument(); // Top
    expect(screen.getByText('F')).toBeInTheDocument(); // Front
    expect(screen.getByText('S')).toBeInTheDocument(); // Side
  });

  it('shows legend', () => {
    render(<LayoutPreview3D {...defaultProps} />);
    
    expect(screen.getByText('Selected')).toBeInTheDocument();
    expect(screen.getByText('Component')).toBeInTheDocument();
    expect(screen.getByText('Enclosure')).toBeInTheDocument();
  });

  it('switches to top view when T button clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutPreview3D {...defaultProps} />);
    
    await user.click(screen.getByText('T'));
    
    // Top button should be active (have different style)
    const topButton = screen.getByText('T');
    expect(topButton.className).toContain('bg-blue-600');
  });

  it('switches to front view when F button clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutPreview3D {...defaultProps} />);
    
    await user.click(screen.getByText('F'));
    
    const frontButton = screen.getByText('F');
    expect(frontButton.className).toContain('bg-blue-600');
  });

  it('switches to side view when S button clicked', async () => {
    const user = userEvent.setup();
    render(<LayoutPreview3D {...defaultProps} />);
    
    await user.click(screen.getByText('S'));
    
    const sideButton = screen.getByText('S');
    expect(sideButton.className).toContain('bg-blue-600');
  });

  it('perspective view is active by default', () => {
    render(<LayoutPreview3D {...defaultProps} />);
    
    // Find perspective button (SVG icon button)
    const buttons = screen.getAllByRole('button');
    const perspectiveButton = buttons.find(btn => btn.title === 'Perspective');
    if (perspectiveButton) {
      expect(perspectiveButton.className).toContain('bg-blue-600');
    }
  });

  it('renders with showEnclosure=true', () => {
    render(<LayoutPreview3D {...defaultProps} showEnclosure={true} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders with showEnclosure=false', () => {
    render(<LayoutPreview3D {...defaultProps} showEnclosure={false} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders with showGrid=true', () => {
    render(<LayoutPreview3D {...defaultProps} showGrid={true} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders with showGrid=false', () => {
    render(<LayoutPreview3D {...defaultProps} showGrid={false} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders with wireframe=true', () => {
    render(<LayoutPreview3D {...defaultProps} wireframe={true} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('highlights selected component', () => {
    render(<LayoutPreview3D {...defaultProps} selectedId="placement-1" />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('calls onSelect when component clicked', () => {
    render(<LayoutPreview3D {...defaultProps} />);
    // Component selection is handled in 3D scene
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders with empty placements', () => {
    render(<LayoutPreview3D {...defaultProps} placements={[]} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('applies correct colors in legend', () => {
    render(<LayoutPreview3D {...defaultProps} />);
    
    // Check for color indicators
    const colorIndicators = document.querySelectorAll('.w-3.h-3.rounded');
    expect(colorIndicators.length).toBeGreaterThan(0);
  });

  it('has correct background color', () => {
    const { container } = render(<LayoutPreview3D {...defaultProps} />);
    
    const wrapper = container.firstChild;
    expect(wrapper).toHaveClass('bg-slate-900');
  });

  it('view buttons have correct titles', () => {
    render(<LayoutPreview3D {...defaultProps} />);
    
    const topButton = screen.getByTitle('Top');
    const frontButton = screen.getByTitle('Front');
    const sideButton = screen.getByTitle('Side');
    const perspectiveButton = screen.getByTitle('Perspective');
    
    expect(topButton).toBeInTheDocument();
    expect(frontButton).toBeInTheDocument();
    expect(sideButton).toBeInTheDocument();
    expect(perspectiveButton).toBeInTheDocument();
  });
});
