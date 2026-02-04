/**
 * Tests for ChatInput component with slash command support
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ChatInput } from './ChatInput';

describe('ChatInput', () => {
  const mockOnSend = vi.fn();
  const mockOnGenerate = vi.fn();
  const mockOnCommand = vi.fn();
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('basic rendering', () => {
    it('renders textarea with placeholder', () => {
      render(<ChatInput onSend={mockOnSend} />);
      
      expect(screen.getByPlaceholderText(/describe the part/i)).toBeInTheDocument();
    });

    it('renders custom placeholder', () => {
      render(<ChatInput onSend={mockOnSend} placeholder="Custom placeholder" />);
      
      expect(screen.getByPlaceholderText('Custom placeholder')).toBeInTheDocument();
    });

    it('renders send button', () => {
      render(<ChatInput onSend={mockOnSend} />);
      
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('renders generate button when showGenerateButton is true', () => {
      render(
        <ChatInput 
          onSend={mockOnSend} 
          onGenerate={mockOnGenerate}
          showGenerateButton={true}
        />
      );
      
      expect(screen.getByText('Generate')).toBeInTheDocument();
    });
  });

  describe('sending messages', () => {
    it('calls onSend when send button is clicked', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello world');
      
      const sendButton = screen.getByRole('button');
      await user.click(sendButton);
      
      expect(mockOnSend).toHaveBeenCalledWith('Hello world');
    });

    it('calls onSend when Enter is pressed', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello world{enter}');
      
      expect(mockOnSend).toHaveBeenCalledWith('Hello world');
    });

    it('does not send when Shift+Enter is pressed', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Line 1');
      await user.keyboard('{Shift>}{Enter}{/Shift}');
      await user.type(textarea, 'Line 2');
      
      // Should not have sent yet
      expect(mockOnSend).not.toHaveBeenCalled();
    });

    it('clears input after sending', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, 'Hello world{enter}');
      
      expect(textarea).toHaveValue('');
    });

    it('trims whitespace from message', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '  Hello world  {enter}');
      
      expect(mockOnSend).toHaveBeenCalledWith('Hello world');
    });

    it('does not send empty messages', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '   {enter}');
      
      expect(mockOnSend).not.toHaveBeenCalled();
    });
  });

  describe('disabled state', () => {
    it('disables textarea when disabled prop is true', () => {
      render(<ChatInput onSend={mockOnSend} disabled={true} />);
      
      expect(screen.getByRole('textbox')).toBeDisabled();
    });

    it('disables send button when disabled', () => {
      render(<ChatInput onSend={mockOnSend} disabled={true} />);
      
      expect(screen.getByRole('button')).toBeDisabled();
    });

    it('disables send button when loading', () => {
      render(<ChatInput onSend={mockOnSend} loading={true} />);
      
      expect(screen.getByRole('textbox')).toBeDisabled();
    });
  });

  describe('slash commands', () => {
    it('shows autocomplete when typing /', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} onCommand={mockOnCommand} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '/');
      
      // Wait for autocomplete to appear - check for listbox role
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });
      
      // Verify at least one command is shown
      expect(screen.getAllByRole('option').length).toBeGreaterThan(0);
    });

    it('filters commands as user types', async () => {
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} onCommand={mockOnCommand} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '/exp');
      
      // Should show filtered commands only
      await waitFor(() => {
        const options = screen.getAllByRole('option');
        // Should have export and exportall (both start with exp)
        expect(options.length).toBe(2);
      });
    });

    it('calls onCommand instead of onSend for commands', async () => {
      mockOnCommand.mockResolvedValue({ success: true, message: 'Done' });
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} onCommand={mockOnCommand} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '/help{enter}');
      
      await waitFor(() => {
        expect(mockOnCommand).toHaveBeenCalledWith('help', []);
        expect(mockOnSend).not.toHaveBeenCalled();
      });
    });

    it('parses command arguments correctly', async () => {
      mockOnCommand.mockResolvedValue({ success: true, message: 'Saved' });
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} onCommand={mockOnCommand} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '/save My Design Name{enter}');
      
      await waitFor(() => {
        expect(mockOnCommand).toHaveBeenCalledWith('save', ['My', 'Design', 'Name']);
      });
    });

    it('clears input after successful command', async () => {
      mockOnCommand.mockResolvedValue({ success: true, message: 'Done' });
      const user = userEvent.setup();
      render(<ChatInput onSend={mockOnSend} onCommand={mockOnCommand} />);
      
      const textarea = screen.getByRole('textbox');
      await user.type(textarea, '/help{enter}');
      
      await waitFor(() => {
        expect(textarea).toHaveValue('');
      });
    });
  });

  describe('generate button', () => {
    it('calls onGenerate when generate button is clicked', async () => {
      const user = userEvent.setup();
      render(
        <ChatInput 
          onSend={mockOnSend} 
          onGenerate={mockOnGenerate}
          showGenerateButton={true}
        />
      );
      
      const generateButton = screen.getByText('Generate').closest('button');
      await user.click(generateButton!);
      
      expect(mockOnGenerate).toHaveBeenCalled();
    });

    it('disables generate button when generateDisabled is true', () => {
      render(
        <ChatInput 
          onSend={mockOnSend} 
          onGenerate={mockOnGenerate}
          showGenerateButton={true}
          generateDisabled={true}
        />
      );
      
      const generateButton = screen.getByText('Generate').closest('button');
      expect(generateButton).toBeDisabled();
    });
  });
});
