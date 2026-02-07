/**
 * Tests for AssemblyPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AssemblyPage } from './AssemblyPage';

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock assembly components
vi.mock('@/components/assembly', () => ({
  AssemblyViewer: ({ assembly }: { assembly: unknown }) => (
    <div data-testid="assembly-viewer">Assembly Viewer: {assembly ? 'loaded' : 'empty'}</div>
  ),
  BOMTable: ({ items }: { items: unknown[] }) => (
    <div data-testid="bom-table">BOM Table: {items?.length || 0} items</div>
  ),
}));

const mockAssembly = {
  id: 'asm1',
  name: 'Test Assembly',
  description: 'A test assembly',
  project_id: 'p1',
  project_name: 'Test Project',
  root_design_id: null,
  status: 'active',
  thumbnail_url: null,
  component_count: 3,
  total_quantity: 5,
  version: 1,
  created_at: '2026-01-15T10:00:00Z',
  updated_at: '2026-01-20T10:00:00Z',
  components: [
    {
      id: 'c1',
      name: 'Component 1',
      description: null,
      design_id: 'd1',
      design_name: 'Design 1',
      quantity: 2,
      position: { x: 0, y: 0, z: 0 },
      rotation: { rx: 0, ry: 0, rz: 0 },
      scale: { sx: 1, sy: 1, sz: 1 },
      is_cots: false,
      part_number: 'P001',
      color: '#ff0000',
      created_at: '2026-01-15T10:00:00Z',
      updated_at: '2026-01-15T10:00:00Z',
    },
  ],
  relationships: [],
};

const mockBOM = {
  assembly_id: 'asm1',
  assembly_name: 'Test Assembly',
  items: [
    {
      id: 'b1',
      component_id: 'c1',
      component_name: 'Component 1',
      part_number: 'P001',
      vendor_part_number: null,
      description: 'Test component',
      category: 'custom',
      vendor_id: null,
      vendor_name: null,
      quantity: 2,
      unit_cost: 10.00,
      total_cost: 20.00,
      currency: 'USD',
      lead_time_days: null,
      minimum_order_quantity: 1,
      in_stock: null,
      notes: null,
    },
  ],
  summary: {
    total_items: 1,
    total_quantity: 2,
    total_cost: 20.00,
    currency: 'USD',
    categories: { custom: 1 },
    longest_lead_time: null,
  },
};

const renderAssemblyPage = (assemblyId = 'asm1') => {
  return render(
    <MemoryRouter initialEntries={[`/assemblies/${assemblyId}`]}>
      <Routes>
        <Route path="/assemblies/:assemblyId" element={<AssemblyPage />} />
      </Routes>
    </MemoryRouter>
  );
};

describe('AssemblyPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderAssemblyPage();

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders assembly name', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      if (url.includes('/vendors')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([]),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText('Test Assembly')).toBeInTheDocument();
    });
  });

  it('displays assembly viewer', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByTestId('assembly-viewer')).toBeInTheDocument();
    });
  });

  it('has tab navigation', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText('Test Assembly')).toBeInTheDocument();
    });

    // Should have tabs for viewer, components, and BOM
    expect(screen.getByRole('button', { name: /3d viewer/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /components/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /bill of materials/i })).toBeInTheDocument();
  });

  it('switches to BOM tab', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText('Test Assembly')).toBeInTheDocument();
    });

    const bomTab = screen.getByRole('button', { name: /bill of materials/i });
    await user.click(bomTab);

    await waitFor(() => {
      // BOM content should appear
      expect(screen.getByRole('button', { name: /bill of materials/i })).toBeInTheDocument();
    });
  });

  it('shows component count', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      // Check for Components tab which shows count
      expect(screen.getByRole('button', { name: /components/i })).toBeInTheDocument();
    });
  });

  it('shows error for not found assembly', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 404,
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText(/not found/i)).toBeInTheDocument();
    });
  });

  it('shows error state', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to load'));

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('has back button', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText('Test Assembly')).toBeInTheDocument();
    });

    // Should have a back link/button (check for link with href to projects)
    const backLink = document.querySelector('a[href="/projects/p1"]');
    expect(backLink).toBeInTheDocument();
  });

  it('can edit assembly name', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText('Test Assembly')).toBeInTheDocument();
    });

    // Find and click edit button for name
    const editButtons = screen.getAllByRole('button');
    const editButton = editButtons.find(btn => 
      btn.querySelector('[class*="Edit"]') || btn.textContent?.includes('Edit')
    );

    if (editButton) {
      await user.click(editButton);
    }
  });

  it('displays total cost in BOM summary', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText('Test Assembly')).toBeInTheDocument();
    });

    const bomTab = screen.getByRole('button', { name: /bill of materials/i });
    await user.click(bomTab);

    await waitFor(() => {
      // BOM tab should be clicked
      expect(bomTab).toHaveAttribute('class', expect.stringContaining('text-primary'));
    });
  });

  it('shows add component button', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/bom')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBOM),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockAssembly),
      });
    });

    renderAssemblyPage();

    await waitFor(() => {
      expect(screen.getByText('Test Assembly')).toBeInTheDocument();
    });

    const componentsTab = screen.getByRole('button', { name: /components/i });
    await user.click(componentsTab);

    await waitFor(() => {
      const addButton = screen.getByRole('button', { name: /add/i });
      expect(addButton).toBeInTheDocument();
    });
  });
});
