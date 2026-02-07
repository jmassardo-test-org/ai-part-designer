/**
 * Tests for CommandAutocomplete component and useCommandAutocomplete hook
 */

import { render, screen, fireEvent, renderHook, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CommandAutocomplete, useCommandAutocomplete } from './CommandAutocomplete';

describe('CommandAutocomplete', () => {
  const mockOnSelect = vi.fn();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('rendering', () => {
    it('shows suggestions when input starts with /', () => {
      render(
        <CommandAutocomplete
          input="/"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      expect(screen.getByRole('listbox')).toBeInTheDocument();
      expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
    });

    it('does not render when not visible', () => {
      render(
        <CommandAutocomplete
          input="/"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={false}
        />
      );

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('does not render when input does not start with /', () => {
      render(
        <CommandAutocomplete
          input="hello"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('displays command name and description', () => {
      render(
        <CommandAutocomplete
          input="/save"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      expect(screen.getByText('/save')).toBeInTheDocument();
      expect(screen.getByText(/save the current design/i)).toBeInTheDocument();
    });
  });

  describe('filtering', () => {
    it('filters commands based on input', () => {
      render(
        <CommandAutocomplete
          input="/exp"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      const options = screen.getAllByRole('option');
      // Should show export and exportall
      expect(options.length).toBe(2);
    });

    it('shows no suggestions for non-matching input', () => {
      render(
        <CommandAutocomplete
          input="/zzzzz"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('shows all commands for just slash', () => {
      render(
        <CommandAutocomplete
          input="/"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      const options = screen.getAllByRole('option');
      // Should show all commands (currently 17)
      expect(options.length).toBeGreaterThanOrEqual(10);
    });
  });

  describe('keyboard navigation', () => {
    it('highlights first option by default', () => {
      render(
        <CommandAutocomplete
          input="/"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      const firstOption = screen.getAllByRole('option')[0];
      expect(firstOption).toHaveAttribute('aria-selected', 'true');
    });

    it('moves selection down with ArrowDown', () => {
      render(
        <CommandAutocomplete
          input="/"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      fireEvent.keyDown(window, { key: 'ArrowDown' });

      const options = screen.getAllByRole('option');
      expect(options[0]).toHaveAttribute('aria-selected', 'false');
      expect(options[1]).toHaveAttribute('aria-selected', 'true');
    });

    it('moves selection up with ArrowUp', () => {
      render(
        <CommandAutocomplete
          input="/"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      // First go down, then up
      fireEvent.keyDown(window, { key: 'ArrowDown' });
      fireEvent.keyDown(window, { key: 'ArrowUp' });

      const options = screen.getAllByRole('option');
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
    });

    it('selects command on Enter', () => {
      render(
        <CommandAutocomplete
          input="/save"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      fireEvent.keyDown(window, { key: 'Enter' });

      expect(mockOnSelect).toHaveBeenCalledWith('/save');
    });

    it('selects command on Tab', () => {
      render(
        <CommandAutocomplete
          input="/save"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      fireEvent.keyDown(window, { key: 'Tab' });

      expect(mockOnSelect).toHaveBeenCalledWith('/save');
    });

    it('closes on Escape', () => {
      render(
        <CommandAutocomplete
          input="/"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      fireEvent.keyDown(window, { key: 'Escape' });

      expect(mockOnClose).toHaveBeenCalled();
    });

    it('wraps around when navigating past last option', () => {
      render(
        <CommandAutocomplete
          input="/exp"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      // There are 2 options (export, exportall)
      fireEvent.keyDown(window, { key: 'ArrowDown' }); // Move to exportall
      fireEvent.keyDown(window, { key: 'ArrowDown' }); // Wrap to export

      const options = screen.getAllByRole('option');
      expect(options[0]).toHaveAttribute('aria-selected', 'true');
    });
  });

  describe('mouse interaction', () => {
    it('selects command on click', async () => {
      const user = userEvent.setup();
      render(
        <CommandAutocomplete
          input="/save"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      // Get first option (there are multiple - /save and /saveas)
      const options = screen.getAllByRole('option');
      await user.click(options[0]);

      expect(mockOnSelect).toHaveBeenCalledWith('/save');
    });
  });

  describe('argument hints', () => {
    it('shows argument placeholder for commands with args', () => {
      render(
        <CommandAutocomplete
          input="/export"
          onSelect={mockOnSelect}
          onClose={mockOnClose}
          visible={true}
        />
      );

      // Export command has format arg - there may be multiple
      const formatHints = screen.getAllByText('<format>');
      expect(formatHints.length).toBeGreaterThan(0);
    });
  });
});

describe('useCommandAutocomplete', () => {
  it('starts with autocomplete hidden', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    expect(result.current.showAutocomplete).toBe(false);
  });

  it('shows autocomplete when input starts with /', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('/');
    });

    expect(result.current.showAutocomplete).toBe(true);
  });

  it('hides autocomplete when input has space (typing args)', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('/save my-design');
    });

    expect(result.current.showAutocomplete).toBe(false);
  });

  it('hides autocomplete for regular text', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('hello world');
    });

    expect(result.current.showAutocomplete).toBe(false);
  });

  it('detects command input correctly', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('/help');
    });

    expect(result.current.isCommand).toBe(true);
  });

  it('does not detect regular text as command', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('hello');
    });

    expect(result.current.isCommand).toBe(false);
  });

  it('parses command without arguments', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('/help');
    });

    const parsed = result.current.parseCommand();
    expect(parsed).toEqual({ command: 'help', args: [] });
  });

  it('parses command with arguments', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('/save my design name');
    });

    const parsed = result.current.parseCommand();
    expect(parsed).toEqual({ command: 'save', args: ['my', 'design', 'name'] });
  });

  it('returns null for non-command input', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('hello');
    });

    expect(result.current.parseCommand()).toBeNull();
  });

  it('closes autocomplete on command select', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('/');
    });

    expect(result.current.showAutocomplete).toBe(true);

    act(() => {
      result.current.handleCommandSelect('/save');
    });

    expect(result.current.showAutocomplete).toBe(false);
    expect(result.current.inputValue).toBe('/save');
  });

  it('closes autocomplete on handleClose', () => {
    const { result } = renderHook(() => useCommandAutocomplete());

    act(() => {
      result.current.handleInputChange('/');
    });

    act(() => {
      result.current.handleClose();
    });

    expect(result.current.showAutocomplete).toBe(false);
  });
});
