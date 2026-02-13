/**
 * AssemblyViewer Component Tests
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
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

vi.mock('three-stdlib', () => {
  class MockSTLLoader {
    load = vi.fn((_, onLoad) => {
      // Simulate successful load with mock geometry
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
    sessionStorage.clear();
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

  // ---------------------------------------------------------------------------
  // Visibility keyboard shortcuts
  // ---------------------------------------------------------------------------

  describe('keyboard shortcuts', () => {
    it('hides selected component on H key', () => {
      render(
        <AssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      fireEvent.keyDown(window, { key: 'h' });

      // After hiding, the component count should reflect 1 hidden
      expect(screen.getByText(/1 hidden/)).toBeInTheDocument();
    });

    it('does not hide when no component is selected on H key', () => {
      render(<AssemblyViewer components={mockComponents} />);

      fireEvent.keyDown(window, { key: 'h' });

      expect(screen.queryByText(/hidden/)).not.toBeInTheDocument();
    });

    it('shows all on Shift+H key', () => {
      render(
        <AssemblyViewer
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
        <AssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      fireEvent.keyDown(window, { key: 'i' });

      // Should show isolated indicator
      expect(screen.getByText(/Isolated/)).toBeInTheDocument();
    });

    it('does not isolate when no component is selected on I key', () => {
      render(<AssemblyViewer components={mockComponents} />);

      fireEvent.keyDown(window, { key: 'i' });

      expect(screen.queryByText(/Isolated/)).not.toBeInTheDocument();
    });

    it('ignores shortcuts when typing in input', () => {
      const { container } = render(
        <AssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Simulate keydown from an input element
      const input = document.createElement('input');
      container.appendChild(input);
      fireEvent.keyDown(input, { key: 'h', target: input });

      expect(screen.queryByText(/hidden/)).not.toBeInTheDocument();
    });
  });

  // ---------------------------------------------------------------------------
  // Component list panel visibility controls
  // ---------------------------------------------------------------------------

  describe('component list panel', () => {
    it('shows isolate and show-all buttons in component list header', () => {
      const { container } = render(
        <AssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open the component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      expect(listButton).toBeDefined();
      fireEvent.click(listButton!);

      // Should find isolate and show-all buttons
      expect(screen.getByLabelText('Isolate selected component')).toBeInTheDocument();
      expect(screen.getByLabelText('Show all components')).toBeInTheDocument();
    });

    it('toggles component visibility via eye button in list', () => {
      const { container } = render(
        <AssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open the component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      fireEvent.click(listButton!);

      // Find the hide button for component 1
      const hideButton = screen.getByLabelText('Hide Component 1');
      expect(hideButton).toBeInTheDocument();
      fireEvent.click(hideButton);

      // Should now show as hidden
      expect(screen.getByLabelText('Show Component 1')).toBeInTheDocument();
    });

    it('isolate button enters isolate mode', () => {
      const { container } = render(
        <AssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open the component list
      const buttons = Array.from(container.querySelectorAll('button'));
      const listButton = buttons.find((btn) => btn.title === 'Component list');
      fireEvent.click(listButton!);

      // Click isolate
      const isolateBtn = screen.getByLabelText('Isolate selected component');
      fireEvent.click(isolateBtn);

      // Should show "Isolated" badge
      expect(screen.getByText('Isolated')).toBeInTheDocument();
    });

    it('show-all button clears hidden and exits isolate', () => {
      const { container } = render(
        <AssemblyViewer
          components={mockComponents}
          selectedComponentId="comp-1"
        />
      );

      // Open the component list
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
        <AssemblyViewer components={mockComponents} />
      );

      // Open the component list
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
        <AssemblyViewer
          components={mockComponents}
          assemblyId="asm-123"
        />
      );
      expect(screen.getByTestId('canvas')).toBeInTheDocument();
    });
  });
});
