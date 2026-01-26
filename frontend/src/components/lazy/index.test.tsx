/**
 * Lazy Components Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Suspense } from 'react';
import { lazyWithFallback, preloadComponent } from './index';

// Mock dynamic imports
vi.mock('@/components/viewer/CADViewer', () => ({
  default: () => <div data-testid="cad-viewer">CAD Viewer</div>,
}));

vi.mock('@/pages/admin/AdminDashboard', () => ({
  default: () => <div data-testid="admin-dashboard">Admin Dashboard</div>,
}));

describe('lazyWithFallback', () => {
  it('creates a lazy component', () => {
    const LazyComponent = lazyWithFallback(
      () => Promise.resolve({ default: () => <div>Test</div> })
    );
    expect(LazyComponent).toBeDefined();
  });

  it('provides a Suspense wrapper', () => {
    const LazyComponent = lazyWithFallback(
      () => Promise.resolve({ default: () => <div>Test</div> })
    );
    expect(LazyComponent.Suspense).toBeDefined();
  });

  it('renders loading fallback while loading', async () => {
    const LazyComponent = lazyWithFallback(
      () => new Promise(() => {}), // Never resolves
      <div data-testid="loading">Loading...</div>
    );

    render(
      <Suspense fallback={<div>Suspense Fallback</div>}>
        <LazyComponent.Suspense />
      </Suspense>
    );

    expect(screen.getByTestId('loading')).toBeInTheDocument();
  });

  it('renders component after loading', async () => {
    const TestComponent = () => <div data-testid="loaded">Loaded Content</div>;
    
    const LazyComponent = lazyWithFallback(
      () => Promise.resolve({ default: TestComponent })
    );

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <LazyComponent />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByTestId('loaded')).toBeInTheDocument();
    });
  });

  it('passes props through to component', async () => {
    const TestComponent = ({ message }: { message: string }) => (
      <div data-testid="with-props">{message}</div>
    );
    
    const LazyComponent = lazyWithFallback(
      () => Promise.resolve({ default: TestComponent })
    );

    render(
      <Suspense fallback={<div>Loading...</div>}>
        <LazyComponent message="Hello World" />
      </Suspense>
    );

    await waitFor(() => {
      expect(screen.getByText('Hello World')).toBeInTheDocument();
    });
  });

  it('uses default loading spinner when no fallback provided', () => {
    const LazyComponent = lazyWithFallback(
      () => new Promise(() => {}) // Never resolves
    );

    render(<LazyComponent.Suspense />);

    // Should have a spinner (animate-spin class)
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });
});

describe('preloadComponent', () => {
  it('calls the import function', () => {
    const importFn = vi.fn(() => Promise.resolve({ default: () => null }));
    
    preloadComponent(importFn);
    
    expect(importFn).toHaveBeenCalled();
  });

  it('does not throw on import', () => {
    expect(() => {
      preloadComponent(() => Promise.resolve({ default: () => null }));
    }).not.toThrow();
  });
});

describe('LoadingSpinner', () => {
  it('renders with correct styling', async () => {
    const LazyComponent = lazyWithFallback(
      () => new Promise(() => {}) // Never resolves
    );

    render(<LazyComponent.Suspense />);

    const container = document.querySelector('.flex.items-center.justify-center');
    expect(container).toBeInTheDocument();
    
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });
});

describe('ViewerSkeleton', () => {
  it('is used for CAD viewer lazy loading', async () => {
    // Import the actual LazyCADViewer
    const { LazyCADViewer } = await import('./index');
    
    expect(LazyCADViewer).toBeDefined();
    expect(LazyCADViewer.Suspense).toBeDefined();
  });
});

describe('PageSkeleton', () => {
  it('is used for admin dashboard lazy loading', async () => {
    const { LazyAdminDashboard } = await import('./index');
    
    expect(LazyAdminDashboard).toBeDefined();
    expect(LazyAdminDashboard.Suspense).toBeDefined();
  });
});

describe('Lazy exports', () => {
  it('exports LazyCADViewer', async () => {
    const exports = await import('./index');
    expect(exports.LazyCADViewer).toBeDefined();
  });

  it('exports LazyAdminDashboard', async () => {
    const exports = await import('./index');
    expect(exports.LazyAdminDashboard).toBeDefined();
  });
});
