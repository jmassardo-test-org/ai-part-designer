/**
 * LayoutEditor Component Tests
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LayoutEditor } from './LayoutEditor';

// Create refs to store callback props
let canvasCallbacks: any = {};
let toolbarCallbacks: any = {};

// Mock child components
vi.mock('./LayoutCanvas', () => ({
  LayoutCanvas: (props: any) => {
    canvasCallbacks = props;
    return (
      <div data-testid="layout-canvas">
        <button data-testid="select-comp" onClick={() => props.onSelect('placement-1')}>Select</button>
        <button data-testid="move-comp" onClick={() => props.onMove('placement-1', 50, 50)}>Move</button>
        <button data-testid="rotate-comp" onClick={() => props.onRotate('placement-1')}>Rotate</button>
        <button data-testid="deselect" onClick={() => props.onSelect(null)}>Deselect</button>
        {props.selectedId && <div data-testid="selected">{props.selectedId}</div>}
      </div>
    );
  },
}));

vi.mock('./LayoutToolbar', () => ({
  LayoutToolbar: (props: any) => {
    toolbarCallbacks = props;
    return (
      <div data-testid="layout-toolbar">
        <button data-testid="zoom-in" onClick={props.onZoomIn}>Zoom In</button>
        <button data-testid="zoom-out" onClick={props.onZoomOut}>Zoom Out</button>
        <button data-testid="zoom-reset" onClick={props.onZoomReset}>Reset</button>
        <button data-testid="rotate" onClick={props.onRotateSelected} disabled={!props.hasSelection}>Rotate</button>
        <button data-testid="delete" onClick={props.onDeleteSelected} disabled={!props.hasSelection}>Delete</button>
        <button data-testid="lock" onClick={props.onToggleLock} disabled={!props.hasSelection}>Lock</button>
        <button data-testid="auto-layout" onClick={() => props.onAutoLayout('packed')} disabled={props.isAutoLayouting}>
          {props.isAutoLayouting ? 'Auto Layout...' : 'Auto Layout'}
        </button>
        <button data-testid="validate" onClick={props.onValidate} disabled={props.isValidating}>
          {props.isValidating ? 'Validating...' : 'Validate'}
        </button>
      </div>
    );
  },
}));

vi.mock('./LayoutSidebar', () => ({
  LayoutSidebar: () => <div data-testid="layout-sidebar">Sidebar</div>,
}));

describe('LayoutEditor', () => {
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
  ];

  const mockComponents = [
    {
      id: 'comp-1',
      name: 'Raspberry Pi',
      width: 85,
      depth: 56,
      height: 17,
    },
  ];

  const defaultProps = {
    layoutId: 'layout-1',
    dimensions: mockDimensions,
    placements: mockPlacements,
    availableComponents: mockComponents,
    onDimensionsChange: vi.fn(),
    onAddPlacement: vi.fn(),
    onUpdatePlacement: vi.fn(),
    onRemovePlacement: vi.fn(),
    onAutoLayout: vi.fn().mockResolvedValue(undefined),
    onValidate: vi.fn().mockResolvedValue({ valid: true, errors: [], warnings: [] }),
    isLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    canvasCallbacks = {};
    toolbarCallbacks = {};
  });

  it('renders main layout structure', () => {
    render(<LayoutEditor {...defaultProps} />);
    
    expect(screen.getByTestId('layout-toolbar')).toBeInTheDocument();
    expect(screen.getByTestId('layout-canvas')).toBeInTheDocument();
    expect(screen.getByTestId('layout-sidebar')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    render(<LayoutEditor {...defaultProps} isLoading={true} />);
    
    expect(screen.getByText(/loading layout/i)).toBeInTheDocument();
  });

  it('handles component selection', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    
    expect(screen.getByTestId('selected')).toHaveTextContent('placement-1');
  });

  it('handles component deselection', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    expect(screen.getByTestId('selected')).toBeInTheDocument();
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('deselect'));
    });
    expect(screen.queryByTestId('selected')).not.toBeInTheDocument();
  });

  it('calls onUpdatePlacement when component moved', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('move-comp'));
    });
    
    expect(defaultProps.onUpdatePlacement).toHaveBeenCalledWith('placement-1', { x: 50, y: 50 });
  });

  it('handles rotate from toolbar', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    // First select a component
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    
    // Then rotate
    await act(async () => {
      fireEvent.click(screen.getByTestId('rotate'));
    });
    
    expect(defaultProps.onUpdatePlacement).toHaveBeenCalledWith('placement-1', { rotation: 90 });
  });

  it('handles delete from toolbar', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('delete'));
    });
    
    expect(defaultProps.onRemovePlacement).toHaveBeenCalledWith('placement-1');
  });

  it('handles lock toggle from toolbar', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    await act(async () => {
      fireEvent.click(screen.getByTestId('lock'));
    });
    
    expect(defaultProps.onUpdatePlacement).toHaveBeenCalledWith('placement-1', { locked: true });
  });

  it('handles auto-layout', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('auto-layout'));
    });
    
    await waitFor(() => {
      expect(defaultProps.onAutoLayout).toHaveBeenCalledWith('packed');
    });
  });

  it('handles validate', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('validate'));
    });
    
    await waitFor(() => {
      expect(defaultProps.onValidate).toHaveBeenCalled();
    });
  });

  it('disables toolbar buttons when no selection', () => {
    render(<LayoutEditor {...defaultProps} />);
    
    expect(screen.getByTestId('rotate')).toBeDisabled();
    expect(screen.getByTestId('delete')).toBeDisabled();
    expect(screen.getByTestId('lock')).toBeDisabled();
  });

  it('enables toolbar buttons when component selected', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    
    expect(screen.getByTestId('rotate')).not.toBeDisabled();
    expect(screen.getByTestId('delete')).not.toBeDisabled();
    expect(screen.getByTestId('lock')).not.toBeDisabled();
  });

  it('handles keyboard shortcut for delete', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    // Select component first
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    
    // Press Delete key
    await act(async () => {
      fireEvent.keyDown(window, { key: 'Delete' });
    });
    
    expect(defaultProps.onRemovePlacement).toHaveBeenCalled();
  });

  it('handles keyboard shortcut for rotate', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    
    await act(async () => {
      fireEvent.keyDown(window, { key: 'r' });
    });
    
    expect(defaultProps.onUpdatePlacement).toHaveBeenCalledWith('placement-1', { rotation: 90 });
  });

  it('handles keyboard shortcut for lock', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    
    await act(async () => {
      fireEvent.keyDown(window, { key: 'l' });
    });
    
    expect(defaultProps.onUpdatePlacement).toHaveBeenCalledWith('placement-1', { locked: true });
  });

  it('handles escape to deselect', async () => {
    render(<LayoutEditor {...defaultProps} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('select-comp'));
    });
    expect(screen.getByTestId('selected')).toBeInTheDocument();
    
    await act(async () => {
      fireEvent.keyDown(window, { key: 'Escape' });
    });
    
    expect(screen.queryByTestId('selected')).not.toBeInTheDocument();
  });

  it('shows validation results', async () => {
    const validateFn = vi.fn().mockResolvedValue({
      valid: false,
      errors: [{ message: 'Components overlap' }],
      warnings: [],
    });
    
    render(<LayoutEditor {...defaultProps} onValidate={validateFn} />);
    
    await act(async () => {
      fireEvent.click(screen.getByTestId('validate'));
    });
    
    await waitFor(() => {
      expect(validateFn).toHaveBeenCalled();
    });
  });
});
