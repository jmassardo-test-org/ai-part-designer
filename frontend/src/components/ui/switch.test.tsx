import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createRef } from 'react';
import { Switch } from './switch';

describe('Switch', () => {
  it('renders without crashing', () => {
    render(<Switch />);
    expect(screen.getByRole('switch')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Switch className="custom-switch" />);
    expect(screen.getByRole('switch')).toHaveClass('custom-switch');
  });

  it('renders in unchecked state by default', () => {
    render(<Switch />);
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
    expect(screen.getByRole('switch')).toHaveAttribute('data-state', 'unchecked');
  });

  it('renders in checked state when defaultChecked is true', () => {
    render(<Switch defaultChecked />);
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByRole('switch')).toHaveAttribute('data-state', 'checked');
  });

  it('toggles state when clicked', async () => {
    const user = userEvent.setup();
    render(<Switch />);

    const switchElement = screen.getByRole('switch');
    expect(switchElement).toHaveAttribute('aria-checked', 'false');

    await user.click(switchElement);
    expect(switchElement).toHaveAttribute('aria-checked', 'true');

    await user.click(switchElement);
    expect(switchElement).toHaveAttribute('aria-checked', 'false');
  });

  it('calls onCheckedChange when toggled', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<Switch onCheckedChange={handleChange} />);

    await user.click(screen.getByRole('switch'));

    expect(handleChange).toHaveBeenCalledWith(true);
  });

  it('works as controlled component', () => {
    const { rerender } = render(<Switch checked={false} />);
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'false');

    rerender(<Switch checked={true} />);
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true');
  });

  it('applies disabled state', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<Switch disabled onCheckedChange={handleChange} />);

    const switchElement = screen.getByRole('switch');
    expect(switchElement).toBeDisabled();

    await user.click(switchElement);
    expect(handleChange).not.toHaveBeenCalled();
  });

  it('applies bg-primary class when checked', () => {
    render(<Switch defaultChecked />);
    expect(screen.getByRole('switch')).toHaveClass('bg-primary');
  });

  it('applies bg-input class when unchecked', () => {
    render(<Switch />);
    expect(screen.getByRole('switch')).toHaveClass('bg-input');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLButtonElement>();
    render(<Switch ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLButtonElement);
  });
});
