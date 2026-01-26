import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createRef } from 'react';
import { Input } from './input';

describe('Input', () => {
  it('renders without crashing', () => {
    render(<Input />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Input className="custom-input" />);
    expect(screen.getByRole('textbox')).toHaveClass('custom-input');
  });

  it('displays placeholder text', () => {
    render(<Input placeholder="Enter your name" />);
    expect(screen.getByPlaceholderText('Enter your name')).toBeInTheDocument();
  });

  it('renders with correct type', () => {
    render(<Input type="email" data-testid="email-input" />);
    expect(screen.getByTestId('email-input')).toHaveAttribute('type', 'email');
  });

  it('accepts input text', async () => {
    const user = userEvent.setup();
    render(<Input />);

    const input = screen.getByRole('textbox');
    await user.type(input, 'Hello World');

    expect(input).toHaveValue('Hello World');
  });

  it('handles onChange event', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<Input onChange={handleChange} />);

    await user.type(screen.getByRole('textbox'), 'Test');

    expect(handleChange).toHaveBeenCalled();
  });

  it('handles disabled state', () => {
    render(<Input disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('handles readonly state', () => {
    render(<Input readOnly value="Read only text" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('readonly');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLInputElement>();
    render(<Input ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });

  it('applies default styles', () => {
    render(<Input />);
    const input = screen.getByRole('textbox');
    expect(input).toHaveClass('h-10');
    expect(input).toHaveClass('rounded-md');
    expect(input).toHaveClass('border');
  });

  it('passes through additional props', () => {
    render(<Input data-testid="input" maxLength={10} />);
    expect(screen.getByTestId('input')).toHaveAttribute('maxLength', '10');
  });

  it('works as controlled component', () => {
    const { rerender } = render(<Input value="Initial" onChange={() => {}} />);
    expect(screen.getByRole('textbox')).toHaveValue('Initial');

    rerender(<Input value="Updated" onChange={() => {}} />);
    expect(screen.getByRole('textbox')).toHaveValue('Updated');
  });

  it('renders number input type', () => {
    render(<Input type="number" data-testid="number-input" />);
    expect(screen.getByTestId('number-input')).toHaveAttribute('type', 'number');
  });

  it('renders password input type', () => {
    render(<Input type="password" data-testid="password-input" />);
    expect(screen.getByTestId('password-input')).toHaveAttribute('type', 'password');
  });
});
