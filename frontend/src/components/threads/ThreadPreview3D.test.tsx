/**
 * Tests for the ThreadPreview3D component.
 *
 * R3F Canvas and drei helpers are mocked so the tests run in jsdom
 * without a real WebGL context.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { ThreadSpec } from '@/types/threads';
import { ThreadPreview3D, type ThreadPreview3DProps } from './ThreadPreview3D';

// ---------------------------------------------------------------------------
// Mocks — R3F, drei, and WebGL utility
// ---------------------------------------------------------------------------

const mockIsWebGLAvailable = vi.fn(() => true);

vi.mock('@/utils/webgl', () => ({
  isWebGLAvailable: () => mockIsWebGLAvailable(),
}));

vi.mock('@react-three/fiber', () => ({
  Canvas: ({ children, ...props }: React.PropsWithChildren<Record<string, unknown>>) => (
    <div data-testid={props['data-testid'] as string ?? 'canvas-mock'}>{children}</div>
  ),
}));

vi.mock('@react-three/drei', () => ({
  OrbitControls: () => null,
  Center: ({ children }: React.PropsWithChildren) => <>{children}</>,
  Grid: () => null,
  Html: ({ children }: React.PropsWithChildren) => <div>{children}</div>,
}));

vi.mock('three', async () => {
  const actual = await vi.importActual<typeof import('three')>('three');
  return {
    ...actual,
    Shape: actual.Shape,
    DoubleSide: actual.DoubleSide,
  };
});

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const baseSpec: ThreadSpec = {
  family: 'iso_metric',
  size: 'M10',
  pitch_mm: 1.5,
  form: 'triangular',
  pitch_series: 'coarse',
  major_diameter: 10,
  pitch_diameter_ext: 9.026,
  minor_diameter_ext: 8.376,
  major_diameter_int: 10,
  pitch_diameter_int: 9.026,
  minor_diameter_int: 8.376,
  profile_angle_deg: 60,
  taper_per_mm: 0,
  tap_drill_mm: 8.5,
  clearance_hole_close_mm: 10.5,
  clearance_hole_medium_mm: 11,
  clearance_hole_free_mm: 12,
  tpi: null,
  nominal_size_inch: null,
  engagement_length_mm: 15,
  standard_ref: 'ISO 261',
  notes: '',
};

function renderComponent(overrides: Partial<ThreadPreview3DProps> = {}) {
  const props: ThreadPreview3DProps = {
    spec: baseSpec,
    threadType: 'external',
    lengthMm: 20,
    ...overrides,
  };
  return render(<ThreadPreview3D {...props} />);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ThreadPreview3D', () => {
  beforeEach(() => {
    mockIsWebGLAvailable.mockReturnValue(true);
  });

  // -- Placeholder state ---------------------------------------------------

  it('renders placeholder when spec is null', () => {
    renderComponent({ spec: null });

    expect(screen.getByTestId('thread-preview-3d')).toBeInTheDocument();
    expect(screen.getByTestId('thread-preview-placeholder')).toBeInTheDocument();
    expect(screen.getByText('Select a thread to preview')).toBeInTheDocument();
  });

  it('does not render canvas when spec is null', () => {
    renderComponent({ spec: null });

    expect(screen.queryByTestId('thread-preview-canvas')).not.toBeInTheDocument();
  });

  // -- WebGL fallback ------------------------------------------------------

  it('renders fallback when WebGL is unavailable', () => {
    mockIsWebGLAvailable.mockReturnValue(false);

    renderComponent();

    expect(screen.getByTestId('thread-preview-no-webgl')).toBeInTheDocument();
    expect(screen.getByText(/WebGL/i)).toBeInTheDocument();
  });

  // -- Canvas rendering with spec ------------------------------------------

  it('renders canvas when spec is provided', () => {
    renderComponent();

    expect(screen.getByTestId('thread-preview-3d')).toBeInTheDocument();
    expect(screen.getByTestId('thread-preview-canvas')).toBeInTheDocument();
  });

  it('displays info badge with family, size, and thread type', () => {
    renderComponent({ threadType: 'external' });

    expect(screen.getByText('ISO_METRIC')).toBeInTheDocument();
    expect(screen.getByText('M10')).toBeInTheDocument();
    expect(screen.getByText('external')).toBeInTheDocument();
  });

  it('renders internal thread variant', () => {
    renderComponent({ threadType: 'internal' });

    expect(screen.getByText('internal')).toBeInTheDocument();
  });

  // -- Dimension annotations -----------------------------------------------

  it('shows major diameter annotation', () => {
    renderComponent();

    expect(screen.getByText(/⌀ Major/)).toBeInTheDocument();
    expect(screen.getByText(/10\.00 mm/)).toBeInTheDocument();
  });

  it('shows length annotation', () => {
    renderComponent({ lengthMm: 25 });

    expect(screen.getByText(/25\.0 mm/)).toBeInTheDocument();
  });

  it('shows pitch annotation', () => {
    renderComponent();

    expect(screen.getByText(/1\.50 mm/)).toBeInTheDocument();
  });

  // -- CSS class forwarding -----------------------------------------------

  it('applies className to the container', () => {
    renderComponent({ className: 'h-64 w-full' });

    const container = screen.getByTestId('thread-preview-3d');
    expect(container.className).toContain('h-64');
    expect(container.className).toContain('w-full');
  });

  it('applies className to the placeholder container', () => {
    renderComponent({ spec: null, className: 'h-48' });

    const container = screen.getByTestId('thread-preview-3d');
    expect(container.className).toContain('h-48');
  });
});
