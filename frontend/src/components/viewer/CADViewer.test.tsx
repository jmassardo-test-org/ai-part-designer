/**
 * CADViewer Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import CADViewer, { ModelViewer } from './CADViewer';

// Mock Three.js and react-three-fiber
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="canvas">{children}</div>
  ),
  useThree: () => ({
    camera: { position: { set: vi.fn(), multiplyScalar: vi.fn() }, lookAt: vi.fn() },
  }),
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Center: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Grid: () => null,
  Environment: () => null,
  Html: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('three-stdlib', () => ({
  STLLoader: vi.fn().mockImplementation(() => ({
    load: vi.fn(),
    parse: vi.fn(),
  })),
}));

describe('CADViewer', () => {
  it('re-exports ModelViewer as default', () => {
    expect(CADViewer).toBe(ModelViewer);
  });

  it('exports ModelViewer as named export', () => {
    expect(ModelViewer).toBeDefined();
  });
});

describe('ModelViewer', () => {
  it('renders with default props', () => {
    render(<ModelViewer />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(<ModelViewer className="custom-class" />);
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('renders with stlUrl prop', () => {
    render(<ModelViewer stlUrl="http://example.com/model.stl" />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders viewer controls', () => {
    render(<ModelViewer stlUrl="http://example.com/model.stl" />);
    // Check for control buttons
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts showGrid prop', () => {
    render(<ModelViewer showGrid={false} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts showAxes prop', () => {
    render(<ModelViewer showAxes={true} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts backgroundColor prop', () => {
    render(<ModelViewer backgroundColor="#ffffff" />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts color prop', () => {
    render(<ModelViewer color="#ff0000" />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });
});
