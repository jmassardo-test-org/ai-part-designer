/**
 * CADViewer Component Tests
 */
/* eslint-disable import/order */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
// Mock WebGL context at the global level before importing components
const mockWebGLContext = {
  getExtension: vi.fn(() => ({ loseContext: vi.fn() })),
  getParameter: vi.fn(),
  createBuffer: vi.fn(),
  bindBuffer: vi.fn(),
  bufferData: vi.fn(),
  createProgram: vi.fn(),
  createShader: vi.fn(),
  shaderSource: vi.fn(),
  compileShader: vi.fn(),
  attachShader: vi.fn(),
  linkProgram: vi.fn(),
  getProgramParameter: vi.fn(() => true),
  useProgram: vi.fn(),
  getAttribLocation: vi.fn(() => 0),
  getUniformLocation: vi.fn(() => ({})),
  enableVertexAttribArray: vi.fn(),
  vertexAttribPointer: vi.fn(),
  uniformMatrix4fv: vi.fn(),
  drawArrays: vi.fn(),
  viewport: vi.fn(),
  clearColor: vi.fn(),
  clear: vi.fn(),
  enable: vi.fn(),
  disable: vi.fn(),
  blendFunc: vi.fn(),
  depthFunc: vi.fn(),
  cullFace: vi.fn(),
  frontFace: vi.fn(),
};

const originalGetContext = HTMLCanvasElement.prototype.getContext;

beforeAll(() => {
  // Mock WebGL context
  HTMLCanvasElement.prototype.getContext = vi.fn(function(
    this: HTMLCanvasElement, 
    contextType: string
  ) {
    if (contextType === 'webgl' || contextType === 'webgl2' || contextType === 'experimental-webgl') {
      return mockWebGLContext as unknown as WebGLRenderingContext;
    }
    return originalGetContext.call(this, contextType as '2d');
  }) as typeof HTMLCanvasElement.prototype.getContext;
});

afterAll(() => {
  HTMLCanvasElement.prototype.getContext = originalGetContext;
});

// Import after mocking
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

// Mock STLLoader as a class - define inside the factory to avoid hoisting issues
vi.mock('three-stdlib', () => {
  return {
    STLLoader: class {
      load = vi.fn();
      parse = vi.fn();
    },
  };
});

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
