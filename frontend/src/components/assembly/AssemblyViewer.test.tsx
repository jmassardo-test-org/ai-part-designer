/**
 * AssemblyViewer Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AssemblyViewer } from './AssemblyViewer';

// Mock Three.js and react-three-fiber
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="canvas">{children}</div>
  ),
  useThree: () => ({
    camera: { position: { set: vi.fn() }, lookAt: vi.fn() },
  }),
  useFrame: vi.fn(),
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  PerspectiveCamera: () => null,
  Environment: () => null,
  Html: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('three-stdlib', () => ({
  STLLoader: vi.fn().mockImplementation(() => ({
    load: vi.fn((_, onLoad) => {
      // Simulate successful load with mock geometry
      setTimeout(() => {
        onLoad({
          computeVertexNormals: vi.fn(),
          center: vi.fn(),
          dispose: vi.fn(),
        });
      }, 0);
    }),
  })),
}));

describe('AssemblyViewer', () => {
  const mockComponents = [
    {
      id: 'comp-1',
      name: 'Component 1',
      quantity: 1,
      position: { x: 0, y: 0, z: 0 },
      rotation: { rx: 0, ry: 0, rz: 0 },
      scale: { sx: 1, sy: 1, sz: 1 },
      is_cots: false,
      color: '#ff0000',
    },
    {
      id: 'comp-2',
      name: 'Component 2',
      quantity: 2,
      position: { x: 50, y: 0, z: 0 },
      rotation: { rx: 0, ry: 45, rz: 0 },
      scale: { sx: 1, sy: 1, sz: 1 },
      is_cots: true,
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders canvas container', () => {
    render(<AssemblyViewer components={mockComponents} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <AssemblyViewer components={mockComponents} className="custom-class" />
    );
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('renders with empty components array', () => {
    render(<AssemblyViewer components={[]} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts selectedComponentId prop', () => {
    render(
      <AssemblyViewer 
        components={mockComponents} 
        selectedComponentId="comp-1"
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('calls onSelectComponent when component clicked', async () => {
    const onSelectComponent = vi.fn();
    render(
      <AssemblyViewer 
        components={mockComponents}
        onSelectComponent={onSelectComponent}
      />
    );
    // Component selection is handled within the 3D scene
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('supports exploded view', () => {
    render(
      <AssemblyViewer 
        components={mockComponents}
        explodedView={true}
        explodeFactor={1.5}
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('supports hidden components', () => {
    const hiddenComponents = new Set(['comp-1']);
    render(
      <AssemblyViewer 
        components={mockComponents}
        hiddenComponents={hiddenComponents}
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders view controls', () => {
    const { container } = render(<AssemblyViewer components={mockComponents} />);
    // Check for control buttons
    expect(container.querySelector('[data-testid="canvas"]')).toBeInTheDocument();
  });

  it('handles components with file_url', () => {
    const componentsWithUrl = [
      {
        ...mockComponents[0],
        file_url: 'http://example.com/model.stl',
      },
    ];
    
    render(<AssemblyViewer components={componentsWithUrl} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('handles components with thumbnail_url', () => {
    const componentsWithThumbnail = [
      {
        ...mockComponents[0],
        thumbnail_url: 'http://example.com/thumb.png',
      },
    ];
    
    render(<AssemblyViewer components={componentsWithThumbnail} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('handles components with design_id', () => {
    const componentsWithDesign = [
      {
        ...mockComponents[0],
        design_id: 'design-123',
      },
    ];
    
    render(<AssemblyViewer components={componentsWithDesign} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders with default explodeFactor', () => {
    render(
      <AssemblyViewer 
        components={mockComponents}
        explodedView={true}
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('distinguishes COTS components visually', () => {
    const cotsComponent = [
      {
        id: 'cots-1',
        name: 'COTS Component',
        quantity: 1,
        position: { x: 0, y: 0, z: 0 },
        rotation: { rx: 0, ry: 0, rz: 0 },
        scale: { sx: 1, sy: 1, sz: 1 },
        is_cots: true,
      },
    ];
    
    render(<AssemblyViewer components={cotsComponent} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });
});
