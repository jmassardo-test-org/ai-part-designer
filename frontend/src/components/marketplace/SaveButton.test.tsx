/**
 * Tests for the SaveButton component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { SaveButton } from './SaveButton';
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
  checkSaveStatus: vi.fn(),
  saveDesign: vi.fn(),
  unsaveDesign: vi.fn(),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
);

describe('SaveButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.checkSaveStatus as any).mockResolvedValue({
      design_id: 'design-1',
      is_saved: false,
      in_lists: [],
    });
    (api.saveDesign as any).mockResolvedValue({
      design_id: 'design-1',
      saved_at: new Date().toISOString(),
      lists: [],
    });
    (api.unsaveDesign as any).mockResolvedValue({
      design_id: 'design-1',
      removed_from_lists: 1,
    });
  });

  it('renders with unsaved state by default', async () => {
    render(<SaveButton designId="design-1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Save')).toBeInTheDocument();
    });
  });

  it('renders with saved state when initialSaved is true', () => {
    (api.checkSaveStatus as any).mockResolvedValue({
      design_id: 'design-1',
      is_saved: true,
      in_lists: ['list-1'],
    });

    render(<SaveButton designId="design-1" initialSaved />, { wrapper });

    expect(screen.getByText('Saved')).toBeInTheDocument();
  });

  it('calls saveDesign when clicking unsaved button', async () => {
    render(<SaveButton designId="design-1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(api.saveDesign).toHaveBeenCalledWith('design-1', undefined, 'test-token');
    });
  });

  it('calls unsaveDesign when clicking saved button', async () => {
    (api.checkSaveStatus as any).mockResolvedValue({
      design_id: 'design-1',
      is_saved: true,
      in_lists: ['list-1'],
    });

    render(<SaveButton designId="design-1" />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Saved')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(api.unsaveDesign).toHaveBeenCalledWith('design-1', 'test-token');
    });
  });

  it('calls onSaveChange callback after save', async () => {
    const onSaveChange = vi.fn();
    render(<SaveButton designId="design-1" onSaveChange={onSaveChange} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Save')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(onSaveChange).toHaveBeenCalledWith('design-1', true);
    });
  });

  it('renders icon variant correctly', async () => {
    render(<SaveButton designId="design-1" variant="icon" />, { wrapper });

    await waitFor(() => {
      const button = screen.getByRole('button');
      expect(button).toHaveClass('rounded-full');
    });
  });
});
