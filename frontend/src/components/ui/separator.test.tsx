import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { describe, it, expect } from 'vitest';
import { Separator } from './separator';

describe('Separator', () => {
  it('renders without crashing', () => {
    render(<Separator data-testid="separator" />);
    expect(screen.getByTestId('separator')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Separator className="custom-separator" data-testid="separator" />);
    expect(screen.getByTestId('separator')).toHaveClass('custom-separator');
  });

  it('renders as horizontal by default', () => {
    render(<Separator data-testid="separator" />);
    expect(screen.getByTestId('separator')).toHaveClass('h-[1px]');
    expect(screen.getByTestId('separator')).toHaveClass('w-full');
  });

  it('applies vertical orientation styles', () => {
    render(<Separator orientation="vertical" data-testid="separator" />);
    expect(screen.getByTestId('separator')).toHaveClass('h-full');
    expect(screen.getByTestId('separator')).toHaveClass('w-[1px]');
  });

  it('is decorative by default', () => {
    render(<Separator data-testid="separator" />);
    expect(screen.getByTestId('separator')).toHaveAttribute('data-orientation', 'horizontal');
  });

  it('applies base styles', () => {
    render(<Separator data-testid="separator" />);
    expect(screen.getByTestId('separator')).toHaveClass('shrink-0');
    expect(screen.getByTestId('separator')).toHaveClass('bg-border');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLDivElement>();
    render(<Separator ref={ref} />);
    expect(ref.current).not.toBeNull();
  });
});
