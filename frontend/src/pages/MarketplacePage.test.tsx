/**
 * Tests for the MarketplacePage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { MarketplacePage } from './MarketplacePage';
import * as api from '@/lib/marketplace';

// Mock the ThemeContext
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
    isLoading: false,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the WebSocketContext
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    isConnected: false,
    connectionState: 'disconnected',
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    sendMessage: vi.fn(),
  }),
}));

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'user-1', email: 'test@example.com', name: 'Test User' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock the marketplace API
vi.mock('@/lib/marketplace', () => ({
  browseDesigns: vi.fn(),
  getFeaturedDesigns: vi.fn(),
  getCategories: vi.fn(),
}));

// Mock the SaveButton to avoid additional API calls
vi.mock('@/components/marketplace/SaveButton', () => ({
  SaveButton: () => <button>Save</button>,
}));

const mockDesigns = [
  {
    id: 'design-1',
    name: 'Arduino Case',
    description: 'A simple case for Arduino',
    thumbnail_url: null,
    category: 'arduino',
    tags: ['arduino', 'case'],
    save_count: 100,
    remix_count: 25,
    is_starter: false,
    created_at: '2025-01-01T00:00:00Z',
    published_at: '2025-01-01T00:00:00Z',
    author_id: 'user-2',
    author_name: 'John Doe',
  },
  {
    id: 'design-2',
    name: 'Raspberry Pi Enclosure',
    description: 'Case for Raspberry Pi 5',
    thumbnail_url: null,
    category: 'raspberry-pi',
    tags: ['raspberry-pi', 'pi5'],
    save_count: 50,
    remix_count: 10,
    is_starter: true,
    created_at: '2025-01-02T00:00:00Z',
    published_at: '2025-01-02T00:00:00Z',
    author_id: 'user-3',
    author_name: 'Jane Smith',
  },
];

const mockCategories = [
  { name: 'Arduino', slug: 'arduino', design_count: 10 },
  { name: 'Raspberry Pi', slug: 'raspberry-pi', design_count: 15 },
];

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
);

describe('MarketplacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.browseDesigns as any).mockResolvedValue({
      items: mockDesigns,
      total: 2,
      page: 1,
      page_size: 20,
      total_pages: 1,
      has_next: false,
      has_prev: false,
    });
    (api.getFeaturedDesigns as any).mockResolvedValue([mockDesigns[1]]);
    (api.getCategories as any).mockResolvedValue(mockCategories);
  });

  it('renders the marketplace header', async () => {
    render(<MarketplacePage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Marketplace')).toBeInTheDocument();
    });
  });

  it('displays designs after loading', async () => {
    render(<MarketplacePage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Arduino Case')).toBeInTheDocument();
      // Raspberry Pi Enclosure may appear multiple times (featured + regular)
      expect(screen.getAllByText('Raspberry Pi Enclosure').length).toBeGreaterThanOrEqual(1);
    });
  });

  it('displays the correct design count', async () => {
    render(<MarketplacePage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('2 designs found')).toBeInTheDocument();
    });
  });

  it('displays categories in sidebar', async () => {
    render(<MarketplacePage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Arduino')).toBeInTheDocument();
      expect(screen.getByText('Raspberry Pi')).toBeInTheDocument();
    });
  });

  it('displays featured designs section', async () => {
    render(<MarketplacePage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Featured Designs')).toBeInTheDocument();
    });
  });

  it('shows starter badge for starter designs', async () => {
    render(<MarketplacePage />, { wrapper });

    await waitFor(() => {
      const starterBadges = screen.getAllByText('Starter');
      expect(starterBadges.length).toBeGreaterThan(0);
    });
  });

  it('calls browseDesigns with correct filters', async () => {
    render(<MarketplacePage />, { wrapper });

    await waitFor(() => {
      expect(api.browseDesigns).toHaveBeenCalledWith(
        expect.objectContaining({
          sort: 'popular',
          page: 1,
          page_size: 20,
        }),
        'test-token'
      );
    });
  });
});
