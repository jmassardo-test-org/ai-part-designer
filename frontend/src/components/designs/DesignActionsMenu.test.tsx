/**
 * Tests for DesignActionsMenu Component
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DesignActionsMenu, RenameModal } from './DesignActionsMenu';

// Mock design and projects
const mockDesign = {
  id: 'design-1',
  name: 'Test Design',
  description: 'A test design',
  project_id: 'project-1',
  project_name: 'Test Project',
  source_type: 'ai_generated',
  status: 'completed',
  thumbnail_url: null,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockProjects = [
  {
    id: 'project-1',
    name: 'Test Project',
    description: null,
    design_count: 5,
    thumbnail_url: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'project-2',
    name: 'Other Project',
    description: null,
    design_count: 3,
    thumbnail_url: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

describe('DesignActionsMenu', () => {
  const defaultProps = {
    design: mockDesign,
    projects: mockProjects,
    onRename: vi.fn(),
    onCopy: vi.fn(),
    onMove: vi.fn(),
    onDelete: vi.fn(),
    onVersions: vi.fn(),
  };

  it('renders the trigger button', () => {
    render(<DesignActionsMenu {...defaultProps} />);

    expect(screen.getByTestId('design-actions-trigger')).toBeInTheDocument();
  });

  it('opens menu when trigger is clicked', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} />);

    await user.click(screen.getByTestId('design-actions-trigger'));

    expect(screen.getByTestId('design-actions-menu')).toBeInTheDocument();
  });

  it('calls onRename when rename is clicked', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} />);

    await user.click(screen.getByTestId('design-actions-trigger'));
    await user.click(screen.getByTestId('action-rename'));

    expect(defaultProps.onRename).toHaveBeenCalledWith(mockDesign);
  });

  it('calls onCopy when copy is clicked', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} />);

    await user.click(screen.getByTestId('design-actions-trigger'));
    await user.click(screen.getByTestId('action-copy'));

    expect(defaultProps.onCopy).toHaveBeenCalledWith(mockDesign);
  });

  it('calls onMove when move is clicked', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} />);

    await user.click(screen.getByTestId('design-actions-trigger'));
    await user.click(screen.getByTestId('action-move'));

    expect(defaultProps.onMove).toHaveBeenCalledWith(mockDesign);
  });

  it('calls onDelete when delete is clicked', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} />);

    await user.click(screen.getByTestId('design-actions-trigger'));
    await user.click(screen.getByTestId('action-delete'));

    expect(defaultProps.onDelete).toHaveBeenCalledWith(mockDesign);
  });

  it('calls onVersions when versions is clicked', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} />);

    await user.click(screen.getByTestId('design-actions-trigger'));
    await user.click(screen.getByTestId('action-versions'));

    expect(defaultProps.onVersions).toHaveBeenCalledWith(mockDesign);
  });

  it('hides move option when only one project exists', async () => {
    const user = userEvent.setup();
    render(
      <DesignActionsMenu {...defaultProps} projects={[mockProjects[0]]} />
    );

    await user.click(screen.getByTestId('design-actions-trigger'));

    expect(screen.queryByTestId('action-move')).not.toBeInTheDocument();
  });

  it('hides versions option when showVersions is false', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} showVersions={false} />);

    await user.click(screen.getByTestId('design-actions-trigger'));

    expect(screen.queryByTestId('action-versions')).not.toBeInTheDocument();
  });

  it('closes menu when backdrop is clicked', async () => {
    const user = userEvent.setup();
    render(<DesignActionsMenu {...defaultProps} />);

    await user.click(screen.getByTestId('design-actions-trigger'));
    expect(screen.getByTestId('design-actions-menu')).toBeInTheDocument();

    await user.click(screen.getByTestId('menu-backdrop'));
    expect(screen.queryByTestId('design-actions-menu')).not.toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<DesignActionsMenu {...defaultProps} disabled />);

    expect(screen.getByTestId('design-actions-trigger')).toBeDisabled();
  });
});

describe('RenameModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    design: mockDesign,
    onConfirm: vi.fn().mockResolvedValue(undefined),
  };

  it('renders when open', () => {
    render(<RenameModal {...defaultProps} />);

    expect(screen.getByText('Rename design')).toBeInTheDocument();
  });

  it('pre-fills with design name', () => {
    render(<RenameModal {...defaultProps} />);

    expect(screen.getByTestId('rename-input')).toHaveValue('Test Design');
  });

  it('calls onConfirm with new name on submit', async () => {
    const user = userEvent.setup();
    render(<RenameModal {...defaultProps} />);

    const input = screen.getByTestId('rename-input');
    await user.clear(input);
    await user.type(input, 'New Name');
    await user.click(screen.getByText('Rename'));

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('New Name');
  });

  it('disables submit button when name is empty', async () => {
    const user = userEvent.setup();
    render(<RenameModal {...defaultProps} />);

    const input = screen.getByTestId('rename-input');
    await user.clear(input);

    // Rename button should be disabled when name is empty
    const renameButton = screen.getByRole('button', { name: 'Rename' });
    expect(renameButton).toBeDisabled();
  });

  it('shows error for name exceeding max length', async () => {
    const user = userEvent.setup();
    render(<RenameModal {...defaultProps} />);

    const input = screen.getByTestId('rename-input');
    await user.clear(input);
    await user.type(input, 'a'.repeat(256));
    await user.click(screen.getByText('Rename'));

    expect(
      screen.getByText('Name must be 255 characters or less')
    ).toBeInTheDocument();
  });

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<RenameModal {...defaultProps} />);

    await user.click(screen.getByText('Cancel'));

    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('disables inputs when loading', () => {
    render(<RenameModal {...defaultProps} isLoading />);

    expect(screen.getByTestId('rename-input')).toBeDisabled();
    expect(screen.getByText('Renaming...')).toBeInTheDocument();
  });
});
