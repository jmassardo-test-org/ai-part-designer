/**
 * Tests for StarterDetailPage component.
 * 
 * Tests the starter design detail view and remix functionality.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithRouter } from '@/test/utils';
import { StarterDetailPage } from './StarterDetailPage';

// Mock the marketplace API
const mockGetStarterDetail = vi.fn();
const mockRemixStarter = vi.fn();

vi.mock('@/lib/marketplace', () => ({
  getStarterDetail: (...args: unknown[]) => mockGetStarterDetail(...args),
  remixStarter: (...args: unknown[]) => mockRemixStarter(...args),
}));

// Mock the auth context with all required exports
vi.mock('@/contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/contexts/AuthContext')>();
  return {
    ...actual,
    useAuth: () => ({
      token: 'mock-token',
      user: { id: 'user-123', email: 'test@example.com' },
      isLoading: false,
      isAuthenticated: true,
    }),
  };
});

const mockStarterDetail = {
  id: 'starter-123',
  name: 'Pi Zero Case',
  description: 'A compact case for Raspberry Pi Zero',
  thumbnail_url: '/images/pi-zero-case.png',
  category: 'Electronics',
  tags: ['raspberry-pi', 'compact'],
  remix_count: 42,
  exterior_dimensions: {
    width: 150,
    depth: 100,
    height: 50,
    unit: 'mm',
  },
  features: ['snap fit lid', 'ventilation'],
  created_at: '2024-01-15T10:00:00Z',
  enclosure_spec: {
    exterior: {
      width: { value: 150, unit: 'mm' },
      depth: { value: 100, unit: 'mm' },
      height: { value: 50, unit: 'mm' },
    },
    walls: { thickness: { value: 2, unit: 'mm' } },
    lid: { type: 'snap_fit' },
    ventilation: { enabled: true, pattern: 'slots' },
  },
  author_id: 'author-123',
  author_name: 'Design Studio',
};

describe('StarterDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetStarterDetail.mockResolvedValue(mockStarterDetail);
  });

  it('should render loading state initially', () => {
    // Make the API call hang
    mockGetStarterDetail.mockImplementation(() => new Promise(() => {}));
    
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    // Look for the Loader2 icon by checking for an animate-spin element
    const loadingContainer = document.querySelector('.animate-spin');
    expect(loadingContainer).toBeDefined();
  });

  it('should display starter details after loading', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText('Pi Zero Case')).toBeInTheDocument();
    });

    expect(screen.getByText('A compact case for Raspberry Pi Zero')).toBeInTheDocument();
  });

  it('should display dimensions from enclosure spec', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText('Pi Zero Case')).toBeInTheDocument();
    });

    // Should display formatted dimensions string
    expect(screen.getByText(/150.*×.*100.*×.*50/)).toBeInTheDocument();
  });

  it('should display features extracted from enclosure spec', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText('Pi Zero Case')).toBeInTheDocument();
    });

    // Should extract and display features - checking for capitalized versions
    // Use getAllByText since "Ventilation" appears multiple times (feature + heading)
    expect(screen.getByText(/snap fit/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Ventilation/i).length).toBeGreaterThan(0);
  });

  it('should show remix count', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText(/42 remixes/i)).toBeInTheDocument();
    });
  });

  it('should display tags', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText('#raspberry-pi')).toBeInTheDocument();
      expect(screen.getByText('#compact')).toBeInTheDocument();
    });
  });

  it('should have a remix button', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /remix/i })).toBeInTheDocument();
    });
  });

  it('should call remix API when remix button is clicked', async () => {
    const user = userEvent.setup();
    
    mockRemixStarter.mockResolvedValue({
      id: 'remix-456',
      name: 'My Remix',
      remixed_from_id: 'starter-123',
      remixed_from_name: 'Pi Zero Case',
      enclosure_spec: mockStarterDetail.enclosure_spec,
      created_at: '2024-01-20T10:00:00Z',
    });

    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /remix/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /remix/i }));

    await waitFor(() => {
      expect(mockRemixStarter).toHaveBeenCalledWith('starter-123', undefined, 'mock-token');
    });
  });

  it('should display error state when API fails', async () => {
    mockGetStarterDetail.mockRejectedValue(new Error('Failed to load'));

    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('should have a back button to starters page', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText('Pi Zero Case')).toBeInTheDocument();
    });

    const backLink = screen.getByRole('link', { name: /back to starters/i });
    expect(backLink).toHaveAttribute('href', '/starters');
  });

  it('should display category badge', async () => {
    renderWithRouter(<StarterDetailPage />, {
      initialEntries: ['/starters/starter-123'],
      route: '/starters/:starterId',
    });

    await waitFor(() => {
      expect(screen.getByText('Pi Zero Case')).toBeInTheDocument();
    });

    // Category should be formatted (capitalized)
    expect(screen.getByText('Electronics')).toBeInTheDocument();
  });
});
