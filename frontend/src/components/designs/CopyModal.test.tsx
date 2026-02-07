/**
 * Tests for CopyModal Component
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { CopyModal } from './CopyModal';

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

describe('CopyModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    design: mockDesign,
    projects: mockProjects,
    onConfirm: vi.fn().mockResolvedValue(undefined),
  };

  it('renders when open', () => {
    render(<CopyModal {...defaultProps} />);

    expect(screen.getByText('Copy design')).toBeInTheDocument();
  });

  it('pre-fills name with "Copy" suffix', () => {
    render(<CopyModal {...defaultProps} />);

    expect(screen.getByTestId('copy-name-input')).toHaveValue(
      'Test Design (Copy)'
    );
  });

  it('pre-selects current project', () => {
    render(<CopyModal {...defaultProps} />);

    const select = screen.getByTestId('copy-project-select');
    expect(select).toHaveValue('project-1');
  });

  it('shows all projects in dropdown', () => {
    render(<CopyModal {...defaultProps} />);

    expect(screen.getByText('Test Project (current)')).toBeInTheDocument();
    expect(screen.getByText('Other Project')).toBeInTheDocument();
  });

  it('calls onConfirm with options on submit', async () => {
    const user = userEvent.setup();
    render(<CopyModal {...defaultProps} />);

    await user.click(screen.getByText('Copy'));

    expect(defaultProps.onConfirm).toHaveBeenCalledWith({
      name: 'Test Design (Copy)',
      targetProjectId: 'project-1',
      includeVersions: false,
    });
  });

  it('calls onConfirm with different project when selected', async () => {
    const user = userEvent.setup();
    render(<CopyModal {...defaultProps} />);

    await user.selectOptions(
      screen.getByTestId('copy-project-select'),
      'project-2'
    );
    await user.click(screen.getByText('Copy'));

    expect(defaultProps.onConfirm).toHaveBeenCalledWith({
      name: 'Test Design (Copy)',
      targetProjectId: 'project-2',
      includeVersions: false,
    });
  });

  it('includes versions when checkbox is checked', async () => {
    const user = userEvent.setup();
    render(<CopyModal {...defaultProps} />);

    await user.click(screen.getByTestId('copy-include-versions'));
    await user.click(screen.getByText('Copy'));

    expect(defaultProps.onConfirm).toHaveBeenCalledWith({
      name: 'Test Design (Copy)',
      targetProjectId: 'project-1',
      includeVersions: true,
    });
  });

  it('disables submit button when name is empty', async () => {
    const user = userEvent.setup();
    render(<CopyModal {...defaultProps} />);

    const input = screen.getByTestId('copy-name-input');
    await user.clear(input);

    // Copy button should be disabled when name is empty
    const copyButton = screen.getByRole('button', { name: 'Copy' });
    expect(copyButton).toBeDisabled();
  });

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup();
    render(<CopyModal {...defaultProps} />);

    await user.click(screen.getByText('Cancel'));

    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('disables inputs when loading', () => {
    render(<CopyModal {...defaultProps} isLoading />);

    expect(screen.getByTestId('copy-name-input')).toBeDisabled();
    expect(screen.getByTestId('copy-project-select')).toBeDisabled();
    expect(screen.getByTestId('copy-include-versions')).toBeDisabled();
    expect(screen.getByText('Copying...')).toBeInTheDocument();
  });

  it('shows info text when changing projects', async () => {
    const user = userEvent.setup();
    render(<CopyModal {...defaultProps} />);

    await user.selectOptions(
      screen.getByTestId('copy-project-select'),
      'project-2'
    );

    expect(
      screen.getByText(/Moving from "Test Project" to "Other Project"/)
    ).toBeInTheDocument();
  });
});
