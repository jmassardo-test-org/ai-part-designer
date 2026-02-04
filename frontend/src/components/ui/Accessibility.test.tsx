/**
 * Accessibility Component Tests
 */

import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SkipLink, FocusTrap, Announce, VisuallyHidden } from './Accessibility';

describe('SkipLink', () => {
  it('renders skip link', () => {
    render(<SkipLink />);
    expect(screen.getByText('Skip to main content')).toBeInTheDocument();
  });

  it('has correct href', () => {
    render(<SkipLink />);
    const link = screen.getByText('Skip to main content');
    expect(link).toHaveAttribute('href', '#main-content');
  });

  it('is visually hidden by default (sr-only)', () => {
    render(<SkipLink />);
    const link = screen.getByText('Skip to main content');
    expect(link).toHaveClass('sr-only');
  });

  it('becomes visible on focus', () => {
    render(<SkipLink />);
    const link = screen.getByText('Skip to main content');
    expect(link).toHaveClass('focus:not-sr-only');
  });

  it('has high z-index when focused', () => {
    render(<SkipLink />);
    const link = screen.getByText('Skip to main content');
    expect(link).toHaveClass('focus:z-[9999]');
  });

  it('has proper focus styling', () => {
    render(<SkipLink />);
    const link = screen.getByText('Skip to main content');
    expect(link).toHaveClass('focus:outline-none');
    expect(link).toHaveClass('focus:ring-2');
  });
});

describe('FocusTrap', () => {
  it('renders children', () => {
    render(
      <FocusTrap>
        <div data-testid="child">Content</div>
      </FocusTrap>
    );
    
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('focuses first focusable element on mount', () => {
    render(
      <FocusTrap>
        <button data-testid="first">First</button>
        <button data-testid="second">Second</button>
      </FocusTrap>
    );
    
    expect(screen.getByTestId('first')).toHaveFocus();
  });

  it('does not trap focus when inactive', () => {
    render(
      <FocusTrap active={false}>
        <button data-testid="button">Button</button>
      </FocusTrap>
    );
    
    expect(screen.getByTestId('button')).not.toHaveFocus();
  });

  it('traps Tab key to cycle through elements', async () => {
    const user = userEvent.setup();
    
    render(
      <FocusTrap>
        <button data-testid="first">First</button>
        <button data-testid="second">Second</button>
        <button data-testid="third">Third</button>
      </FocusTrap>
    );
    
    expect(screen.getByTestId('first')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByTestId('second')).toHaveFocus();
    
    await user.tab();
    expect(screen.getByTestId('third')).toHaveFocus();
    
    // Tab from last should go to first
    await user.tab();
    expect(screen.getByTestId('first')).toHaveFocus();
  });

  it('traps Shift+Tab to cycle backwards', async () => {
    const user = userEvent.setup();
    
    render(
      <FocusTrap>
        <button data-testid="first">First</button>
        <button data-testid="second">Second</button>
        <button data-testid="third">Third</button>
      </FocusTrap>
    );
    
    // First element is focused
    expect(screen.getByTestId('first')).toHaveFocus();
    
    // Shift+Tab from first should go to last
    await user.tab({ shift: true });
    expect(screen.getByTestId('third')).toHaveFocus();
  });

  it('handles container with no focusable elements', () => {
    render(
      <FocusTrap>
        <div>No focusable elements</div>
      </FocusTrap>
    );
    
    // Should not throw
    expect(screen.getByText('No focusable elements')).toBeInTheDocument();
  });

  it('includes inputs, links, and buttons as focusable', () => {
    render(
      <FocusTrap>
        <button data-testid="button">Button</button>
        <a href="#" data-testid="link">Link</a>
        <input data-testid="input" />
      </FocusTrap>
    );
    
    expect(screen.getByTestId('button')).toHaveFocus();
  });

  it('excludes elements with tabindex=-1', () => {
    render(
      <FocusTrap>
        <button data-testid="first">First</button>
        <button tabIndex={-1} data-testid="excluded">Excluded</button>
        <button data-testid="second">Second</button>
      </FocusTrap>
    );
    
    expect(screen.getByTestId('first')).toHaveFocus();
  });
});

describe('Announce', () => {
  it('renders with polite aria-live by default', () => {
    render(<Announce message="Hello" />);
    
    const announcer = screen.getByRole('status');
    expect(announcer).toHaveAttribute('aria-live', 'polite');
  });

  it('renders with assertive aria-live when specified', () => {
    render(<Announce message="Important!" assertive={true} />);
    
    const announcer = screen.getByRole('status');
    expect(announcer).toHaveAttribute('aria-live', 'assertive');
  });

  it('displays the message', () => {
    render(<Announce message="Test message" />);
    
    expect(screen.getByText('Test message')).toBeInTheDocument();
  });

  it('is visually hidden', () => {
    render(<Announce message="Hidden message" />);
    
    const announcer = screen.getByRole('status');
    expect(announcer).toHaveClass('sr-only');
  });

  it('has aria-atomic true', () => {
    render(<Announce message="Atomic message" />);
    
    const announcer = screen.getByRole('status');
    expect(announcer).toHaveAttribute('aria-atomic', 'true');
  });
});

describe('VisuallyHidden', () => {
  it('renders children', () => {
    render(<VisuallyHidden>Hidden text</VisuallyHidden>);
    
    expect(screen.getByText('Hidden text')).toBeInTheDocument();
  });

  it('is visually hidden (sr-only)', () => {
    render(<VisuallyHidden>Hidden content</VisuallyHidden>);
    
    const element = screen.getByText('Hidden content');
    expect(element).toHaveClass('sr-only');
  });

  it('wraps content in span', () => {
    render(<VisuallyHidden>Content</VisuallyHidden>);
    
    const element = screen.getByText('Content');
    expect(element.tagName).toBe('SPAN');
  });

  it('renders complex children', () => {
    render(
      <VisuallyHidden>
        <span data-testid="inner">Inner content</span>
      </VisuallyHidden>
    );
    
    expect(screen.getByTestId('inner')).toBeInTheDocument();
  });
});
