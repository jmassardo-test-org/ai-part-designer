/**
 * Tests for MoveModal Component
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { MoveModal } from './MoveModal';

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
  {
    id: 'project-3',
    name: 'Third Project',
    description: null,
    design_count: 0,
    thumbnail_url: null,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
];

describe('MoveModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    design: mockDesign,
    projects: mockProjects,
    onConfirm: vi.fn().mockResolvedValue(undefined),
  };

  it('renders when open', () => {
    render(<MoveModal {...defaultProps} />);

    expect(screen.getByText('Move design')).toBeInTheDocument();
  });

  it('displays current project', () => {
    render(<MoveModal {...defaultProps} />);

    expect(screen.getByText('Test Project')).toBeInTheDocument();
  });

  it('excludes current project from target options', () => {
    render(<MoveModal {...defaultProps} />);

    const select = screen.getByTestId('move-project-select');
    const options = select.querySelectorAll('option');

    expect(options).toHaveLength(2);
    expect(
      Array.from(options).map((o) => o.textContent)
    ).not.toContain('Test Project');
  });

  it('shows available projects with design counts', () => {
    render(<MoveModal {...defaultProps} />);

    expect(screen.getByText('Other Project (3 designs)')).toBeInTheDocument();
    expect(screen.getByText('Third Project (0 designs)')).toBeInTheDocument();
  });

  it('calls onConfirm with target project on submit', async () => {
    const user = userEvent.setup();
    render(<MoveModal {...defaultProps} />);

    await user.selectOptions(
      screen.getByTestId('move-project-select'),
      'project-2'
    );
    await user.click(screen.getByText('Move'));

    expect(defaultProps.onConfirm).toHaveBeenCalledWith('project-2');
  });

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<MoveModal {...defaultProps} />);

    await user.click(screen.getByText('Cancel'));

    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('disables select when loading', () => {
    render(<MoveModal {...defaultProps} isLoading />);

    expect(screen.getByTestId('move-project-select')).toBeDisabled();
    expect(screen.getByText('Moving...')).toBeInTheDocument();
  });

  it('shows preview of move operation', async () => {
    const user = userEvent.setup();
    render(<MoveModal {...defaultProps} />);

    await user.selectOptions(
      screen.getByTestId('move-project-select'),
      'project-2'
    );

    expect(
      screen.getByText(/will be moved from .* to/)
    ).toBeInTheDocument();
  });

  it('shows message when only one project exists', () => {
    render(
      <MoveModal {...defaultProps} projects={[mockProjects[0]]} />
    );

    expect(
      screen.getByText(/need at least two projects/)
    ).toBeInTheDocument();
    expect(screen.getByText('Close')).toBeInTheDocument();
  });
});
