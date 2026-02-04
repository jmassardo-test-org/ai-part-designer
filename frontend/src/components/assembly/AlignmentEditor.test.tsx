/**
 * AlignmentEditor Component Tests
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AlignmentEditor } from './AlignmentEditor';

// Mock react-three/fiber
vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="canvas">{children}</div>
  ),
  useFrame: vi.fn(),
  useThree: () => ({
    camera: { position: { set: vi.fn() } },
    gl: { domElement: document.createElement('canvas') },
    scene: {},
  }),
}));

// Mock react-three/drei
vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Environment: () => null,
  Grid: () => null,
  Html: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

// Mock THREE - use actual class constructors inside the factory to avoid hoisting issues
vi.mock('three', () => {
  class MockVector3 {
    x = 0;
    y = 0;
    z = 0;
    constructor(x = 0, y = 0, z = 0) {
      this.x = x;
      this.y = y;
      this.z = z;
    }
  }
  return {
    Vector3: MockVector3,
    BufferGeometry: vi.fn(),
    BoxGeometry: vi.fn(),
    MeshStandardMaterial: vi.fn(),
    MeshBasicMaterial: vi.fn(),
  };
});

// Mock three-stdlib - define class inside factory
vi.mock('three-stdlib', () => {
  return {
    STLLoader: class {
      load = vi.fn();
    },
  };
});

// Mock alignment API
const mockAlign = vi.fn();
const mockPreview = vi.fn();

vi.mock('@/lib/api/alignment', () => ({
  alignmentApi: {
    align: (...args: unknown[]) => mockAlign(...args),
    preview: (...args: unknown[]) => mockPreview(...args),
  },
  ALIGNMENT_PRESETS: [
    { mode: 'CENTER', label: 'Center All', description: 'Align centers', icon: 'target' },
    { mode: 'ORIGIN', label: 'Align to Origin', description: 'Move to origin', icon: 'crosshair' },
    { mode: 'STACK_Z', label: 'Stack Vertical', description: 'Stack vertically', icon: 'layers' },
    { mode: 'STACK_X', label: 'Stack Horizontal X', description: 'Stack X', icon: 'arrow-right' },
    { mode: 'STACK_Y', label: 'Stack Horizontal Y', description: 'Stack Y', icon: 'arrow-up' },
    { mode: 'FACE', label: 'Align Faces', description: 'Align faces', icon: 'square' },
    { mode: 'EDGE', label: 'Align Edges', description: 'Align edges', icon: 'align-left' },
  ],
}));

const mockParts = [
  { id: 'part-1', name: 'Enclosure Base', filePath: '/files/base.step', color: '#3B82F6' },
  { id: 'part-2', name: 'Lid', filePath: '/files/lid.step', color: '#10B981' },
  { id: 'part-3', name: 'PCB Mount', filePath: '/files/pcb.step', color: '#F59E0B' },
];

describe('AlignmentEditor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAlign.mockResolvedValue({
      success: true,
      output_path: '/output/aligned.step',
      mode: 'CENTER',
      file_count: 3,
      combined_bounds: {
        min_x: 0, min_y: 0, min_z: 0,
        max_x: 100, max_y: 100, max_z: 50,
        center_x: 50, center_y: 50, center_z: 25,
      },
      transformations: [],
      message: 'Alignment complete',
    });
  });

  describe('Rendering', () => {
    it('renders the alignment editor title', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('Alignment Editor')).toBeInTheDocument();
    });

    it('displays parts list with count', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText(/Parts \(3\)/)).toBeInTheDocument();
    });

    it('renders all part names', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('Enclosure Base')).toBeInTheDocument();
      expect(screen.getByText('Lid')).toBeInTheDocument();
      expect(screen.getByText('PCB Mount')).toBeInTheDocument();
    });

    it('renders alignment mode buttons', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('Center All')).toBeInTheDocument();
      expect(screen.getByText('Align to Origin')).toBeInTheDocument();
      expect(screen.getByText('Stack Vertical')).toBeInTheDocument();
    });

    it('renders the 3D canvas', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByTestId('canvas')).toBeInTheDocument();
    });
  });

  describe('Reference Part Selection', () => {
    it('shows first part as reference by default', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('Reference')).toBeInTheDocument();
    });

    it('highlights the reference part', () => {
      render(<AlignmentEditor parts={mockParts} />);
      // First part should have Reference label
      const partsList = screen.getAllByText('Reference');
      expect(partsList.length).toBe(1);
    });
  });

  describe('Alignment Mode Selection', () => {
    it('selects CENTER mode by default', () => {
      render(<AlignmentEditor parts={mockParts} />);
      const centerButton = screen.getByText('Center All').closest('button');
      expect(centerButton).toHaveClass('border-blue-500');
    });

    it('changes mode when clicking different preset', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Stack Vertical'));
      
      const stackButton = screen.getByText('Stack Vertical').closest('button');
      expect(stackButton).toHaveClass('border-blue-500');
    });

    it('shows gap control for stacking modes', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Stack Vertical'));
      
      expect(screen.getByText('Gap Between Parts')).toBeInTheDocument();
    });

    it('hides gap control for non-stacking modes', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.queryByText('Gap Between Parts')).not.toBeInTheDocument();
    });
  });

  describe('View Options', () => {
    it('shows view options section', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('View Options')).toBeInTheDocument();
    });

    it('has Show Grid checkbox', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('Show Grid')).toBeInTheDocument();
    });

    it('has Show Bounding Boxes checkbox', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('Show Bounding Boxes')).toBeInTheDocument();
    });

    it('toggles grid visibility', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      const gridCheckbox = screen.getByText('Show Grid').previousElementSibling as HTMLInputElement;
      expect(gridCheckbox.checked).toBe(true);
      
      await user.click(gridCheckbox);
      expect(gridCheckbox.checked).toBe(false);
    });
  });

  describe('Alignment Execution', () => {
    it('renders Apply Alignment button', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.getByText('Apply Alignment')).toBeInTheDocument();
    });

    it('calls alignment API when Apply clicked', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      expect(mockAlign).toHaveBeenCalledWith({
        file_paths: ['/files/base.step', '/files/lid.step', '/files/pcb.step'],
        mode: 'CENTER',
        reference_index: 0,
        gap: 0,
      });
    });

    it('shows loading state while aligning', async () => {
      mockAlign.mockImplementation(() => new Promise(() => {})); // Never resolves
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      expect(screen.getByText('Aligning...')).toBeInTheDocument();
    });

    it('shows success message after alignment', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      await waitFor(() => {
        expect(screen.getByText('Alignment complete')).toBeInTheDocument();
      });
    });

    it('shows download button after successful alignment', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      await waitFor(() => {
        expect(screen.getByText('Download')).toBeInTheDocument();
      });
    });

    it('calls onAlignmentComplete callback', async () => {
      const onComplete = vi.fn();
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} onAlignmentComplete={onComplete} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      await waitFor(() => {
        expect(onComplete).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('shows error when alignment fails', async () => {
      mockAlign.mockRejectedValue(new Error('Alignment service unavailable'));
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      await waitFor(() => {
        expect(screen.getByText('Alignment service unavailable')).toBeInTheDocument();
      });
    });

    it('disables button when less than 2 parts', () => {
      render(<AlignmentEditor parts={[mockParts[0]]} />);
      
      const button = screen.getByText('Apply Alignment').closest('button');
      expect(button).toBeDisabled();
    });
  });

  describe('Reset', () => {
    it('shows Reset button after alignment', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      await waitFor(() => {
        expect(screen.getByText('Reset')).toBeInTheDocument();
      });
    });

    it('clears alignment result on reset', async () => {
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} />);
      
      await user.click(screen.getByText('Apply Alignment'));
      
      await waitFor(() => {
        expect(screen.getByText('Download')).toBeInTheDocument();
      });
      
      await user.click(screen.getByText('Reset'));
      
      expect(screen.queryByText('Download')).not.toBeInTheDocument();
    });
  });

  describe('Close', () => {
    it('renders close button when onClose provided', () => {
      const onClose = vi.fn();
      render(<AlignmentEditor parts={mockParts} onClose={onClose} />);
      expect(screen.getByText('Close')).toBeInTheDocument();
    });

    it('calls onClose when close button clicked', async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(<AlignmentEditor parts={mockParts} onClose={onClose} />);
      
      await user.click(screen.getByText('Close'));
      
      expect(onClose).toHaveBeenCalled();
    });

    it('does not render close button when onClose not provided', () => {
      render(<AlignmentEditor parts={mockParts} />);
      expect(screen.queryByText('Close')).not.toBeInTheDocument();
    });
  });
});
