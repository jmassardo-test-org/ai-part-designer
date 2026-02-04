/**
 * Tests for the StartersPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { StartersPage } from './StartersPage';
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
  getStarters: vi.fn(),
  getStarterCategories: vi.fn(),
  remixStarter: vi.fn(),
}));

const mockStarters = [
  {
    id: 'starter-1',
    name: 'Raspberry Pi 5 Basic Case',
    description: 'A simple case for Raspberry Pi 5',
    thumbnail_url: null,
    category: 'raspberry-pi',
    tags: ['raspberry-pi', 'pi5', 'basic'],
    remix_count: 50,
    exterior_dimensions: {
      width: 100,
      depth: 70,
      height: 30,
      unit: 'mm',
    },
    features: ['ventilation', 'lid-snap_fit'],
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'starter-2',
    name: 'Arduino Uno Shield Case',
    description: 'Enclosure for Arduino Uno with room for shields',
    thumbnail_url: null,
    category: 'arduino',
    tags: ['arduino', 'uno', 'shields'],
    remix_count: 30,
    exterior_dimensions: {
      width: 80,
      depth: 60,
      height: 40,
      unit: 'mm',
    },
    features: ['lid-screw_on'],
    created_at: '2025-01-02T00:00:00Z',
  },
];

const mockCategories = [
  { name: 'Raspberry Pi', slug: 'raspberry-pi', count: 5 },
  { name: 'Arduino', slug: 'arduino', count: 3 },
];

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
);

describe('StartersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getStarters as any).mockResolvedValue({
      items: mockStarters,
      total: 2,
      page: 1,
      page_size: 12,
    });
    (api.getStarterCategories as any).mockResolvedValue(mockCategories);
    (api.remixStarter as any).mockResolvedValue({
      id: 'remix-1',
      name: 'Raspberry Pi 5 Basic Case (Remix)',
      remixed_from_id: 'starter-1',
      remixed_from_name: 'Raspberry Pi 5 Basic Case',
      enclosure_spec: {},
      created_at: new Date().toISOString(),
    });
  });

  it('renders the page header', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Starter Designs')).toBeInTheDocument();
    });
  });

  it('displays starters after loading', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 5 Basic Case')).toBeInTheDocument();
      expect(screen.getByText('Arduino Uno Shield Case')).toBeInTheDocument();
    });
  });

  it('shows dimensions for each starter', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/100 × 70 × 30 mm/)).toBeInTheDocument();
    });
  });

  it('displays category pills', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      // Category pills may appear multiple times in filters and cards
      expect(screen.getAllByText(/Raspberry Pi/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Arduino/).length).toBeGreaterThanOrEqual(1);
    });
  });

  it('shows remix count for starters', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      // Remix counts should be visible
      expect(screen.getByText('50')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });

  it('displays remix buttons', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      const remixButtons = screen.getAllByText('Remix This Design');
      expect(remixButtons.length).toBe(2);
    });
  });

  it('shows total starter count', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/2 starter designs available/)).toBeInTheDocument();
    });
  });

  it('calls getStarters on mount', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      expect(api.getStarters).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 1,
          page_size: 12,
        })
      );
    });
  });

  it('displays CTA section for custom designs', async () => {
    render(<StartersPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("Can't find what you need?")).toBeInTheDocument();
      expect(screen.getByText('Create from Scratch')).toBeInTheDocument();
    });
  });
});
