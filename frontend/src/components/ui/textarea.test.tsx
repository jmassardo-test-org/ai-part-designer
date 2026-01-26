import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createRef } from 'react';
import { Textarea } from './textarea';

describe('Textarea', () => {
  it('renders without crashing', () => {
    render(<Textarea />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(<Textarea className="custom-textarea" />);
    expect(screen.getByRole('textbox')).toHaveClass('custom-textarea');
  });

  it('displays placeholder text', () => {
    render(<Textarea placeholder="Enter description" />);
    expect(screen.getByPlaceholderText('Enter description')).toBeInTheDocument();
  });

  it('accepts input text', async () => {
    const user = userEvent.setup();
    render(<Textarea />);

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello World');

    expect(textarea).toHaveValue('Hello World');
  });

  it('handles onChange event', async () => {
    const handleChange = vi.fn();
    const user = userEvent.setup();
    render(<Textarea onChange={handleChange} />);

    await user.type(screen.getByRole('textbox'), 'Test');

    expect(handleChange).toHaveBeenCalled();
  });

  it('handles disabled state', () => {
    render(<Textarea disabled />);
    expect(screen.getByRole('textbox')).toBeDisabled();
  });

  it('handles readonly state', () => {
    render(<Textarea readOnly value="Read only text" />);
    expect(screen.getByRole('textbox')).toHaveAttribute('readonly');
  });

  it('applies min-height style', () => {
    render(<Textarea />);
    expect(screen.getByRole('textbox')).toHaveClass('min-h-[80px]');
  });

  it('forwards ref correctly', () => {
    const ref = createRef<HTMLTextAreaElement>();
    render(<Textarea ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLTextAreaElement);
  });

  it('passes through additional props', () => {
    render(<Textarea data-testid="textarea" rows={5} />);
    const textarea = screen.getByTestId('textarea');
    expect(textarea).toHaveAttribute('rows', '5');
  });

  it('works as controlled component', () => {
    const { rerender } = render(<Textarea value="Initial" onChange={() => {}} />);
    expect(screen.getByRole('textbox')).toHaveValue('Initial');

    rerender(<Textarea value="Updated" onChange={() => {}} />);
    expect(screen.getByRole('textbox')).toHaveValue('Updated');
  });
});
