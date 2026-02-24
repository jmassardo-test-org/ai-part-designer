/**
 * Tests for the ThreadWizard component.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import { ThreadWizard } from './ThreadWizard';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockFamilies = {
  families: [
    {
      family: 'iso_metric',
      name: 'ISO Metric',
      description: 'Standard metric threads per ISO 261',
      standard_ref: 'ISO 261',
      size_count: 42,
    },
    {
      family: 'unc',
      name: 'Unified National Coarse',
      description: 'Coarse pitch unified inch threads',
      standard_ref: 'ANSI/ASME B1.1',
      size_count: 25,
    },
  ],
  total: 2,
};

const mockSizes = {
  family: 'iso_metric',
  sizes: ['M3', 'M4', 'M5', 'M6', 'M8'],
  total: 5,
  pitch_series: null,
};

const mockSpec = {
  family: 'iso_metric',
  size: 'M8',
  pitch_mm: 1.25,
  form: 'V60',
  pitch_series: 'coarse',
  major_diameter: 8.0,
  pitch_diameter_ext: 7.188,
  minor_diameter_ext: 6.647,
  major_diameter_int: 8.0,
  pitch_diameter_int: 7.188,
  minor_diameter_int: 6.647,
  profile_angle_deg: 60,
  taper_per_mm: 0,
  tap_drill_mm: 6.8,
  clearance_hole_close_mm: 8.4,
  clearance_hole_medium_mm: 9.0,
  clearance_hole_free_mm: 10.0,
  tpi: null,
  nominal_size_inch: null,
  engagement_length_mm: 10.0,
  standard_ref: 'ISO 261',
  notes: '',
};

const mockTapDrill = {
  family: 'iso_metric',
  size: 'M8',
  tap_drill_mm: 6.8,
  clearance_hole_close_mm: 8.4,
  clearance_hole_medium_mm: 9.0,
  clearance_hole_free_mm: 10.0,
};

const mockGenerateResult = {
  success: true,
  metadata: {},
  generation_time_ms: 142.5,
  estimated_face_count: 3200,
  message: 'Thread generated successfully',
};

// Mock the hooks module
vi.mock('@/hooks/useThreads', () => ({
  useThreadFamilies: vi.fn(() => ({
    data: mockFamilies,
    isLoading: false,
    error: null,
  })),
  useThreadSizes: vi.fn(() => ({
    data: mockSizes,
    isLoading: false,
    error: null,
  })),
  useThreadSpec: vi.fn(() => ({
    data: mockSpec,
    isLoading: false,
    error: null,
  })),
  useTapDrill: vi.fn(() => ({
    data: mockTapDrill,
    isLoading: false,
    error: null,
  })),
  useGenerateThread: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    isSuccess: false,
    isError: false,
    data: null,
    error: null,
    reset: vi.fn(),
  })),
  useGeneratePrintOptimized: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    isSuccess: false,
    isError: false,
    data: null,
    error: null,
    reset: vi.fn(),
  })),
  usePrintRecommendation: vi.fn(() => ({
    data: null,
    isLoading: false,
    error: null,
  })),
}));

// Captured props ref for PrintOptimizationForm mock
let capturedPrintOptProps: Record<string, any> = {};

// Mock sub-components to keep tests focused
vi.mock('@/components/threads/PrintOptimizationForm', () => ({
  PrintOptimizationForm: (props: any) => {
    capturedPrintOptProps = props;
    return <div data-testid="print-optimization-form" data-enabled={props.enabled} />;
  },
}));

vi.mock('@/components/threads/ThreadPreview3D', () => ({
  ThreadPreview3D: (props: any) => <div data-testid="thread-preview-3d" data-thread-type={props.threadType} />,
}));

// Mock AuthContext
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

function renderWizard(props: Partial<React.ComponentProps<typeof ThreadWizard>> = {}) {
  const qc = createTestQueryClient();
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onGenerate: vi.fn(),
    ...props,
  };

  return {
    ...render(
      React.createElement(
        QueryClientProvider,
        { client: qc },
        React.createElement(ThreadWizard, defaultProps),
      ),
    ),
    onClose: defaultProps.onClose,
    onGenerate: defaultProps.onGenerate,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ThreadWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders when open', () => {
    renderWizard();
    expect(screen.getByTestId('thread-wizard')).toBeInTheDocument();
    expect(screen.getByText('Thread Wizard')).toBeInTheDocument();
  });

  it('does not render content when closed', () => {
    renderWizard({ isOpen: false });
    expect(screen.queryByTestId('thread-wizard')).not.toBeInTheDocument();
  });

  it('shows family selection on first step', () => {
    renderWizard();
    expect(screen.getByTestId('family-list')).toBeInTheDocument();
    expect(screen.getByTestId('family-iso_metric')).toBeInTheDocument();
    expect(screen.getByTestId('family-unc')).toBeInTheDocument();
    expect(screen.getByText('ISO Metric')).toBeInTheDocument();
  });

  it('navigates to size step after selecting family and clicking next', async () => {
    renderWizard();

    // Select a family
    fireEvent.click(screen.getByTestId('family-iso_metric'));

    // Click next
    fireEvent.click(screen.getByTestId('wizard-next'));

    await waitFor(() => {
      expect(screen.getByTestId('size-list')).toBeInTheDocument();
    });
  });

  it('navigates back from size step to family step', async () => {
    renderWizard();

    // Go to size step
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    fireEvent.click(screen.getByTestId('wizard-next'));

    await waitFor(() => {
      expect(screen.getByTestId('size-list')).toBeInTheDocument();
    });

    // Go back
    fireEvent.click(screen.getByTestId('wizard-back'));

    await waitFor(() => {
      expect(screen.getByTestId('family-list')).toBeInTheDocument();
    });
  });

  it('navigates through all steps to generate step', async () => {
    renderWizard();

    // Step 1: Select family
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    fireEvent.click(screen.getByTestId('wizard-next'));

    // Step 2: Select size
    await waitFor(() => {
      expect(screen.getByTestId('size-list')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('size-M8'));
    fireEvent.click(screen.getByTestId('wizard-next'));

    // Step 3: Configure
    await waitFor(() => {
      expect(screen.getByTestId('configure-step')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('wizard-next'));

    // Step 4: Generate
    await waitFor(() => {
      expect(screen.getByTestId('generate-step')).toBeInTheDocument();
    });
    expect(screen.getByTestId('generate-button')).toBeInTheDocument();
  });

  it('disables next button when no family is selected', () => {
    renderWizard();
    expect(screen.getByTestId('wizard-next')).toBeDisabled();
  });

  it('enables next button after family selection', () => {
    renderWizard();
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    expect(screen.getByTestId('wizard-next')).toBeEnabled();
  });

  it('disables back button on first step', () => {
    renderWizard();
    expect(screen.getByTestId('wizard-back')).toBeDisabled();
  });

  it('calls onClose when cancel is clicked', () => {
    const { onClose } = renderWizard();
    fireEvent.click(screen.getByTestId('wizard-close'));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('shows step progress indicator', () => {
    renderWizard();
    expect(screen.getByTestId('step-indicator')).toBeInTheDocument();
    // 4 step bars
    expect(screen.getByTestId('step-indicator').children).toHaveLength(4);
  });

  it('calls generate mutation and invokes onGenerate on success', async () => {
    // Override useGenerateThread to capture mutate call
    const mockMutate = vi.fn((_, options) => {
      // Simulate immediate success callback
      options?.onSuccess?.(mockGenerateResult);
    });

    const { useGenerateThread } = await import('@/hooks/useThreads');
    (useGenerateThread as ReturnType<typeof vi.fn>).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      data: null,
      error: null,
      reset: vi.fn(),
    });

    const { onGenerate } = renderWizard();

    // Navigate to generate step
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('size-list')).toBeInTheDocument(); });
    fireEvent.click(screen.getByTestId('size-M8'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('configure-step')).toBeInTheDocument(); });
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('generate-step')).toBeInTheDocument(); });

    // Click generate
    fireEvent.click(screen.getByTestId('generate-button'));

    expect(mockMutate).toHaveBeenCalledTimes(1);
    expect(onGenerate).toHaveBeenCalledWith(mockGenerateResult);
  });

  it('shows PrintOptimizationForm on the configure step', async () => {
    renderWizard();

    // Navigate to configure step
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('size-list')).toBeInTheDocument(); });
    fireEvent.click(screen.getByTestId('size-M8'));
    fireEvent.click(screen.getByTestId('wizard-next'));

    await waitFor(() => {
      expect(screen.getByTestId('configure-step')).toBeInTheDocument();
    });

    expect(screen.getByTestId('print-optimization-form')).toBeInTheDocument();
  });

  it('shows pitch series toggle for ISO Metric family on the size step', async () => {
    renderWizard();

    // Select ISO Metric family and navigate to size step
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    fireEvent.click(screen.getByTestId('wizard-next'));

    await waitFor(() => {
      expect(screen.getByTestId('size-list')).toBeInTheDocument();
    });

    // Pitch series toggle buttons should be visible
    expect(screen.getByRole('button', { name: 'Coarse' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Fine' })).toBeInTheDocument();
  });

  it('shows ThreadPreview3D on the generate step', async () => {
    renderWizard();

    // Navigate all the way to generate step
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('size-list')).toBeInTheDocument(); });
    fireEvent.click(screen.getByTestId('size-M8'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('configure-step')).toBeInTheDocument(); });
    fireEvent.click(screen.getByTestId('wizard-next'));

    await waitFor(() => {
      expect(screen.getByTestId('generate-step')).toBeInTheDocument();
    });

    expect(screen.getByTestId('thread-preview-3d')).toBeInTheDocument();
  });

  it('calls print-optimized endpoint when print optimization is enabled', async () => {
    const mockPrintOptMutate = vi.fn((_, options) => {
      options?.onSuccess?.({
        success: true,
        message: 'Print-optimized thread generated',
        generation_result: mockGenerateResult,
      });
    });

    const { useGeneratePrintOptimized } = await import('@/hooks/useThreads');
    (useGeneratePrintOptimized as ReturnType<typeof vi.fn>).mockReturnValue({
      mutate: mockPrintOptMutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      data: null,
      error: null,
      reset: vi.fn(),
    });

    const { useGenerateThread } = await import('@/hooks/useThreads');
    const mockStandardMutate = vi.fn();
    (useGenerateThread as ReturnType<typeof vi.fn>).mockReturnValue({
      mutate: mockStandardMutate,
      isPending: false,
      isSuccess: false,
      isError: false,
      data: null,
      error: null,
      reset: vi.fn(),
    });

    const { onGenerate } = renderWizard();

    // Navigate to configure step
    fireEvent.click(screen.getByTestId('family-iso_metric'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('size-list')).toBeInTheDocument(); });
    fireEvent.click(screen.getByTestId('size-M8'));
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('configure-step')).toBeInTheDocument(); });

    // Enable print optimization by calling the captured callback from
    // the mocked PrintOptimizationForm
    expect(capturedPrintOptProps.onEnabledChange).toBeDefined();
    act(() => {
      capturedPrintOptProps.onEnabledChange(true);
    });

    // Verify the form now reflects enabled state
    await waitFor(() => {
      expect(screen.getByTestId('print-optimization-form').getAttribute('data-enabled')).toBe('true');
    });

    // Proceed to generate step
    fireEvent.click(screen.getByTestId('wizard-next'));
    await waitFor(() => { expect(screen.getByTestId('generate-step')).toBeInTheDocument(); });

    // Click generate
    fireEvent.click(screen.getByTestId('generate-button'));

    // Print-optimized mutation should have been called, NOT the standard one
    expect(mockPrintOptMutate).toHaveBeenCalledTimes(1);
    expect(mockStandardMutate).not.toHaveBeenCalled();
    expect(onGenerate).toHaveBeenCalledWith(mockGenerateResult);
  });
});
