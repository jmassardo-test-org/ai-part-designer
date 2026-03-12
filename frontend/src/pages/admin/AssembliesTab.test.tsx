/**
 * AssembliesTab Tests.
 *
 * Unit tests for the AssembliesTab component.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from '@/lib/api/admin';
import type { AdminAssemblyListResponse, AssemblyStats } from '@/types/admin';

// Mock the admin API
vi.mock('@/lib/api/admin', () => ({
  adminApi: {
    assemblies: {
      list: vi.fn(),
      get: vi.fn(),
      getStats: vi.fn(),
      updateStatus: vi.fn(),
      delete: vi.fn(),
    },
    vendors: {
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      getAnalytics: vi.fn(),
      bulkUpdatePrices: vi.fn(),
    },
    bom: {
      getAuditQueue: vi.fn(),
      approveAudit: vi.fn(),
      rejectAudit: vi.fn(),
    },
  },
}));

const mockAdminApi = vi.mocked(adminApi, true);

// Import after mocks
import { AssembliesTab } from './AssembliesTab';

describe('AssembliesTab', () => {
  const mockAssembliesResponse: AdminAssemblyListResponse = {
    items: [
      {
        id: 'asm-1',
        name: 'Widget Assembly',
        description: null,
        status: 'active',
        user_id: 'user-1',
        user_email: 'user@example.com',
        project_id: 'proj-1',
        component_count: 5,
        version: 1,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-02-01T00:00:00Z',
      },
      {
        id: 'asm-2',
        name: 'Bracket Assembly',
        description: null,
        status: 'draft',
        user_id: 'user-2',
        user_email: 'user2@example.com',
        project_id: 'proj-2',
        component_count: 3,
        version: 1,
        created_at: '2024-02-01T00:00:00Z',
        updated_at: '2024-03-01T00:00:00Z',
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
  };

  const mockStatsResponse: AssemblyStats = {
    total_assemblies: 50,
    avg_components_per_assembly: 6.0,
    assemblies_by_status: { active: 35, draft: 10, archived: 5 },
    top_categories: [],
    assemblies_created_today: 2,
    assemblies_created_this_week: 10,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminApi.assemblies.list.mockResolvedValue(mockAssembliesResponse);
    mockAdminApi.assemblies.getStats.mockResolvedValue(mockStatsResponse);
  });

  it('renders the assemblies heading', async () => {
    render(<AssembliesTab />);

    expect(screen.getByText('Assemblies & BOM')).toBeInTheDocument();
  });

  it('fetches and displays assemblies on mount', async () => {
    render(<AssembliesTab />);

    await waitFor(() => {
      expect(mockAdminApi.assemblies.list).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Widget Assembly')).toBeInTheDocument();
      expect(screen.getByText('Bracket Assembly')).toBeInTheDocument();
    });
  });

  it('displays assembly stats', async () => {
    render(<AssembliesTab />);

    await waitFor(() => {
      expect(screen.getByText('Widget Assembly')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Stats'));

    await waitFor(() => {
      expect(mockAdminApi.assemblies.getStats).toHaveBeenCalled();
    });
  });

  it('shows empty state when no assemblies exist', async () => {
    mockAdminApi.assemblies.list.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    render(<AssembliesTab />);

    await waitFor(() => {
      expect(screen.getByText('No assemblies found.')).toBeInTheDocument();
    });
  });

  it('handles API error gracefully', async () => {
    mockAdminApi.assemblies.list.mockRejectedValue(new Error('Network error'));

    render(<AssembliesTab />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load assemblies')).toBeInTheDocument();
    });
  });

  it('switches to vendors view', async () => {
    mockAdminApi.vendors.list.mockResolvedValue({
      items: [
        { id: 'v-1', name: 'Acme Corp', display_name: 'Acme', website: null, logo_url: null, api_type: null, categories: [], is_active: true, created_at: '2024-01-01T00:00:00Z', updated_at: null },
      ],
      total: 1,
    });

    render(<AssembliesTab />);

    await waitFor(() => {
      expect(screen.getByText('Widget Assembly')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Vendors'));

    await waitFor(() => {
      expect(mockAdminApi.vendors.list).toHaveBeenCalled();
    });
  });

  it('switches to BOM audit view', async () => {
    mockAdminApi.bom.getAuditQueue.mockResolvedValue({
      items: [],
      total: 0,
    });

    render(<AssembliesTab />);

    await waitFor(() => {
      expect(screen.getByText('Widget Assembly')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('BOM Audit'));

    await waitFor(() => {
      expect(mockAdminApi.bom.getAuditQueue).toHaveBeenCalled();
    });
  });

  it('opens stats dashboard view', async () => {
    render(<AssembliesTab />);

    await waitFor(() => {
      expect(screen.getByText('Widget Assembly')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Stats'));

    await waitFor(() => {
      expect(screen.getByText('Assembly Statistics')).toBeInTheDocument();
    });
  });

  it('filters assemblies by search term', async () => {
    render(<AssembliesTab />);

    await waitFor(() => {
      expect(mockAdminApi.assemblies.list).toHaveBeenCalledTimes(1);
    });

    const searchInput = screen.getByPlaceholderText('Search assemblies…');
    fireEvent.change(searchInput, { target: { value: 'Widget' } });
    fireEvent.keyDown(searchInput, { key: 'Enter' });

    await waitFor(() => {
      expect(mockAdminApi.assemblies.list).toHaveBeenCalledTimes(2);
    });
  });
});
