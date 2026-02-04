import { render, screen } from '@testing-library/react';
import { createRef } from 'react';
import { describe, it, expect } from 'vitest';
import { ScrollArea, ScrollBar } from './scroll-area';

describe('ScrollArea', () => {
  it('renders without crashing', () => {
    render(<ScrollArea data-testid="scroll-area">Content</ScrollArea>);
    expect(screen.getByTestId('scroll-area')).toBeInTheDocument();
  });

  it('renders children', () => {
    render(<ScrollArea>Scrollable content</ScrollArea>);
    expect(screen.getByText('Scrollable content')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<ScrollArea className="custom-scroll" data-testid="scroll-area">Content</ScrollArea>);
    expect(screen.getByTestId('scroll-area')).toHaveClass('custom-scroll');
  });

  it('applies vertical orientation styles', () => {
    render(
      <ScrollArea orientation="vertical" data-testid="scroll-area">
        Content
      </ScrollArea>
    );
    expect(screen.getByTestId('scroll-area')).toHaveClass('overflow-x-hidden');
  });

  it('applies horizontal orientation styles', () => {
    render(
      <ScrollArea orientation="horizontal" data-testid="scroll-area">
        Content
      </ScrollArea>
    );
    expect(screen.getByTestId('scroll-area')).toHaveClass('overflow-y-hidden');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLDivElement>();
    render(<ScrollArea ref={ref}>Content</ScrollArea>);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });
});

describe('ScrollBar', () => {
  it('renders without crashing', () => {
    render(<ScrollBar data-testid="scroll-bar" />);
    expect(screen.getByTestId('scroll-bar')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<ScrollBar className="custom-scrollbar" data-testid="scroll-bar" />);
    expect(screen.getByTestId('scroll-bar')).toHaveClass('custom-scrollbar');
  });

  it('applies vertical orientation styles', () => {
    render(<ScrollBar orientation="vertical" data-testid="scroll-bar" />);
    expect(screen.getByTestId('scroll-bar')).toHaveClass('h-full');
    expect(screen.getByTestId('scroll-bar')).toHaveClass('w-2.5');
  });

  it('applies horizontal orientation styles', () => {
    render(<ScrollBar orientation="horizontal" data-testid="scroll-bar" />);
    expect(screen.getByTestId('scroll-bar')).toHaveClass('h-2.5');
    expect(screen.getByTestId('scroll-bar')).toHaveClass('flex-col');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLDivElement>();
    render(<ScrollBar ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLDivElement);
  });
});
