/**
 * Tests for DesignDetailPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DesignDetailPage } from './DesignDetailPage';
import * as designs from '@/lib/designs';
import * as generate from '@/lib/generate';

// Mock the auth context
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
    user: { id: 'user-1', email: 'test@test.com' },
  }),
}));

// Mock the ModelViewer component
vi.mock('@/components/viewer/ModelViewer', () => ({
  ModelViewer: ({ stlData }: { stlData?: ArrayBuffer }) => (
    <div data-testid="model-viewer" data-has-data={!!stlData}>
      Model Viewer
    </div>
  ),
}));

// Mock design API
vi.mock('@/lib/designs', () => ({
  getDesign: vi.fn(),
}));

// Mock generate API
vi.mock('@/lib/generate', () => ({
  getPreviewData: vi.fn(),
  downloadGeneratedFile: vi.fn(),
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

const mockDesign: designs.Design = {
  id: 'design-123',
  name: 'Test Design',
  description: 'A test design description',
  project_id: 'project-123',
  project_name: 'My Project',
  source_type: 'ai_generated',
  status: 'ready',
  thumbnail_url: null,
  extra_data: {
    job_id: 'job-123',
    downloads: {
      step: '/download/step',
      stl: '/download/stl',
    },
    shape: 'box',
  },
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const renderPage = (designId: string = 'design-123') => {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/designs/${designId}`]}>
        <Routes>
          <Route path="/designs/:designId" element={<DesignDetailPage />} />
          <Route path="/projects" element={<div>Projects Page</div>} />
          <Route path="/create" element={<div>Create Page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe('DesignDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
  });

  describe('loading state', () => {
    it('shows loading indicator while fetching design', () => {
      vi.mocked(designs.getDesign).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      renderPage();

      expect(screen.getByText('Loading design...')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message when design fails to load', async () => {
      vi.mocked(designs.getDesign).mockRejectedValue(new Error('Not found'));

      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Design Not Found')).toBeInTheDocument();
      });
    });

    it('shows back link to projects on error', async () => {
      vi.mocked(designs.getDesign).mockRejectedValue(new Error('Not found'));

      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Back to Projects')).toBeInTheDocument();
      });
    });
  });

  describe('success state', () => {
    beforeEach(() => {
      vi.mocked(designs.getDesign).mockResolvedValue(mockDesign);
      vi.mocked(generate.getPreviewData).mockResolvedValue(new ArrayBuffer(100));
    });

    it('displays design name', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Test Design')).toBeInTheDocument();
      });
    });

    it('displays design description', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('A test design description')).toBeInTheDocument();
      });
    });

    it('displays project name', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('My Project')).toBeInTheDocument();
      });
    });

    it('displays source type', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('ai generated')).toBeInTheDocument();
      });
    });

    it('renders ModelViewer with STL data', async () => {
      renderPage();

      await waitFor(() => {
        const viewer = screen.getByTestId('model-viewer');
        expect(viewer).toBeInTheDocument();
        expect(viewer).toHaveAttribute('data-has-data', 'true');
      });
    });

    it('shows download buttons when downloads available', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('STEP File')).toBeInTheDocument();
        expect(screen.getByText('STL File')).toBeInTheDocument();
      });
    });

    it('shows remix button', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remix/i })).toBeInTheDocument();
      });
    });
  });

  describe('download functionality', () => {
    beforeEach(() => {
      vi.mocked(designs.getDesign).mockResolvedValue(mockDesign);
      vi.mocked(generate.getPreviewData).mockResolvedValue(new ArrayBuffer(100));
    });

    it('calls downloadGeneratedFile when STEP download clicked', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/octet-stream' });
      vi.mocked(generate.downloadGeneratedFile).mockResolvedValue(mockBlob);

      const user = userEvent.setup();
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('STEP File')).toBeInTheDocument();
      });

      await user.click(screen.getByText('STEP File'));

      await waitFor(() => {
        expect(generate.downloadGeneratedFile).toHaveBeenCalledWith(
          'job-123',
          'step',
          'test-token'
        );
      });
    });

    it('calls downloadGeneratedFile when STL download clicked', async () => {
      const mockBlob = new Blob(['test'], { type: 'application/octet-stream' });
      vi.mocked(generate.downloadGeneratedFile).mockResolvedValue(mockBlob);

      const user = userEvent.setup();
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('STL File')).toBeInTheDocument();
      });

      await user.click(screen.getByText('STL File'));

      await waitFor(() => {
        expect(generate.downloadGeneratedFile).toHaveBeenCalledWith(
          'job-123',
          'stl',
          'test-token'
        );
      });
    });
  });

  describe('remix functionality', () => {
    beforeEach(() => {
      vi.mocked(designs.getDesign).mockResolvedValue(mockDesign);
      vi.mocked(generate.getPreviewData).mockResolvedValue(new ArrayBuffer(100));
    });

    it('navigates to create page when remix clicked', async () => {
      const user = userEvent.setup();
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /remix/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /remix/i }));

      await waitFor(() => {
        expect(screen.getByText('Create Page')).toBeInTheDocument();
      });
    });
  });

  describe('no preview state', () => {
    it('shows no preview message when STL fails to load', async () => {
      vi.mocked(designs.getDesign).mockResolvedValue({
        ...mockDesign,
        extra_data: { ...mockDesign.extra_data, job_id: undefined },
      });

      renderPage();

      await waitFor(() => {
        expect(screen.getByText('No preview available')).toBeInTheDocument();
      });
    });
  });
});
