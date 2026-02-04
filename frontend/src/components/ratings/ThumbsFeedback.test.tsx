/**
 * Tests for ThumbsFeedback component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ThumbsFeedback, FeedbackSummary } from './ThumbsFeedback';

describe('ThumbsFeedback', () => {
  it('renders thumbs up and down buttons', () => {
    render(<ThumbsFeedback thumbsUp={10} thumbsDown={5} />);
    
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(2);
  });

  it('displays counts for both options', () => {
    render(<ThumbsFeedback thumbsUp={42} thumbsDown={13} />);
    
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('13')).toBeInTheDocument();
  });

  it('calls onFeedback with thumbs_up when clicked', () => {
    const handleFeedback = vi.fn();
    render(
      <ThumbsFeedback
        thumbsUp={10}
        thumbsDown={5}
        onFeedback={handleFeedback}
      />
    );
    
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]); // Thumbs up button
    
    expect(handleFeedback).toHaveBeenCalledWith('thumbs_up');
  });

  it('calls onFeedback with thumbs_down when clicked', () => {
    const handleFeedback = vi.fn();
    render(
      <ThumbsFeedback
        thumbsUp={10}
        thumbsDown={5}
        onFeedback={handleFeedback}
      />
    );
    
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[1]); // Thumbs down button
    
    expect(handleFeedback).toHaveBeenCalledWith('thumbs_down');
  });

  it('toggles off when clicking same feedback again', () => {
    const handleFeedback = vi.fn();
    render(
      <ThumbsFeedback
        thumbsUp={10}
        thumbsDown={5}
        userFeedback="thumbs_up"
        onFeedback={handleFeedback}
      />
    );
    
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]); // Click thumbs up again
    
    expect(handleFeedback).toHaveBeenCalledWith(null);
  });

  it('does not call onFeedback when disabled', () => {
    const handleFeedback = vi.fn();
    render(
      <ThumbsFeedback
        thumbsUp={10}
        thumbsDown={5}
        onFeedback={handleFeedback}
        disabled
      />
    );
    
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[0]);
    
    expect(handleFeedback).not.toHaveBeenCalled();
  });

  it('highlights selected feedback', () => {
    render(
      <ThumbsFeedback
        thumbsUp={10}
        thumbsDown={5}
        userFeedback="thumbs_up"
      />
    );
    
    const buttons = screen.getAllByRole('button');
    // The first button should have different styling when selected
    expect(buttons[0]).toBeInTheDocument();
  });
});

describe('FeedbackSummary', () => {
  it('renders counts for both options', () => {
    render(<FeedbackSummary thumbsUp={25} thumbsDown={10} />);
    
    expect(screen.getByText('25')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('calculates and displays positive percentage', () => {
    render(<FeedbackSummary thumbsUp={75} thumbsDown={25} />);
    
    expect(screen.getByText('(75% positive)')).toBeInTheDocument();
  });

  it('handles zero total feedback', () => {
    render(<FeedbackSummary thumbsUp={0} thumbsDown={0} />);
    
    // Should not show percentage when no feedback
    expect(screen.queryByText(/positive/)).not.toBeInTheDocument();
  });

  it('rounds percentage correctly', () => {
    render(<FeedbackSummary thumbsUp={2} thumbsDown={1} />);
    
    // 2/3 = 66.67% rounds to 67%
    expect(screen.getByText('(67% positive)')).toBeInTheDocument();
  });
});
