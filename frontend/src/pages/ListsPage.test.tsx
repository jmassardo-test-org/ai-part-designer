/**
 * Tests for the ListsPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ListsPage } from './ListsPage';
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
  getMyLists: vi.fn(),
  createList: vi.fn(),
  deleteList: vi.fn(),
}));

const mockLists = [
  {
    id: 'list-1',
    name: 'Favorites',
    description: 'My favorite designs',
    icon: 'heart',
    color: '#ef4444',
    is_public: false,
    position: 0,
    item_count: 5,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'list-2',
    name: 'Arduino Projects',
    description: 'All my Arduino enclosures',
    icon: 'folder',
    color: '#3b82f6',
    is_public: true,
    position: 1,
    item_count: 3,
    created_at: '2025-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
  },
];

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
);

describe('ListsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.getMyLists as any).mockResolvedValue(mockLists);
    (api.createList as any).mockImplementation(async (data: any) => ({
      id: 'list-new',
      ...data,
      item_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));
    (api.deleteList as any).mockResolvedValue(undefined);
  });

  it('renders the page header', async () => {
    render(<ListsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('My Lists')).toBeInTheDocument();
    });
  });

  it('displays lists after loading', async () => {
    render(<ListsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Favorites')).toBeInTheDocument();
      expect(screen.getByText('Arduino Projects')).toBeInTheDocument();
    });
  });

  it('shows item counts for each list', async () => {
    render(<ListsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('5 designs')).toBeInTheDocument();
      expect(screen.getByText('3 designs')).toBeInTheDocument();
    });
  });

  it('shows public badge for public lists', async () => {
    render(<ListsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Public')).toBeInTheDocument();
    });
  });

  it('opens create dialog when clicking New List button', async () => {
    render(<ListsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('New List')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('New List'));

    await waitFor(() => {
      expect(screen.getByText('Create New List')).toBeInTheDocument();
    });
  });

  it('shows empty state when no lists exist', async () => {
    (api.getMyLists as any).mockResolvedValue([]);

    render(<ListsPage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('No lists yet')).toBeInTheDocument();
    });
  });

  it('calls getMyLists on mount', async () => {
    render(<ListsPage />, { wrapper });

    await waitFor(() => {
      expect(api.getMyLists).toHaveBeenCalledWith('test-token');
    });
  });
});
