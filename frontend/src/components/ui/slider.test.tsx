import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { Slider } from './slider';

describe('Slider', () => {
  it('renders without crashing', () => {
    render(<Slider />);
    expect(screen.getByRole('slider')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Slider className="custom-slider" data-testid="slider-container" />);
    expect(screen.getByTestId('slider-container')).toHaveClass('custom-slider');
  });

  it('uses default value', () => {
    render(<Slider defaultValue={[75]} />);
    expect(screen.getByRole('slider')).toHaveValue('75');
  });

  it('respects min and max props', () => {
    render(<Slider min={10} max={50} defaultValue={[30]} />);
    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('min', '10');
    expect(slider).toHaveAttribute('max', '50');
  });

  it('respects step prop', () => {
    render(<Slider step={5} />);
    expect(screen.getByRole('slider')).toHaveAttribute('step', '5');
  });

  it('calls onValueChange when value changes', () => {
    const handleChange = vi.fn();
    render(<Slider onValueChange={handleChange} defaultValue={[50]} />);

    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '75' } });

    expect(handleChange).toHaveBeenCalledWith([75]);
  });

  it('calls onValueCommit on mouse up', () => {
    const handleCommit = vi.fn();
    render(<Slider onValueCommit={handleCommit} defaultValue={[50]} />);

    const slider = screen.getByRole('slider');
    fireEvent.mouseUp(slider);

    expect(handleCommit).toHaveBeenCalled();
  });

  it('applies disabled state', () => {
    render(<Slider disabled data-testid="slider-container" />);
    expect(screen.getByRole('slider')).toBeDisabled();
    expect(screen.getByTestId('slider-container')).toHaveClass('opacity-50');
  });

  it('works as controlled component', () => {
    const { rerender } = render(<Slider value={[25]} />);
    expect(screen.getByRole('slider')).toHaveValue('25');

    rerender(<Slider value={[50]} />);
    expect(screen.getByRole('slider')).toHaveValue('50');
  });
});
