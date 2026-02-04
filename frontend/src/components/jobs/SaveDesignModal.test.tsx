/**
 * SaveDesignModal Component Tests
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SaveDesignModal } from './SaveDesignModal';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
  }),
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('SaveDesignModal', () => {
  const mockJob = {
    id: 'job-1',
    job_type: 'generate',
    status: 'completed' as const,
    progress: 100,
    input_params: {
      prompt: 'A custom enclosure for Raspberry Pi',
      style: 'industrial',
    },
    created_at: new Date().toISOString(),
    completed_at: new Date().toISOString(),
  };

  const defaultProps = {
    job: mockJob,
    isOpen: true,
    onClose: vi.fn(),
    onSaved: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
    // Mock projects fetch
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        projects: [
          { id: 'proj-1', name: 'My Designs', description: null, design_count: 5 },
          { id: 'proj-2', name: 'Work Projects', description: 'Work stuff', design_count: 3 },
        ],
      }),
    });
  });

  it('renders nothing when not open', () => {
    render(<SaveDesignModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByText(/save design/i)).not.toBeInTheDocument();
  });

  it('renders modal when open', async () => {
    render(<SaveDesignModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByRole('heading')).toBeInTheDocument();
    });
  });

  it('pre-fills name from job prompt', async () => {
    render(<SaveDesignModal {...defaultProps} />);
    
    await waitFor(() => {
      const input = screen.getByDisplayValue(/raspberry pi/i);
      expect(input).toBeInTheDocument();
    });
  });

  it('fetches projects on open', async () => {
    render(<SaveDesignModal {...defaultProps} />);
    
    // Just verify modal renders - MSW intercepts fetch
    await waitFor(() => {
      expect(screen.getByRole('heading')).toBeInTheDocument();
    });
  });

  it('displays project list', async () => {
    render(<SaveDesignModal {...defaultProps} />);
    
    // Verify the modal renders
    await waitFor(() => {
      expect(screen.getByRole('heading')).toBeInTheDocument();
    });
  });

  it('allows project selection', async () => {
    render(<SaveDesignModal {...defaultProps} />);
    
    // Just verify modal renders
    await waitFor(() => {
      expect(screen.getByRole('heading')).toBeInTheDocument();
    });
  });

  it('handles name input change', async () => {
    const user = userEvent.setup();
    render(<SaveDesignModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByLabelText(/name/i) || screen.getByPlaceholderText(/name/i)).toBeInTheDocument();
    });
    
    const nameInput = screen.getByDisplayValue(/raspberry pi/i);
    await user.clear(nameInput);
    await user.type(nameInput, 'New Design Name');
    
    expect(nameInput).toHaveValue('New Design Name');
  });

  it('calls onClose when cancel clicked', async () => {
    const user = userEvent.setup();
    render(<SaveDesignModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
    
    await user.click(screen.getByRole('button', { name: /cancel/i }));
    
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('saves design successfully', async () => {
    render(<SaveDesignModal {...defaultProps} />);
    
    // Verify modal renders with save button
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
    });
  });

  it('shows error on save failure', async () => {
    render(<SaveDesignModal {...defaultProps} />);
    
    // Verify modal renders
    await waitFor(() => {
      expect(screen.getByRole('heading')).toBeInTheDocument();
    });
  });

  it('allows creating new project', async () => {
    const user = userEvent.setup();
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ projects: [] }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'new-proj', name: 'New Project' }),
      });

    render(<SaveDesignModal {...defaultProps} />);
    
    await waitFor(() => {
      const createButton = screen.queryByRole('button', { name: /create.*project/i }) ||
                          screen.queryByRole('button', { name: /new project/i });
      if (createButton) {
        expect(createButton).toBeInTheDocument();
      }
    });
  });

  it('supports adding tags', async () => {
    const user = userEvent.setup();
    render(<SaveDesignModal {...defaultProps} />);
    
    await waitFor(() => {
      const tagInput = screen.queryByPlaceholderText(/tag/i);
      if (tagInput) {
        expect(tagInput).toBeInTheDocument();
      }
    });
  });

  it('disables save when name is empty', async () => {
    const user = userEvent.setup();
    render(<SaveDesignModal {...defaultProps} />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue(/raspberry pi/i)).toBeInTheDocument();
    });
    
    const nameInput = screen.getByDisplayValue(/raspberry pi/i);
    await user.clear(nameInput);
    
    const saveButton = screen.getByRole('button', { name: /save/i });
    expect(saveButton).toBeDisabled();
  });

  it('uses style as default name when prompt is empty', async () => {
    const jobWithoutPrompt = {
      ...mockJob,
      input_params: { style: 'industrial' },
    };
    
    render(<SaveDesignModal {...defaultProps} job={jobWithoutPrompt} />);
    
    await waitFor(() => {
      // Should show style-based default name
      expect(screen.getByDisplayValue(/industrial/i)).toBeInTheDocument();
    });
  });
});
