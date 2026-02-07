/**
 * Tests for DeleteModal Component
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DeleteModal } from './DeleteModal';

// Mock design
const mockDesign = {
  id: 'design-1',
  name: 'Test Design',
  description: 'A test design',
  project_id: 'project-1',
  project_name: 'Test Project',
  source_type: 'ai_generated',
  status: 'completed',
  thumbnail_url: 'https://example.com/thumb.png',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('DeleteModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    design: mockDesign,
    onConfirm: vi.fn().mockResolvedValue({
      undoToken: 'test-token',
      expiresAt: '2024-01-01T00:01:00Z',
    }),
  };

  it('renders when open', () => {
    render(<DeleteModal {...defaultProps} />);

    expect(screen.getByText('Delete design')).toBeInTheDocument();
  });

  it('displays design name', () => {
    render(<DeleteModal {...defaultProps} />);

    expect(screen.getByText('Test Design')).toBeInTheDocument();
  });

  it('displays project name', () => {
    render(<DeleteModal {...defaultProps} />);

    expect(screen.getByText('in Test Project')).toBeInTheDocument();
  });

  it('shows warning about undo capability', () => {
    render(<DeleteModal {...defaultProps} />);

    expect(screen.getByText(/This action can be undone/)).toBeInTheDocument();
    expect(screen.getByText(/30 seconds/)).toBeInTheDocument();
  });

  it('displays thumbnail when available', () => {
    render(<DeleteModal {...defaultProps} />);

    const img = screen.getByAltText('Test Design');
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', 'https://example.com/thumb.png');
  });

  it('shows placeholder when no thumbnail', () => {
    render(
      <DeleteModal
        {...defaultProps}
        design={{ ...mockDesign, thumbnail_url: null }}
      />
    );

    expect(screen.queryByAltText('Test Design')).not.toBeInTheDocument();
  });

  it('calls onConfirm when delete is clicked', async () => {
    const user = userEvent.setup();
    render(<DeleteModal {...defaultProps} />);

    await user.click(screen.getByTestId('confirm-delete'));

    expect(defaultProps.onConfirm).toHaveBeenCalled();
  });

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<DeleteModal {...defaultProps} />);

    await user.click(screen.getByText('Cancel'));

    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('disables buttons when loading', () => {
    render(<DeleteModal {...defaultProps} isLoading />);

    expect(screen.getByText('Cancel')).toBeDisabled();
    expect(screen.getByText('Deleting...')).toBeInTheDocument();
  });

  it('shows error message when delete fails', async () => {
    const user = userEvent.setup();
    const failingConfirm = vi.fn().mockRejectedValue(new Error('Network error'));

    render(<DeleteModal {...defaultProps} onConfirm={failingConfirm} />);

    await user.click(screen.getByTestId('confirm-delete'));

    expect(screen.getByText('Network error')).toBeInTheDocument();
  });

  it('closes modal after successful delete', async () => {
    const user = userEvent.setup();
    render(<DeleteModal {...defaultProps} />);

    await user.click(screen.getByTestId('confirm-delete'));

    expect(defaultProps.onClose).toHaveBeenCalled();
  });
});
