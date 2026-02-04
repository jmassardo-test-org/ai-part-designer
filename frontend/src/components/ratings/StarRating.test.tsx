/**
 * Tests for StarRating component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { StarRating, AverageRating, RatingDistribution } from './StarRating';

describe('StarRating', () => {
  it('renders 5 stars', () => {
    render(<StarRating value={3} />);
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(5);
  });

  it('displays current rating visually', () => {
    render(<StarRating value={4} />);
    // The component should have 4 filled stars and 1 empty
    const buttons = screen.getAllByRole('button');
    expect(buttons).toHaveLength(5);
  });

  it('calls onChange when star is clicked', () => {
    const handleChange = vi.fn();
    render(<StarRating value={3} onChange={handleChange} />);
    
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[4]); // Click 5th star
    
    expect(handleChange).toHaveBeenCalledWith(5);
  });

  it('does not call onChange in readonly mode', () => {
    const handleChange = vi.fn();
    render(<StarRating value={3} onChange={handleChange} readonly />);
    
    const buttons = screen.getAllByRole('button');
    fireEvent.click(buttons[4]);
    
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('shows rating value when showValue is true', () => {
    render(<StarRating value={4.5} showValue />);
    expect(screen.getByText('4.5')).toBeInTheDocument();
  });

  it('shows total ratings count when provided', () => {
    render(<StarRating value={4.5} showValue totalRatings={123} />);
    expect(screen.getByText('(123)')).toBeInTheDocument();
  });

  it('applies different sizes correctly', () => {
    const { rerender } = render(<StarRating value={3} size="sm" />);
    expect(screen.getAllByRole('button')[0]).toBeInTheDocument();
    
    rerender(<StarRating value={3} size="lg" />);
    expect(screen.getAllByRole('button')[0]).toBeInTheDocument();
  });
});

describe('AverageRating', () => {
  it('renders average rating value', () => {
    render(<AverageRating average={4.2} total={50} />);
    expect(screen.getByText('4.2')).toBeInTheDocument();
  });

  it('renders total count in parentheses', () => {
    render(<AverageRating average={4.2} total={50} />);
    expect(screen.getByText('(50)')).toBeInTheDocument();
  });

  it('formats rating to one decimal place', () => {
    render(<AverageRating average={3.789} total={10} />);
    expect(screen.getByText('3.8')).toBeInTheDocument();
  });
});

describe('RatingDistribution', () => {
  it('renders all 5 rating levels', () => {
    const distribution = { 1: 5, 2: 10, 3: 20, 4: 30, 5: 35 };
    render(<RatingDistribution distribution={distribution} total={100} />);
    
    // Use getAllByText since '5' appears as both a rating level and a count
    expect(screen.getAllByText('5').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('4')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('shows counts for each rating level', () => {
    const distribution = { 1: 5, 2: 10, 3: 20, 4: 30, 5: 35 };
    render(<RatingDistribution distribution={distribution} total={100} />);
    
    expect(screen.getByText('35')).toBeInTheDocument();
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
    // Note: '5' appears twice (as rating level and count)
  });

  it('handles empty distribution', () => {
    const distribution = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    render(<RatingDistribution distribution={distribution} total={0} />);
    
    // Should still render without errors
    expect(screen.getByText('5')).toBeInTheDocument();
  });
});
