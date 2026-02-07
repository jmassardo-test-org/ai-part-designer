/**
 * ComponentSpecsViewer Component Tests
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { componentsApi } from '@/lib/api/components';
import { ComponentSpecsViewer } from './ComponentSpecsViewer';

// Mock the components API
vi.mock('@/lib/api/components', () => ({
  componentsApi: {
    getComponent: vi.fn(),
  },
}));

// Mock UI components
vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <span data-testid="badge" className={className}>{children}</span>
  ),
}));

vi.mock('@/components/ui/skeleton', () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}));

vi.mock('@/components/ui/tabs', () => ({
  Tabs: ({ children, defaultValue }: { children: React.ReactNode; defaultValue?: string }) => (
    <div data-testid="tabs" data-default={defaultValue}>{children}</div>
  ),
  TabsContent: ({ children, value }: { children: React.ReactNode; value: string }) => (
    <div data-testid={`tab-content-${value}`}>{children}</div>
  ),
  TabsList: ({ children }: { children: React.ReactNode }) => <div data-testid="tabs-list">{children}</div>,
  TabsTrigger: ({ children, value }: { children: React.ReactNode; value: string }) => (
    <button data-testid={`tab-trigger-${value}`}>{children}</button>
  ),
}));

vi.mock('@/components/ui/progress', () => ({
  Progress: ({ value }: { value: number }) => (
    <div data-testid="progress" data-value={value} />
  ),
}));


const createQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

describe('ComponentSpecsViewer', () => {
  const mockSpecs = {
    id: 'comp-1',
    name: 'Raspberry Pi 4',
    dimensions: {
      length: 85,
      width: 56,
      height: 17,
      pcb_thickness: 1.6,
    },
    mounting_holes: [
      { x: 3.5, y: 3.5, diameter: 2.7, type: 'M2.5', label: 'Corner 1' },
      { x: 81.5, y: 3.5, diameter: 2.7, type: 'M2.5', label: 'Corner 2' },
    ],
    connectors: [
      { name: 'USB-C Power', type: 'USB-C', x: 10, y: 0, width: 9, height: 3, side: 'bottom' },
      { name: 'HDMI 0', type: 'micro-HDMI', x: 24, y: 0, width: 6, height: 3, side: 'bottom' },
    ],
    clearance_zones: [
      { name: 'CPU Heatsink', x: 25, y: 20, width: 15, height: 15, z_height: 10, side: 'top' },
    ],
    thermal_properties: {
      max_temp_c: 85,
      recommended_ventilation: true,
      heat_zones: [{ x: 25, y: 20, radius: 10 }],
    },
    weight_grams: 46,
    datasheet_url: 'https://example.com/datasheet.pdf',
    is_verified: true,
    confidence: 0.95,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(componentsApi.getComponent).mockResolvedValue(mockSpecs);
  });

  const renderComponent = (componentId: string, props = {}) => {
    const queryClient = createQueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <ComponentSpecsViewer componentId={componentId} {...props} />
      </QueryClientProvider>
    );
  };

  it('shows loading state initially', () => {
    vi.mocked(componentsApi.getComponent).mockImplementation(() => new Promise(() => {}));
    
    renderComponent('comp-1');
    
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  it('fetches component specs on mount', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(componentsApi.getComponent).toHaveBeenCalledWith('comp-1');
    });
  });

  it('displays component name when showTitle is true', async () => {
    renderComponent('comp-1', { showTitle: true });
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
    });
  });

  it('shows verified badge for verified components', async () => {
    renderComponent('comp-1', { showTitle: true });
    
    await waitFor(() => {
      expect(screen.getByText(/verified/i)).toBeInTheDocument();
    });
  });

  it('displays confidence progress bar', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      const progress = screen.getByTestId('progress');
      expect(progress).toHaveAttribute('data-value', '95');
    });
  });

  it('renders dimension tabs', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(screen.getByTestId('tabs')).toBeInTheDocument();
      expect(screen.getByTestId('tab-trigger-dimensions')).toBeInTheDocument();
    });
  });

  it('shows mounting holes tab', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(screen.getByTestId('tab-trigger-mounting')).toBeInTheDocument();
    });
  });

  it('shows connectors tab', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(screen.getByTestId('tab-trigger-connectors')).toBeInTheDocument();
    });
  });

  it('shows clearance tab', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(screen.getByTestId('tab-trigger-clearance')).toBeInTheDocument();
    });
  });

  it('shows thermal tab in non-compact mode', async () => {
    renderComponent('comp-1', { compact: false });
    
    await waitFor(() => {
      expect(screen.getByTestId('tab-trigger-thermal')).toBeInTheDocument();
    });
  });

  it('hides thermal tab in compact mode', async () => {
    renderComponent('comp-1', { compact: true });
    
    await waitFor(() => {
      expect(screen.queryByTestId('tab-trigger-thermal')).not.toBeInTheDocument();
    });
  });

  it('shows error state when fetch fails', async () => {
    vi.mocked(componentsApi.getComponent).mockRejectedValue(new Error('Fetch failed'));
    
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(screen.getByText(/failed to load specifications/i)).toBeInTheDocument();
    });
  });

  it('displays dimensions values', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      // Dimensions should be displayed in the form: 85 × 56 × 17 mm or similar
      const container = document.body;
      expect(container.textContent).toMatch(/85/);
      expect(container.textContent).toMatch(/56/);
      expect(container.textContent).toMatch(/17/);
    });
  });

  it('uses default showTitle value of false', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(screen.queryByText('Raspberry Pi 4')).not.toBeInTheDocument();
    });
  });

  it('uses default compact value of false', async () => {
    renderComponent('comp-1');
    
    await waitFor(() => {
      expect(screen.getByTestId('tab-trigger-thermal')).toBeInTheDocument();
    });
  });
});
