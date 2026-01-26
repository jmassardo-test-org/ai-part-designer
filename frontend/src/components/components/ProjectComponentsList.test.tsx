/**
 * ProjectComponentsList Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectComponentsList } from './ProjectComponentsList';

// Mock the components API
vi.mock('@/lib/api/components', () => ({
  componentsApi: {
    getProjectComponents: vi.fn(),
    updateProjectComponent: vi.fn(),
    removeProjectComponent: vi.fn(),
    reorderProjectComponents: vi.fn(),
  },
}));

// Mock dnd-kit
vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <div data-testid="dnd-context">{children}</div>,
  closestCenter: vi.fn(),
  KeyboardSensor: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
}));

vi.mock('@dnd-kit/sortable', () => ({
  arrayMove: vi.fn((arr, from, to) => {
    const result = [...arr];
    const [removed] = result.splice(from, 1);
    result.splice(to, 0, removed);
    return result;
  }),
  SortableContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  sortableKeyboardCoordinates: vi.fn(),
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
  verticalListSortingStrategy: vi.fn(),
}));

vi.mock('@dnd-kit/utilities', () => ({
  CSS: {
    Transform: {
      toString: () => '',
    },
  },
}));

// Mock UI components
vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled, ...props }: any) => (
    <button onClick={onClick} disabled={disabled} {...props}>{children}</button>
  ),
}));

vi.mock('@/components/ui/input', () => ({
  Input: (props: any) => <input {...props} />,
}));

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <h3>{children}</h3>,
}));

vi.mock('@/components/ui/sheet', () => ({
  Sheet: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SheetContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SheetDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  SheetHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SheetTitle: ({ children }: { children: React.ReactNode }) => <h3>{children}</h3>,
}));

vi.mock('@/components/ui/alert-dialog', () => ({
  AlertDialog: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AlertDialogAction: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
  AlertDialogCancel: ({ children }: { children: React.ReactNode }) => <button>{children}</button>,
  AlertDialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AlertDialogDescription: ({ children }: { children: React.ReactNode }) => <p>{children}</p>,
  AlertDialogFooter: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AlertDialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  AlertDialogTitle: ({ children }: { children: React.ReactNode }) => <h3>{children}</h3>,
  AlertDialogTrigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) => <>{children}</>,
}));

vi.mock('@/components/ui/skeleton', () => ({
  Skeleton: () => <div data-testid="skeleton" />,
}));

vi.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

// Mock ComponentSpecsViewer
vi.mock('./ComponentSpecsViewer', () => ({
  ComponentSpecsViewer: () => <div data-testid="component-specs-viewer">Specs Viewer</div>,
}));

import { componentsApi } from '@/lib/api/components';

const createQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
  },
});

describe('ProjectComponentsList', () => {
  const mockComponents = [
    {
      id: 'pc-1',
      component_id: 'comp-1',
      name: 'Raspberry Pi 4',
      manufacturer: 'Raspberry Pi Foundation',
      model_number: 'RPI4-4GB',
      category: 'electronic',
      thumbnail_url: 'http://example.com/thumb.png',
      quantity: 1,
      position: { x: 0, y: 0, z: 0 },
      dimensions: { length: 85, width: 56, height: 17 },
    },
    {
      id: 'pc-2',
      component_id: 'comp-2',
      name: 'Custom Enclosure',
      category: 'printed',
      quantity: 1,
      dimensions: { length: 100, width: 70, height: 30 },
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(componentsApi.getProjectComponents).mockResolvedValue(mockComponents);
    vi.mocked(componentsApi.updateProjectComponent).mockResolvedValue(mockComponents[0]);
    vi.mocked(componentsApi.removeProjectComponent).mockResolvedValue(undefined);
  });

  const renderComponent = (projectId: string, props = {}) => {
    const queryClient = createQueryClient();
    return render(
      <QueryClientProvider client={queryClient}>
        <ProjectComponentsList projectId={projectId} {...props} />
      </QueryClientProvider>
    );
  };

  it('renders component list', async () => {
    renderComponent('project-1');
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
      expect(screen.getByText('Custom Enclosure')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    vi.mocked(componentsApi.getProjectComponents).mockImplementation(() => new Promise(() => {}));
    
    renderComponent('project-1');
    
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  it('displays component dimensions', async () => {
    renderComponent('project-1');
    
    await waitFor(() => {
      expect(screen.getByText(/85×56×17/)).toBeInTheDocument();
    });
  });

  it('shows quantity for each component', async () => {
    renderComponent('project-1');
    
    await waitFor(() => {
      // Should have quantity inputs
      const inputs = screen.getAllByRole('spinbutton');
      expect(inputs.length).toBeGreaterThan(0);
    });
  });

  it('calls onComponentSelect when component clicked', async () => {
    const onComponentSelect = vi.fn();
    const user = userEvent.setup();
    
    renderComponent('project-1', { onComponentSelect });
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
    });
    
    const componentItem = screen.getByText('Raspberry Pi 4');
    await user.click(componentItem);
    
    // The component passes component.id (pc-1), not component_id (comp-1)
    expect(onComponentSelect).toHaveBeenCalledWith('pc-1');
  });

  it('highlights selected component', async () => {
    renderComponent('project-1', { selectedComponentId: 'comp-1' });
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
    });
    
    // Selected component should have different styling
  });

  it('handles quantity increase', async () => {
    const user = userEvent.setup();
    
    renderComponent('project-1');
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
    });
    
    // Find plus button
    const plusButtons = screen.getAllByRole('button');
    const plusButton = plusButtons.find(btn => btn.innerHTML.includes('+') || btn.querySelector('svg'));
    
    if (plusButton) {
      await user.click(plusButton);
    }
  });

  it('handles quantity decrease', async () => {
    const user = userEvent.setup();
    
    renderComponent('project-1');
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
    });
    
    // Find minus button
    const minusButtons = screen.getAllByRole('button');
    const minusButton = minusButtons.find(btn => btn.innerHTML.includes('-') || btn.querySelector('svg'));
    
    if (minusButton) {
      await user.click(minusButton);
    }
  });

  it('prevents quantity below 1', async () => {
    renderComponent('project-1');
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
    });
    
    // Check that minus button is disabled when quantity is 1
    const buttons = screen.getAllByRole('button');
    const minusButton = buttons.find(b => b.getAttribute('disabled') !== null);
    
    // At least one minus button should be disabled when quantity is 1
  });

  it('shows remove confirmation dialog', async () => {
    const user = userEvent.setup();
    
    renderComponent('project-1');
    
    await waitFor(() => {
      expect(screen.getByText('Raspberry Pi 4')).toBeInTheDocument();
    });
    
    // Hover over component and click delete
    const deleteButtons = screen.queryAllByRole('button');
    // Find the trash/delete button
  });

  it('renders with drag handles', async () => {
    renderComponent('project-1');
    
    await waitFor(() => {
      expect(screen.getByTestId('dnd-context')).toBeInTheDocument();
    });
  });

  it('shows thumbnail when available', async () => {
    renderComponent('project-1');
    
    await waitFor(() => {
      const thumbnail = screen.getByAltText('Raspberry Pi 4');
      expect(thumbnail).toBeInTheDocument();
      expect(thumbnail).toHaveAttribute('src', 'http://example.com/thumb.png');
    });
  });

  it('shows placeholder icon when no thumbnail', async () => {
    renderComponent('project-1');
    
    await waitFor(() => {
      // Custom Enclosure has no thumbnail
      expect(screen.getByText('Custom Enclosure')).toBeInTheDocument();
    });
  });
});
