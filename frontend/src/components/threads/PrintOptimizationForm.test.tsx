/**
 * Tests for the PrintOptimizationForm component.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

import type { PrintRecommendation } from '@/types/threads';

import { PrintOptimizationForm, type PrintOptimizationFormProps } from './PrintOptimizationForm';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

const mockRecommendation: PrintRecommendation = {
  family: 'iso_metric',
  size: 'M8',
  feasibility: 'good',
  min_recommended_size: 'M6',
  recommended_tolerance: 'standard',
  clearance_mm: 0.3,
  notes: ['Use supports for overhangs', 'Orient vertically for best results'],
  orientation_advice: 'Print vertically with thread axis aligned to Z',
  estimated_strength_pct: 75,
};

const mockUsePrintRecommendation = vi.fn(
  (_family?: string | null, _size?: string | null, _process?: string) => ({
    data: undefined as PrintRecommendation | undefined,
    isLoading: false,
    error: null as Error | null,
  }),
);

vi.mock('@/hooks/useThreads', () => ({
  usePrintRecommendation: (
    family: string | null,
    size: string | null,
    process?: string,
  ) => mockUsePrintRecommendation(family, size, process),
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
}

function defaultProps(overrides: Partial<PrintOptimizationFormProps> = {}): PrintOptimizationFormProps {
  return {
    enabled: false,
    onEnabledChange: vi.fn(),
    process: 'fdm',
    onProcessChange: vi.fn(),
    toleranceClass: 'standard',
    onToleranceClassChange: vi.fn(),
    nozzleDiameterMm: 0.4,
    onNozzleDiameterChange: vi.fn(),
    layerHeightMm: 0.2,
    onLayerHeightChange: vi.fn(),
    useFlatBottom: false,
    onFlatBottomChange: vi.fn(),
    customClearanceMm: null,
    onCustomClearanceChange: vi.fn(),
    family: null,
    size: null,
    ...overrides,
  };
}

function renderForm(props: Partial<PrintOptimizationFormProps> = {}) {
  const qc = createQueryClient();
  return render(
    <QueryClientProvider client={qc}>
      <PrintOptimizationForm {...defaultProps(props)} />
    </QueryClientProvider>,
  );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PrintOptimizationForm', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUsePrintRecommendation.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
  });

  // ---- Toggle behaviour ----

  describe('toggle behaviour', () => {
    it('renders the toggle switch', () => {
      renderForm();
      expect(screen.getByTestId('print-opt-toggle')).toBeInTheDocument();
    });

    it('shows muted message when disabled', () => {
      renderForm({ enabled: false });
      expect(
        screen.getByText('Standard thread geometry will be generated.'),
      ).toBeInTheDocument();
    });

    it('does not show controls when disabled', () => {
      renderForm({ enabled: false });
      expect(screen.queryByTestId('process-select')).not.toBeInTheDocument();
      expect(screen.queryByTestId('tolerance-select')).not.toBeInTheDocument();
    });

    it('calls onEnabledChange when toggle is clicked', () => {
      const onEnabledChange = vi.fn();
      renderForm({ enabled: false, onEnabledChange });
      fireEvent.click(screen.getByTestId('print-opt-toggle'));
      expect(onEnabledChange).toHaveBeenCalledWith(true);
    });

    it('shows controls when enabled', () => {
      renderForm({ enabled: true });
      expect(screen.getByTestId('process-select')).toBeInTheDocument();
      expect(screen.getByTestId('tolerance-select')).toBeInTheDocument();
    });

    it('does not show muted message when enabled', () => {
      renderForm({ enabled: true });
      expect(
        screen.queryByText('Standard thread geometry will be generated.'),
      ).not.toBeInTheDocument();
    });
  });

  // ---- FDM-specific controls ----

  describe('FDM-specific controls', () => {
    it('shows nozzle, layer height, and flat-bottom when process is FDM', () => {
      renderForm({ enabled: true, process: 'fdm' });
      expect(screen.getByTestId('nozzle-input')).toBeInTheDocument();
      expect(screen.getByTestId('layer-height-input')).toBeInTheDocument();
      expect(screen.getByTestId('flat-bottom-checkbox')).toBeInTheDocument();
    });

    it('hides FDM controls when process is SLA', () => {
      renderForm({ enabled: true, process: 'sla' });
      expect(screen.queryByTestId('nozzle-input')).not.toBeInTheDocument();
      expect(screen.queryByTestId('layer-height-input')).not.toBeInTheDocument();
      expect(screen.queryByTestId('flat-bottom-checkbox')).not.toBeInTheDocument();
    });

    it('hides FDM controls when process is SLS', () => {
      renderForm({ enabled: true, process: 'sls' });
      expect(screen.queryByTestId('nozzle-input')).not.toBeInTheDocument();
      expect(screen.queryByTestId('layer-height-input')).not.toBeInTheDocument();
      expect(screen.queryByTestId('flat-bottom-checkbox')).not.toBeInTheDocument();
    });

    it('calls onNozzleDiameterChange with clamped value', () => {
      const onNozzleDiameterChange = vi.fn();
      renderForm({ enabled: true, process: 'fdm', onNozzleDiameterChange });
      const input = screen.getByTestId('nozzle-input');
      fireEvent.change(input, { target: { value: '1.5' } });
      // Should clamp to 1.0 max
      expect(onNozzleDiameterChange).toHaveBeenCalledWith(1.0);
    });

    it('calls onNozzleDiameterChange with lower-bound clamped value', () => {
      const onNozzleDiameterChange = vi.fn();
      renderForm({ enabled: true, process: 'fdm', onNozzleDiameterChange });
      const input = screen.getByTestId('nozzle-input');
      fireEvent.change(input, { target: { value: '0.01' } });
      expect(onNozzleDiameterChange).toHaveBeenCalledWith(0.1);
    });

    it('calls onLayerHeightChange with clamped value', () => {
      const onLayerHeightChange = vi.fn();
      renderForm({ enabled: true, process: 'fdm', onLayerHeightChange });
      const input = screen.getByTestId('layer-height-input');
      fireEvent.change(input, { target: { value: '0.8' } });
      expect(onLayerHeightChange).toHaveBeenCalledWith(0.5);
    });

    it('calls onFlatBottomChange when flat-bottom toggle is clicked', () => {
      const onFlatBottomChange = vi.fn();
      renderForm({ enabled: true, process: 'fdm', useFlatBottom: false, onFlatBottomChange });
      fireEvent.click(screen.getByTestId('flat-bottom-checkbox'));
      expect(onFlatBottomChange).toHaveBeenCalledWith(true);
    });
  });

  // ---- Custom clearance ----

  describe('custom clearance', () => {
    it('shows clearance input when enabled', () => {
      renderForm({ enabled: true });
      expect(screen.getByTestId('clearance-input')).toBeInTheDocument();
    });

    it('calls onCustomClearanceChange with null when cleared', () => {
      const onCustomClearanceChange = vi.fn();
      renderForm({ enabled: true, customClearanceMm: 0.5, onCustomClearanceChange });
      const input = screen.getByTestId('clearance-input');
      fireEvent.change(input, { target: { value: '' } });
      expect(onCustomClearanceChange).toHaveBeenCalledWith(null);
    });

    it('calls onCustomClearanceChange with clamped value', () => {
      const onCustomClearanceChange = vi.fn();
      renderForm({ enabled: true, onCustomClearanceChange });
      const input = screen.getByTestId('clearance-input');
      fireEvent.change(input, { target: { value: '5.0' } });
      expect(onCustomClearanceChange).toHaveBeenCalledWith(2.0);
    });

    it('calls onCustomClearanceChange with lower-bound clamped value', () => {
      const onCustomClearanceChange = vi.fn();
      renderForm({ enabled: true, onCustomClearanceChange });
      const input = screen.getByTestId('clearance-input');
      fireEvent.change(input, { target: { value: '0.01' } });
      expect(onCustomClearanceChange).toHaveBeenCalledWith(0.05);
    });
  });

  // ---- Recommendation panel ----

  describe('recommendation panel', () => {
    it('does not show recommendation when family/size are null', () => {
      renderForm({ enabled: true, family: null, size: null });
      expect(screen.queryByTestId('print-recommendation')).not.toBeInTheDocument();
    });

    it('shows loading skeleton while recommendation is loading', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      const panel = screen.getByTestId('print-recommendation');
      expect(panel).toBeInTheDocument();
      // Skeletons render as divs with animate-pulse
      const skeletons = panel.querySelectorAll('.animate-pulse');
      expect(skeletons.length).toBeGreaterThanOrEqual(1);
    });

    it('shows error message when recommendation fetch fails', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Network error'),
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      expect(
        screen.getByText('Failed to load print recommendation.'),
      ).toBeInTheDocument();
    });

    it('displays feasibility badge from recommendation', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: mockRecommendation,
        isLoading: false,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      expect(screen.getByText('Good')).toBeInTheDocument();
    });

    it('displays excellent feasibility with green styling', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: { ...mockRecommendation, feasibility: 'excellent' as const },
        isLoading: false,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      const badge = screen.getByText('Excellent');
      expect(badge.className).toContain('green');
    });

    it('displays not_recommended feasibility with red styling', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: { ...mockRecommendation, feasibility: 'not_recommended' as const },
        isLoading: false,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      const badge = screen.getByText('Not Recommended');
      expect(badge.className).toContain('red');
    });

    it('displays clearance recommendation', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: mockRecommendation,
        isLoading: false,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      expect(screen.getByText('0.30 mm')).toBeInTheDocument();
    });

    it('displays orientation advice', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: mockRecommendation,
        isLoading: false,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      expect(
        screen.getByText('Print vertically with thread axis aligned to Z'),
      ).toBeInTheDocument();
    });

    it('displays notes list', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: mockRecommendation,
        isLoading: false,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      expect(screen.getByText('Use supports for overhangs')).toBeInTheDocument();
      expect(screen.getByText('Orient vertically for best results')).toBeInTheDocument();
    });

    it('displays estimated strength percentage', () => {
      mockUsePrintRecommendation.mockReturnValue({
        data: mockRecommendation,
        isLoading: false,
        error: null,
      });
      renderForm({ enabled: true, family: 'iso_metric', size: 'M8' });
      expect(screen.getByText('~75% strength')).toBeInTheDocument();
    });

    it('does not fetch recommendation when disabled even with family/size', () => {
      renderForm({ enabled: false, family: 'iso_metric', size: 'M8' });
      // The hook should be called with null family/size
      expect(mockUsePrintRecommendation).toHaveBeenCalledWith(null, null, 'fdm');
    });
  });

  // ---- Ignores invalid input ----

  describe('invalid input handling', () => {
    it('ignores NaN nozzle input', () => {
      const onNozzleDiameterChange = vi.fn();
      renderForm({ enabled: true, process: 'fdm', onNozzleDiameterChange });
      fireEvent.change(screen.getByTestId('nozzle-input'), {
        target: { value: 'abc' },
      });
      expect(onNozzleDiameterChange).not.toHaveBeenCalled();
    });

    it('ignores NaN layer height input', () => {
      const onLayerHeightChange = vi.fn();
      renderForm({ enabled: true, process: 'fdm', onLayerHeightChange });
      fireEvent.change(screen.getByTestId('layer-height-input'), {
        target: { value: 'xyz' },
      });
      expect(onLayerHeightChange).not.toHaveBeenCalled();
    });

    it('ignores NaN clearance input (non-empty)', () => {
      const onCustomClearanceChange = vi.fn();
      renderForm({ enabled: true, onCustomClearanceChange });
      fireEvent.change(screen.getByTestId('clearance-input'), {
        target: { value: 'bad' },
      });
      expect(onCustomClearanceChange).not.toHaveBeenCalled();
    });
  });
});
