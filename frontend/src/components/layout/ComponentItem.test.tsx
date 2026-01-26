/**
 * ComponentItem Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ComponentItem } from './ComponentItem';

describe('ComponentItem', () => {
  const mockComponent = {
    id: 'comp-1',
    name: 'Raspberry Pi 4',
    width: 85,
    depth: 56,
    height: 17,
    thumbnailUrl: 'http://example.com/thumb.png',
  };

  const defaultProps = {
    component: mockComponent,
    onDragStart: vi.fn(),
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders component name', () => {
    render(<ComponentItem {...defaultProps} />);
    expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
  });

  it('displays dimensions', () => {
    render(<ComponentItem {...defaultProps} />);
    expect(screen.getByText('85 × 56 × 17 mm')).toBeInTheDocument();
  });

  it('shows thumbnail when available', () => {
    render(<ComponentItem {...defaultProps} />);
    
    const img = screen.getByAltText('Raspberry Pi 4');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'http://example.com/thumb.png');
  });

  it('shows placeholder when no thumbnail', () => {
    const componentWithoutThumb = { ...mockComponent, thumbnailUrl: undefined };
    render(<ComponentItem {...defaultProps} component={componentWithoutThumb} />);
    
    // Should have an SVG placeholder instead
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('is draggable by default', () => {
    render(<ComponentItem {...defaultProps} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('[draggable]');
    expect(item).toHaveAttribute('draggable', 'true');
  });

  it('is not draggable when disabled', () => {
    render(<ComponentItem {...defaultProps} disabled={true} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('[draggable]');
    expect(item).toHaveAttribute('draggable', 'false');
  });

  it('calls onDragStart when drag starts', () => {
    render(<ComponentItem {...defaultProps} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('[draggable]');
    
    const dataTransfer = {
      setData: vi.fn(),
      effectAllowed: '',
    };
    
    fireEvent.dragStart(item!, { dataTransfer });
    
    expect(defaultProps.onDragStart).toHaveBeenCalledWith(mockComponent);
    expect(dataTransfer.setData).toHaveBeenCalledWith('component', JSON.stringify(mockComponent));
  });

  it('does not call onDragStart when disabled', () => {
    render(<ComponentItem {...defaultProps} disabled={true} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('[draggable]');
    
    const dataTransfer = {
      setData: vi.fn(),
      effectAllowed: '',
    };
    
    fireEvent.dragStart(item!, { dataTransfer });
    
    expect(defaultProps.onDragStart).not.toHaveBeenCalled();
  });

  it('has grab cursor when not disabled', () => {
    render(<ComponentItem {...defaultProps} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('div[class*="cursor-grab"]');
    expect(item).toBeInTheDocument();
  });

  it('has not-allowed cursor when disabled', () => {
    render(<ComponentItem {...defaultProps} disabled={true} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('div[class*="cursor-not-allowed"]');
    expect(item).toBeInTheDocument();
  });

  it('has reduced opacity when disabled', () => {
    render(<ComponentItem {...defaultProps} disabled={true} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('div[class*="opacity-50"]');
    expect(item).toBeInTheDocument();
  });

  it('shows drag handle icon', () => {
    render(<ComponentItem {...defaultProps} />);
    
    // Should have a drag handle SVG icon
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has hover effect when not disabled', () => {
    render(<ComponentItem {...defaultProps} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('div[class*="hover:border-blue-500"]');
    expect(item).toBeInTheDocument();
  });

  it('does not have hover effect when disabled', () => {
    render(<ComponentItem {...defaultProps} disabled={true} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('div');
    expect(item).not.toHaveClass('hover:border-blue-500');
  });

  it('sets dataTransfer.effectAllowed to copy', () => {
    render(<ComponentItem {...defaultProps} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('[draggable]');
    
    const dataTransfer = {
      setData: vi.fn(),
      effectAllowed: '',
    };
    
    fireEvent.dragStart(item!, { dataTransfer });
    
    expect(dataTransfer.effectAllowed).toBe('copy');
  });

  it('prevents drag start event when disabled', () => {
    render(<ComponentItem {...defaultProps} disabled={true} />);
    
    const item = screen.getByText('Raspberry Pi 4').closest('[draggable]');
    
    const preventDefault = vi.fn();
    const dataTransfer = {
      setData: vi.fn(),
      effectAllowed: '',
    };
    
    fireEvent.dragStart(item!, { dataTransfer, preventDefault });
    
    // The drag should be prevented
    expect(dataTransfer.setData).not.toHaveBeenCalled();
  });
});
