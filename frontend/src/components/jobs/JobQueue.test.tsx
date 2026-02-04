/**
 * JobQueue Component Tests
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { JobQueue } from './JobQueue';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
  }),
}));

// Mock WebSocket context
const mockSubscribe = vi.fn(() => vi.fn());
const mockSubscribeToRoom = vi.fn();
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    connected: true,
    connecting: false,
    subscribe: mockSubscribe,
    subscribeToRoom: mockSubscribeToRoom,
    send: vi.fn(),
    reconnect: vi.fn(),
    unsubscribeFromRoom: vi.fn(),
    subscribeToJob: vi.fn(),
  }),
}));

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('JobQueue', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  const renderWithMockFetch = (mockResponse: any = { items: [] }) => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });
    global.fetch = mockFetch;
    
    const result = render(
      <BrowserRouter>
        <JobQueue />
      </BrowserRouter>
    );
    
    return { ...result, mockFetch };
  };

  it('renders job queue button', async () => {
    renderWithMockFetch();
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /view active jobs/i })).toBeInTheDocument();
    });
  });

  it('fetches jobs on mount', async () => {
    const { mockFetch } = renderWithMockFetch();
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    // Verify fetch was called with correct URL and headers
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/jobs'),
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer test-token',
        },
      })
    );
  });

  it('shows active job count badge', async () => {
    renderWithMockFetch({
      items: [
        { id: '1', job_type: 'generate', status: 'processing', progress: 50, created_at: new Date().toISOString() },
        { id: '2', job_type: 'export', status: 'pending', progress: 0, created_at: new Date().toISOString() },
      ],
    });
    
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    });
  });

  it('opens dropdown when clicked', async () => {
    const { mockFetch } = renderWithMockFetch();
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    expect(screen.getByText('Active Jobs')).toBeInTheDocument();
  });

  it('shows empty state when no jobs', async () => {
    const { mockFetch } = renderWithMockFetch();
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    expect(screen.getByText('No active jobs')).toBeInTheDocument();
  });

  it('displays job list with correct info', async () => {
    const jobDate = new Date();
    jobDate.setMinutes(jobDate.getMinutes() - 5);
    
    const { mockFetch } = renderWithMockFetch({
      items: [
        { 
          id: '1', 
          job_type: 'generate', 
          status: 'processing', 
          progress: 50, 
          created_at: jobDate.toISOString(),
          metadata: {},
        },
      ],
    });
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    expect(screen.getByText('Generate')).toBeInTheDocument();
    expect(screen.getByText('50% complete')).toBeInTheDocument();
  });

  it('navigates to job details on click', async () => {
    const { mockFetch } = renderWithMockFetch({
      items: [
        { 
          id: 'job-123', 
          job_type: 'generate', 
          status: 'processing', 
          progress: 50, 
          created_at: new Date().toISOString(),
          metadata: {},
        },
      ],
    });
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    const jobItem = screen.getByText('Generate').closest('div[class*="hover:bg-gray-50"]');
    if (jobItem) {
      fireEvent.click(jobItem);
      expect(mockNavigate).toHaveBeenCalledWith('/jobs/job-123');
    }
  });

  it('shows view all jobs link', async () => {
    const { mockFetch } = renderWithMockFetch();
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    expect(screen.getByText('View all jobs')).toBeInTheDocument();
  });

  it('navigates to jobs page when view all clicked', async () => {
    const { mockFetch } = renderWithMockFetch();
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    const viewAllButton = screen.getByText('View all jobs');
    fireEvent.click(viewAllButton);
    
    expect(mockNavigate).toHaveBeenCalledWith('/jobs');
  });

  it('closes dropdown when backdrop clicked', async () => {
    const { mockFetch } = renderWithMockFetch();
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    expect(screen.getByText('Active Jobs')).toBeInTheDocument();
    
    // Click backdrop
    const backdrop = document.querySelector('.fixed.inset-0');
    if (backdrop) {
      fireEvent.click(backdrop);
    }
  });

  it('shows failed job error message', async () => {
    const { mockFetch } = renderWithMockFetch({
      items: [
        { 
          id: '1', 
          job_type: 'generate', 
          status: 'failed', 
          progress: 0, 
          error_message: 'Generation failed',
          created_at: new Date().toISOString(),
          metadata: {},
        },
      ],
    });
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    
    const button = screen.getByRole('button', { name: /view active jobs/i });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText('Generation failed')).toBeInTheDocument();
    });
  });

  it('fetches jobs with auth header', async () => {
    const { mockFetch } = renderWithMockFetch();
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/jobs'),
        expect.objectContaining({
          headers: {
            Authorization: 'Bearer test-token',
          },
        })
      );
    });
  });
});
