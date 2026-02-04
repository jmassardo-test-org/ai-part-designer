import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { describe, it, expect } from 'vitest';
import { Label } from './label';

describe('Label', () => {
  it('renders without crashing', () => {
    render(<Label>Username</Label>);
    expect(screen.getByText('Username')).toBeInTheDocument();
  });

  it('renders children', () => {
    render(<Label>Email Address</Label>);
    expect(screen.getByText('Email Address')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Label className="custom-label">Test</Label>);
    expect(screen.getByText('Test')).toHaveClass('custom-label');
  });

  it('applies default label styles', () => {
    render(<Label>Label Text</Label>);
    expect(screen.getByText('Label Text')).toHaveClass('text-sm');
    expect(screen.getByText('Label Text')).toHaveClass('font-medium');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLLabelElement>();
    render(<Label ref={ref}>Test</Label>);
    expect(ref.current).toBeInstanceOf(HTMLLabelElement);
  });

  it('associates with input via htmlFor', () => {
    render(
      <>
        <Label htmlFor="test-input">Test Label</Label>
        <input id="test-input" />
      </>
    );
    const label = screen.getByText('Test Label');
    expect(label).toHaveAttribute('for', 'test-input');
  });
});
