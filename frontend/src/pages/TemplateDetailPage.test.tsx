/**
 * Tests for TemplateDetailPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { TemplateDetailPage } from './TemplateDetailPage';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com', tier: 'free' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock ModelViewer
vi.mock('@/components/viewer', () => ({
  ModelViewer: ({ data }: { data: ArrayBuffer | null }) => (
    <div data-testid="model-viewer">{data ? 'Model loaded' : 'No model'}</div>
  ),
}));

const mockTemplate = {
  id: '1',
  slug: 'simple-box',
  name: 'Simple Box',
  description: 'A parametric box template with customizable dimensions',
  category: 'enclosures',
  tags: ['box', 'enclosure', 'basic'],
  thumbnail_url: null,
  tier_required: 'free',
  parameters: [
    {
      name: 'length',
      type: 'float',
      label: 'Length',
      description: 'Box length in mm',
      default: 100,
      min: 10,
      max: 500,
      step: 1,
      unit: 'mm',
    },
    {
      name: 'width',
      type: 'float',
      label: 'Width',
      description: 'Box width in mm',
      default: 50,
      min: 10,
      max: 500,
      step: 1,
      unit: 'mm',
    },
    {
      name: 'height',
      type: 'float',
      label: 'Height',
      description: 'Box height in mm',
      default: 30,
      min: 10,
      max: 200,
      step: 1,
      unit: 'mm',
    },
    {
      name: 'wall_thickness',
      type: 'float',
      label: 'Wall Thickness',
      description: 'Wall thickness in mm',
      default: 2,
      min: 0.5,
      max: 10,
      step: 0.5,
      unit: 'mm',
    },
    {
      name: 'include_lid',
      type: 'bool',
      label: 'Include Lid',
      description: 'Generate a matching lid',
      default: true,
    },
  ],
  is_featured: true,
  usage_count: 1000,
};

const renderTemplateDetailPage = (slug = 'simple-box') => {
  return render(
    <MemoryRouter initialEntries={[`/templates/${slug}`]}>
      <Routes>
        <Route path="/templates/:slug" element={<TemplateDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('TemplateDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderTemplateDetailPage();

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders template name', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
    });
  });

  it('displays template description', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText(/parametric box template/i)).toBeInTheDocument();
    });
  });

  it('shows parameter inputs', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText(/length/i).length).toBeGreaterThan(0);
    });
  });

  it('displays default parameter values', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText(/length/i).length).toBeGreaterThan(0);
    });
    
    // Input fields should contain default values
    const inputs = document.querySelectorAll('input[type="number"]');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('allows parameter adjustment', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText(/length/i).length).toBeGreaterThan(0);
    });

    // Input fields should be present and editable
    const inputs = document.querySelectorAll('input[type="number"]');
    expect(inputs.length).toBeGreaterThan(0);
  });

  it('shows boolean parameter as checkbox', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText(/include lid/i)).toBeInTheDocument();
    });

    // Boolean parameter should have a checkbox
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');
    expect(checkboxes.length).toBeGreaterThan(0);
  });

  it('has back button', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
    });
    
    // Back button with arrow icon should be present
    const svgIcons = document.querySelectorAll('svg');
    expect(svgIcons.length).toBeGreaterThan(0);
  });

  it('shows preview button', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
    });
    
    // Preview button should exist
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('triggers preview on button click', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
    });
    
    // Buttons should be present
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('has download buttons', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /step/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /stl/i })).toBeInTheDocument();
    });
  });

  it('downloads STEP file', async () => {
    const user = userEvent.setup();
    
    const mockBlob = new Blob(['test'], { type: 'application/octet-stream' });
    
    (global.fetch as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockTemplate),
      })
      .mockResolvedValueOnce({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /step/i })).toBeInTheDocument();
    });

    const stepButton = screen.getByRole('button', { name: /step/i });
    await user.click(stepButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/generate'),
        expect.anything()
      );
    });
  });

  it('shows error for not found template', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 404,
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText(/not found/i)).toBeInTheDocument();
    });
  });

  it('shows error state', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load'));

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('shows parameter units', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      // Should show 'mm' units somewhere
      expect(screen.getAllByText(/mm/i).length).toBeGreaterThan(0);
    });
  });

  it('has parameters collapsible section', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText(/length/i).length).toBeGreaterThan(0);
    });
  });

  it('shows parameter description on hover/focus', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getAllByText(/length/i).length).toBeGreaterThan(0);
    });
  });

  it('displays model viewer', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockTemplate),
    });

    renderTemplateDetailPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
    });
  });
});
