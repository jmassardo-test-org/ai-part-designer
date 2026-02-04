/**
 * Logo Component Tests
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Logo, LogoIcon } from './Logo';

describe('Logo', () => {
  it('renders with default props', () => {
    render(<Logo />);
    expect(screen.getByText('Assemblematic')).toBeInTheDocument();
    expect(screen.getByText('AI')).toBeInTheDocument();
  });

  it('renders icon only when showText is false', () => {
    render(<Logo showText={false} />);
    expect(screen.queryByText('Assemblematic')).not.toBeInTheDocument();
  });

  it('renders icon only with variant="icon"', () => {
    render(<Logo variant="icon" />);
    expect(screen.queryByText('Assemblematic')).not.toBeInTheDocument();
  });

  it('renders with full variant', () => {
    render(<Logo variant="full" />);
    expect(screen.getByText('Assemblematic')).toBeInTheDocument();
    expect(screen.getByText('AI')).toBeInTheDocument();
  });

  it('applies different sizes', () => {
    const { rerender, container } = render(<Logo size="sm" />);
    let svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '24');

    rerender(<Logo size="md" />);
    svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '32');

    rerender(<Logo size="lg" />);
    svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '40');

    rerender(<Logo size="xl" />);
    svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '48');
  });

  it('applies custom className', () => {
    const { container } = render(<Logo className="custom-class" />);
    expect(container.querySelector('.custom-class')).toBeInTheDocument();
  });

  it('renders text with correct colors', () => {
    render(<Logo />);
    const assemblematicText = screen.getByText('Assemblematic');
    const aiText = screen.getByText('AI');
    
    expect(assemblematicText).toHaveClass('text-white');
    expect(aiText).toHaveClass('text-brand-cyan');
  });

  it('applies correct text size based on size prop', () => {
    const { container, rerender } = render(<Logo size="sm" />);
    let textContainer = container.querySelector('span.font-bold');
    expect(textContainer).toHaveClass('text-lg');

    rerender(<Logo size="md" />);
    textContainer = container.querySelector('span.font-bold');
    expect(textContainer).toHaveClass('text-xl');

    rerender(<Logo size="lg" />);
    textContainer = container.querySelector('span.font-bold');
    expect(textContainer).toHaveClass('text-2xl');

    rerender(<Logo size="xl" />);
    textContainer = container.querySelector('span.font-bold');
    expect(textContainer).toHaveClass('text-3xl');
  });
});

describe('LogoIcon', () => {
  it('renders with default size', () => {
    const { container } = render(<LogoIcon />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '32');
    expect(svg).toHaveAttribute('height', '32');
  });

  it('renders with custom size', () => {
    const { container } = render(<LogoIcon size={64} />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('width', '64');
    expect(svg).toHaveAttribute('height', '64');
  });

  it('applies custom className', () => {
    const { container } = render(<LogoIcon className="my-custom-class" />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveClass('my-custom-class');
  });

  it('renders SVG with correct viewBox', () => {
    const { container } = render(<LogoIcon />);
    const svg = container.querySelector('svg');
    expect(svg).toHaveAttribute('viewBox', '0 0 64 64');
  });

  it('contains gear and block elements', () => {
    const { container } = render(<LogoIcon />);
    const paths = container.querySelectorAll('path');
    expect(paths.length).toBeGreaterThan(0);
  });
});
