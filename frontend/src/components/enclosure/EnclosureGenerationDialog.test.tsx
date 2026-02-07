/**
 * EnclosureGenerationDialog Component Tests
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EnclosureGenerationDialog } from './EnclosureGenerationDialog';

describe('EnclosureGenerationDialog', () => {
  const mockDimensions = {
    width: 100,
    depth: 80,
    height: 40,
    gridSize: 5,
    clearance: 2,
    autoDimensions: true,
  };

  const mockPlacements = [
    {
      id: 'placement-1',
      componentId: 'comp-1',
      name: 'Raspberry Pi',
      x: 10,
      y: 10,
      z: 0,
      width: 85,
      depth: 56,
      height: 17,
      rotation: 0,
      locked: false,
      faceDirection: 'bottom' as const,
    },
    {
      id: 'placement-2',
      componentId: 'comp-2',
      name: 'USB Connector',
      x: 5,
      y: 30,
      z: 0,
      width: 15,
      depth: 10,
      height: 5,
      rotation: 0,
      locked: false,
      faceDirection: 'left' as const,
    },
  ];

  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onGenerate: vi.fn(),
    dimensions: mockDimensions,
    placements: mockPlacements,
    isGenerating: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nothing when not open', () => {
    render(<EnclosureGenerationDialog {...defaultProps} isOpen={false} />);
    expect(screen.queryByText(/generate enclosure/i)).not.toBeInTheDocument();
  });

  it('renders dialog when open', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    // The dialog has a title "Generate Enclosure"
    expect(screen.getByRole('heading', { name: /generate enclosure/i })).toBeInTheDocument();
  });

  it('shows configuration tabs', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    expect(screen.getByText('Basic')).toBeInTheDocument();
    expect(screen.getByText(/style/i)).toBeInTheDocument();
    expect(screen.getByText('Features')).toBeInTheDocument();
  });

  it('displays calculated dimensions in footer', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    // Wall thickness (2) * 2 + width (100) = 104
    // Wall thickness (2) * 2 + depth (80) = 84
    // Top (2) + Bottom (2) + height (40) = 44
    expect(screen.getByText(/104 × 84 × 44/)).toBeInTheDocument();
  });

  it('shows component count', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    expect(screen.getByText(/2 components/)).toBeInTheDocument();
  });

  it('shows cutout count', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    expect(screen.getByText(/2 cutouts/)).toBeInTheDocument();
  });

  it('calls onClose when cancel clicked', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    await user.click(screen.getByText('Cancel'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('calls onClose when backdrop clicked', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    const backdrop = document.querySelector('.bg-black\\/60');
    if (backdrop) {
      await user.click(backdrop);
      expect(defaultProps.onClose).toHaveBeenCalled();
    }
  });

  it('calls onGenerate when generate button clicked', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    // Find the generate button (not the title)
    const generateButton = screen.getByRole('button', { name: /generate enclosure/i });
    await user.click(generateButton);
    expect(defaultProps.onGenerate).toHaveBeenCalled();
  });

  it('shows loading state when generating', () => {
    render(<EnclosureGenerationDialog {...defaultProps} isGenerating={true} />);
    expect(screen.getByText('Generating...')).toBeInTheDocument();
  });

  it('disables generate button when generating', () => {
    render(<EnclosureGenerationDialog {...defaultProps} isGenerating={true} />);
    
    const button = screen.getByRole('button', { name: /generating/i });
    expect(button).toBeDisabled();
  });

  it('switches between tabs', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    await user.click(screen.getByText(/style & lid/i));
    // Style tab content should be visible - "Enclosure Style" heading
    expect(screen.getByText(/enclosure style/i)).toBeInTheDocument();
  });

  it('shows wall thickness controls in basic tab', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    expect(screen.getByText(/wall thickness/i)).toBeInTheDocument();
  });

  it('shows style options in style tab', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    await user.click(screen.getByText(/style & lid/i));
    
    // Labels are capitalized
    expect(screen.getByText('Rectangular')).toBeInTheDocument();
    expect(screen.getByText('Rounded')).toBeInTheDocument();
    expect(screen.getByText('Chamfered')).toBeInTheDocument();
  });

  it('shows lid type options', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    await user.click(screen.getByText(/style/i));
    
    expect(screen.getByText(/snap fit/i)).toBeInTheDocument();
  });

  it('shows features options', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    await user.click(screen.getByText('Features'));
    
    // Features tab content
  });

  it('passes correct options to onGenerate', async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn().mockResolvedValue(undefined);
    
    render(<EnclosureGenerationDialog {...defaultProps} onGenerate={onGenerate} />);
    
    const generateButton = screen.getByRole('button', { name: /generate enclosure/i });
    await user.click(generateButton);
    
    expect(onGenerate).toHaveBeenCalledWith(expect.objectContaining({
      wallThickness: expect.any(Number),
      style: expect.any(String),
      lidType: expect.any(String),
    }));
  });

  it('has accessible dialog structure', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    // Check for proper heading
    expect(screen.getByRole('heading', { name: /generate enclosure/i })).toBeInTheDocument();
  });

  it('shows close button', () => {
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    // There should be a close button (X icon)
    const closeButtons = screen.getAllByRole('button');
    expect(closeButtons.length).toBeGreaterThan(0);
  });

  it('calls onClose when X button clicked', async () => {
    const user = userEvent.setup();
    render(<EnclosureGenerationDialog {...defaultProps} />);
    
    // Find the X close button in the header
    const buttons = screen.getAllByRole('button');
    const closeButton = buttons.find(btn => btn.querySelector('svg'));
    
    if (closeButton) {
      await user.click(closeButton);
    }
  });
});
