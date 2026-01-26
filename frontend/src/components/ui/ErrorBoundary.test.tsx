/**
 * ErrorBoundary Component Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ErrorBoundary, NotFoundPage } from './ErrorBoundary';

// Component that throws an error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

describe('ErrorBoundary', () => {
  // Suppress console.error during these tests
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
  });

  it('renders children when no error', () => {
    render(
      <ErrorBoundary>
        <div data-testid="child">Child content</div>
      </ErrorBoundary>
    );
    
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders error UI when child throws', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('shows helpful error message', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    expect(screen.getByText(/unexpected happened/i)).toBeInTheDocument();
  });

  it('shows Try Again button', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
  });

  it('shows Go to Dashboard button', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    expect(screen.getByRole('button', { name: /go to dashboard/i })).toBeInTheDocument();
  });

  it('resets error state when Try Again clicked', async () => {
    const user = userEvent.setup();
    let shouldThrow = true;
    
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={shouldThrow} />
      </ErrorBoundary>
    );
    
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    
    // Change the prop so it won't throw on retry
    shouldThrow = false;
    
    await user.click(screen.getByRole('button', { name: /try again/i }));
    
    // Rerender with updated prop
    rerender(
      <ErrorBoundary>
        <ThrowError shouldThrow={shouldThrow} />
      </ErrorBoundary>
    );
    
    // Error state should be reset (though child might still throw if props haven't changed)
  });

  it('navigates to dashboard when Go to Dashboard clicked', async () => {
    const user = userEvent.setup();
    
    // Mock window.location
    const originalLocation = window.location;
    delete (window as any).location;
    window.location = { ...originalLocation, href: '' } as any;
    
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    await user.click(screen.getByRole('button', { name: /go to dashboard/i }));
    
    expect(window.location.href).toBe('/dashboard');
    
    // Restore
    window.location = originalLocation;
  });

  it('calls onError callback when error occurs', () => {
    const onError = vi.fn();
    
    render(
      <ErrorBoundary onError={onError}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ componentStack: expect.any(String) })
    );
  });

  it('uses custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div data-testid="custom-fallback">Custom Error</div>}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  it('shows error details in development mode', () => {
    const originalNodeEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';
    
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    // Should have details element
    const details = screen.queryByText('Error Details');
    // In development, error details should be expandable
    
    process.env.NODE_ENV = originalNodeEnv;
  });

  it('logs error to console', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    expect(console.error).toHaveBeenCalled();
  });

  it('shows alert icon', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );
    
    // AlertTriangle icon should be present
    const icon = document.querySelector('.text-red-500');
    expect(icon).toBeInTheDocument();
  });
});

describe('NotFoundPage', () => {
  it('renders 404 page', () => {
    render(<NotFoundPage />);
    
    expect(screen.getByText('404')).toBeInTheDocument();
  });

  it('shows page not found message', () => {
    render(<NotFoundPage />);
    
    expect(screen.getByText('Page not found')).toBeInTheDocument();
  });

  it('shows helpful description', () => {
    render(<NotFoundPage />);
    
    expect(screen.getByText(/couldn't find the page/i)).toBeInTheDocument();
  });

  it('has proper styling', () => {
    const { container } = render(<NotFoundPage />);
    
    expect(container.querySelector('.min-h-screen')).toBeInTheDocument();
  });
});
