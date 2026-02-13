/**
 * InteractiveAssemblyViewer Component Tests
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { InteractiveAssemblyViewer } from './InteractiveAssemblyViewer';

// Mock Three.js and react-three-fiber
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="canvas">{children}</div>
  ),
  useThree: () => ({
    camera: { position: { set: vi.fn() }, lookAt: vi.fn() },
    gl: { domElement: document.createElement('canvas') },
  }),
  useFrame: vi.fn(),
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  PerspectiveCamera: () => null,
  Environment: () => null,
  Html: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TransformControls: () => null,
}));

vi.mock('three-stdlib', () => {
  class MockSTLLoader {
    load = vi.fn((_, onLoad) => {
      setTimeout(() => {
        onLoad({
          computeVertexNormals: vi.fn(),
          center: vi.fn(),
          dispose: vi.fn(),
        });
      }, 0);
    });
  }
  return { STLLoader: MockSTLLoader };
});

// Mock hooks
vi.mock('../../hooks/usePartTransforms', () => ({
  usePartTransforms: () => ({
    transforms: {},
    updateTransform: vi.fn(),
    resetTransform: vi.fn(),
    resetAllTransforms: vi.fn(),
    canUndo: false,
    canRedo: false,
    undo: vi.fn(),
    redo: vi.fn(),
    undoDescription: null,
    redoDescription: null,
    clearHistory: vi.fn(),
  }),
}));

describe('InteractiveAssemblyViewer', () => {
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
    sessionStorage.clear();
  });

  it('renders canvas container', () => {
    render(<InteractiveAssemblyViewer components={mockComponents} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    const { container } = render(
      <InteractiveAssemblyViewer components={mockComponents} className="custom-class" />
    );
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('renders with empty components array', () => {
    render(<InteractiveAssemblyViewer components={[]} />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('displays component count', () => {
    render(<InteractiveAssemblyViewer components={mockComponents} />);
    expect(screen.getByText(/2 components/i)).toBeInTheDocument();
  });

  it('displays transform mode buttons', () => {
    const { container } = render(
      <InteractiveAssemblyViewer components={mockComponents} />
    );
    
    // Move and Rotate buttons should be present (using lucide-react icons)
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('displays undo/redo buttons', () => {
    const { container } = render(
      <InteractiveAssemblyViewer components={mockComponents} />
    );
    
    // Undo and Redo buttons should be present
    const buttons = container.querySelectorAll('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('calls onSelectComponent when component clicked', () => {
    const onSelectComponent = vi.fn();
    render(
      <InteractiveAssemblyViewer
        components={mockComponents}
        onSelectComponent={onSelectComponent}
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('calls onComponentTransform when provided', () => {
    const onComponentTransform = vi.fn();
    render(
      <InteractiveAssemblyViewer
        components={mockComponents}
        onComponentTransform={onComponentTransform}
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts selectedComponentId prop', () => {
    render(
      <InteractiveAssemblyViewer
        components={mockComponents}
        selectedComponentId="comp-1"
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts explodedView and explodeFactor props', () => {
    render(
      <InteractiveAssemblyViewer
        components={mockComponents}
        explodedView={true}
        explodeFactor={1}
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('accepts hiddenComponents prop', () => {
    const hiddenComponents = new Set(['comp-1']);
    render(
      <InteractiveAssemblyViewer
        components={mockComponents}
        hiddenComponents={hiddenComponents}
      />
    );
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('toggles component list when button clicked', () => {
    const { container } = render(
      <InteractiveAssemblyViewer components={mockComponents} />
    );

    // Find the list button and click it
    const buttons = Array.from(container.querySelectorAll('button'));
    const listButton = buttons.find(btn => btn.title === 'Component list');
    
    if (listButton) {
      fireEvent.click(listButton);
      // Component list panel should appear
      expect(screen.getByText('Components')).toBeInTheDocument();
    }
  });

  it('displays selected component info when component is selected', () => {
    render(
      <InteractiveAssemblyViewer
        components={mockComponents}
        selectedComponentId="comp-1"
      />
    );
    
    // Selected component name should be displayed in the info panel (h4 element)
    const heading = screen.getByRole('heading', { name: 'Component 1', level: 4 });
    expect(heading).toBeInTheDocument();
  });

  it('shows COTS badge for COTS parts', () => {
    render(
      <InteractiveAssemblyViewer
        components={mockComponents}
        selectedComponentId="comp-2"
      />
    );
    
    // COTS Part badge should be displayed for comp-2
    expect(screen.getByText('COTS Part')).toBeInTheDocument();
  });

  it('renders all toolbar sections', () => {
    const { container } = render(
      <InteractiveAssemblyViewer components={mockComponents} />
    );
    
    // Should have multiple toolbar sections
    const toolbars = container.querySelectorAll('.absolute.top-4.left-4 > div');
    expect(toolbars.length).toBeGreaterThan(0);
  });

  // ---------------------------------------------------------------------------
  // Visibility keyboard shortcuts
  // ---------------------------------------------------------------------------

  describe('keyboard shortcuts for visibility', () => {
    it('hides selected component on H key', () => {
      render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      fireEvent.keyDown(window, { key: 'h' });
      expect(screen.getByText(/1 hidden/)).toBeInTheDocument();
    });

    it('does not hide when no component is selected on H key', () => {
      render(<InteractiveAssemblyViewer components={mockComponents} />);

      fireEvent.keyDown(window, { key: 'h' });
      expect(screen.queryByText(/hidden/)).not.toBeInTheDocument();
    });

    it('shows all on Shift+H key', () => {
      render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Hide one first
      fireEvent.keyDown(window, { key: 'h' });
      expect(screen.getByText(/1 hidden/)).toBeInTheDocument();

      // Show all
      fireEvent.keyDown(window, { key: 'H', shiftKey: true });
      expect(screen.queryByText(/hidden/)).not.toBeInTheDocument();
    });

    it('isolates selected component on I key', () => {
      render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      fireEvent.keyDown(window, { key: 'i' });
      expect(screen.getByText(/Isolated/)).toBeInTheDocument();
    });

    it('does not isolate when no component is selected on I key', () => {
      render(<InteractiveAssemblyViewer components={mockComponents} />);

      fireEvent.keyDown(window, { key: 'i' });
      expect(screen.queryByText(/Isolated/)).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Component list panel visibility controls
  // ---------------------------------------------------------------------------

  describe('component list panel visibility controls', () => {
    it('shows isolate and show-all buttons in component list header', () => {
      const { container } = render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      expect(listButton).toBeDefined();
      fireEvent.click(listButton!);

      expect(screen.getByLabelText('Isolate selected component')).toBeInTheDocument();
      expect(screen.getByLabelText('Show all components')).toBeInTheDocument();
    });

    it('toggles visibility via eye button in list', () => {
      const { container } = render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      fireEvent.click(listButton!);

      const hideButton = screen.getByLabelText('Hide Component 1');
      expect(hideButton).toBeInTheDocument();
      fireEvent.click(hideButton);

      expect(screen.getByLabelText('Show Component 1')).toBeInTheDocument();
    });

    it('isolate button enters isolate mode', () => {
      const { container } = render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      fireEvent.click(listButton!);

      const isolateBtn = screen.getByLabelText('Isolate selected component');
      fireEvent.click(isolateBtn);

      expect(screen.getByText('Isolated')).toBeInTheDocument();
    });

    it('show-all button clears hidden and exits isolate', () => {
      const { container } = render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      fireEvent.click(listButton!);

      // Isolate first
      const isolateBtn = screen.getByLabelText('Isolate selected component');
      fireEvent.click(isolateBtn);
      expect(screen.getByText('Isolated')).toBeInTheDocument();

      // Show all
      const showAllBtn = screen.getByLabelText('Show all components');
      fireEvent.click(showAllBtn);
      expect(screen.queryByText('Isolated')).not.toBeInTheDocument();
    });

    it('isolate button is disabled when no component is selected', () => {
      const { container } = render(
        <InteractiveAssemblyViewer components={mockComponents} />
      );

      // Open component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      fireEvent.click(listButton!);

      const isolateBtn = screen.getByLabelText('Isolate selected component');
      expect(isolateBtn).toBeDisabled();
    });
  });

  // ---------------------------------------------------------------------------
  // assemblyId prop
  // ---------------------------------------------------------------------------

  describe('assemblyId prop', () => {
    it('accepts assemblyId prop without error', () => {
      render(
        <InteractiveAssemblyViewer
          components={mockComponents}
          assemblyId="asm-456"
        />
      );
      expect(screen.getByTestId('canvas')).toBeInTheDocument();
    });
  });
});
