import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Skeleton } from './skeleton';

describe('Skeleton', () => {
  it('renders without crashing', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Skeleton className="custom-skeleton" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('custom-skeleton');
  });

  it('applies animate-pulse class', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('animate-pulse');
  });

  it('applies rounded-md class', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('rounded-md');
  });

  it('applies bg-muted class', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('bg-muted');
  });

  it('passes through additional props', () => {
    render(<Skeleton data-testid="skeleton" style={{ width: '100px', height: '20px' }} />);
    const skeleton = screen.getByTestId('skeleton');
    expect(skeleton).toHaveStyle({ width: '100px', height: '20px' });
  });

  it('can render with custom dimensions via className', () => {
    render(<Skeleton className="w-full h-12" data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton')).toHaveClass('w-full');
    expect(screen.getByTestId('skeleton')).toHaveClass('h-12');
  });

  it('renders as a div element', () => {
    render(<Skeleton data-testid="skeleton" />);
    expect(screen.getByTestId('skeleton').tagName).toBe('DIV');
  });
});
