import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { Alert, AlertTitle, AlertDescription } from './alert';

describe('Alert', () => {
  it('renders without crashing', () => {
    render(<Alert>Alert content</Alert>);
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('renders children', () => {
    render(<Alert>Important message</Alert>);
    expect(screen.getByText('Important message')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Alert className="custom-alert">Test</Alert>);
    expect(screen.getByRole('alert')).toHaveClass('custom-alert');
  });

  it('applies default variant styles', () => {
    render(<Alert>Default alert</Alert>);
    expect(screen.getByRole('alert')).toHaveClass('bg-background');
  });

  it('applies destructive variant styles', () => {
    render(<Alert variant="destructive">Error alert</Alert>);
    expect(screen.getByRole('alert')).toHaveClass('text-destructive');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLDivElement>();
    render(<Alert ref={ref}>Test</Alert>);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });
});

describe('AlertTitle', () => {
  it('renders without crashing', () => {
    render(<AlertTitle>Title</AlertTitle>);
    expect(screen.getByText('Title')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<AlertTitle className="custom-title">Title</AlertTitle>);
    expect(screen.getByText('Title')).toHaveClass('custom-title');
  });

  it('applies default styles', () => {
    render(<AlertTitle>Title</AlertTitle>);
    expect(screen.getByText('Title')).toHaveClass('font-medium');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLParagraphElement>();
    render(<AlertTitle ref={ref}>Title</AlertTitle>);
    expect(ref.current).toBeInstanceOf(HTMLHeadingElement);
  });
});

describe('AlertDescription', () => {
  it('renders without crashing', () => {
    render(<AlertDescription>Description</AlertDescription>);
    expect(screen.getByText('Description')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<AlertDescription className="custom-desc">Description</AlertDescription>);
    expect(screen.getByText('Description')).toHaveClass('custom-desc');
  });

  it('applies default styles', () => {
    render(<AlertDescription>Description</AlertDescription>);
    expect(screen.getByText('Description')).toHaveClass('text-sm');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLParagraphElement>();
    render(<AlertDescription ref={ref}>Description</AlertDescription>);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });
});
