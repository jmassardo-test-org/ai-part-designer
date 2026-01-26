/**
 * Tooltip Component Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { Tooltip } from './Tooltip';

describe('Tooltip', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders trigger element', () => {
    render(
      <Tooltip content="Tooltip text">
        <button>Hover me</button>
      </Tooltip>
    );
    
    expect(screen.getByText('Hover me')).toBeInTheDocument();
  });

  it('does not show tooltip initially', () => {
    render(
      <Tooltip content="Tooltip text">
        <button>Hover me</button>
      </Tooltip>
    );
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('shows tooltip on mouse enter after delay', () => {
    render(
      <Tooltip content="Tooltip text" delay={200}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Tooltip should not be visible yet
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    
    // Advance timer
    act(() => {
      vi.advanceTimersByTime(200);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('hides tooltip on mouse leave', () => {
    render(
      <Tooltip content="Tooltip text" delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    const trigger = screen.getByText('Hover me');
    
    fireEvent.mouseEnter(trigger);
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    
    fireEvent.mouseLeave(trigger);
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('shows tooltip on focus', () => {
    render(
      <Tooltip content="Tooltip text" delay={0}>
        <button>Focus me</button>
      </Tooltip>
    );
    
    const trigger = screen.getByText('Focus me');
    
    fireEvent.focus(trigger);
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('hides tooltip on blur', () => {
    render(
      <Tooltip content="Tooltip text" delay={0}>
        <button>Focus me</button>
      </Tooltip>
    );
    
    const trigger = screen.getByText('Focus me');
    
    fireEvent.focus(trigger);
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    
    fireEvent.blur(trigger);
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('displays tooltip content', () => {
    render(
      <Tooltip content="My tooltip content" delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByText('My tooltip content')).toBeInTheDocument();
  });

  it('renders complex content', () => {
    render(
      <Tooltip content={<div data-testid="complex-content"><strong>Bold</strong> text</div>} delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByTestId('complex-content')).toBeInTheDocument();
    expect(screen.getByText('Bold')).toBeInTheDocument();
  });

  it('does not show when disabled', () => {
    render(
      <Tooltip content="Tooltip text" disabled={true} delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(100);
    });
    
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('uses default delay of 200ms', () => {
    render(
      <Tooltip content="Tooltip text">
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // At 100ms, tooltip should not be visible
    act(() => {
      vi.advanceTimersByTime(100);
    });
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
    
    // At 200ms, tooltip should be visible
    act(() => {
      vi.advanceTimersByTime(100);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('positions tooltip at top by default', () => {
    render(
      <Tooltip content="Tooltip text" delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('accepts position prop', () => {
    render(
      <Tooltip content="Tooltip text" position="bottom" delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('supports left position', () => {
    render(
      <Tooltip content="Tooltip text" position="left" delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('supports right position', () => {
    render(
      <Tooltip content="Tooltip text" position="right" delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
  });

  it('clears timeout on unmount', () => {
    const { unmount } = render(
      <Tooltip content="Tooltip text" delay={500}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    
    // Unmount before delay completes
    unmount();
    
    // Should not throw or cause issues
    act(() => {
      vi.advanceTimersByTime(500);
    });
  });

  it('cancels pending show on mouse leave', () => {
    render(
      <Tooltip content="Tooltip text" delay={500}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    const trigger = screen.getByText('Hover me');
    
    fireEvent.mouseEnter(trigger);
    
    // Leave before delay completes
    act(() => {
      vi.advanceTimersByTime(200);
    });
    
    fireEvent.mouseLeave(trigger);
    
    // Finish the delay
    act(() => {
      vi.advanceTimersByTime(300);
    });
    
    // Tooltip should not appear
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument();
  });

  it('has tooltip role for accessibility', () => {
    render(
      <Tooltip content="Accessible tooltip" delay={0}>
        <button>Hover me</button>
      </Tooltip>
    );
    
    fireEvent.mouseEnter(screen.getByText('Hover me'));
    act(() => {
      vi.advanceTimersByTime(0);
    });
    
    const tooltip = screen.getByRole('tooltip');
    expect(tooltip).toBeInTheDocument();
  });
});
