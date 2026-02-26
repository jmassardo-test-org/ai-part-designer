/**
 * Tests for the TapDrillReference component.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { TapDrillReference } from './TapDrillReference';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockTapDrill = {
  family: 'iso_metric',
  size: 'M8',
  tap_drill_mm: 6.8,
  clearance_hole_close_mm: 8.4,
  clearance_hole_medium_mm: 9.0,
  clearance_hole_free_mm: 10.0,
};

const mockUseTapDrill = vi.fn((_family: string | null, _size: string | null) => ({
  data: mockTapDrill as typeof mockTapDrill | undefined,
  isLoading: false as boolean,
  error: null as Error | null,
}));

vi.mock('@/hooks/useThreads', () => ({
  useTapDrill: (family: string | null, size: string | null) => mockUseTapDrill(family, size),
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'mock-token',
    user: { id: 'user-1', email: 'test@test.com' },
    isAuthenticated: true,
    isLoading: false,
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function renderComponent(props = { family: 'iso_metric', size: 'M8' }) {
  const qc = createTestQueryClient();
  return render(
    React.createElement(
      QueryClientProvider,
      { client: qc },
      React.createElement(TapDrillReference, props),
    ),
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('TapDrillReference', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseTapDrill.mockReturnValue({
      data: mockTapDrill,
      isLoading: false,
      error: null,
    });
  });

  it('renders loading state', () => {
    mockUseTapDrill.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    renderComponent();

    expect(screen.getByTestId('tap-drill-loading')).toBeInTheDocument();
    expect(screen.getByText(/loading tap drill data/i)).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseTapDrill.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Network error'),
    });

    renderComponent();

    expect(screen.getByTestId('tap-drill-error')).toBeInTheDocument();
    expect(screen.getByText(/failed to load tap drill information/i)).toBeInTheDocument();
  });

  it('displays tap drill data', () => {
    renderComponent();

    expect(screen.getByTestId('tap-drill-table')).toBeInTheDocument();
    expect(screen.getByTestId('tap-drill-value')).toHaveTextContent('6.80');
  });

  it('shows all clearance hole types', () => {
    renderComponent();

    expect(screen.getByTestId('clearance-close-value')).toHaveTextContent('8.40');
    expect(screen.getByTestId('clearance-medium-value')).toHaveTextContent('9.00');
    expect(screen.getByTestId('clearance-free-value')).toHaveTextContent('10.00');
  });

  it('renders all measurement labels', () => {
    renderComponent();

    expect(screen.getByText('Tap Drill')).toBeInTheDocument();
    expect(screen.getByText('Clearance – Close')).toBeInTheDocument();
    expect(screen.getByText('Clearance – Medium')).toBeInTheDocument();
    expect(screen.getByText('Clearance – Free')).toBeInTheDocument();
  });

  it('renders nothing when no data and not loading', () => {
    mockUseTapDrill.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });

    const { container } = renderComponent();
    expect(container.innerHTML).toBe('');
  });

  it('passes family and size to the hook', () => {
    renderComponent({ family: 'unc', size: '1/4-20' });
    expect(mockUseTapDrill).toHaveBeenCalledWith('unc', '1/4-20');
  });
});
