/**
 * Tests for HistoryPanel Component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { HistoryPanel, ConversationPreview } from './HistoryPanel';

const mockConversations: ConversationPreview[] = [
  {
    id: '1',
    title: 'Raspberry Pi Case',
    preview: 'Create a case for Raspberry Pi 4',
    timestamp: new Date(Date.now() - 1000 * 60 * 30), // 30 mins ago
    designCount: 2,
    thumbnail: undefined,
  },
  {
    id: '2',
    title: 'Phone Stand',
    preview: 'Design a phone stand with adjustable angle',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 3), // 3 hours ago
    designCount: 1,
  },
  {
    id: '3',
    title: 'Cable Organizer',
    preview: 'Make a desk cable organizer',
    timestamp: new Date(Date.now() - 1000 * 60 * 60 * 24 * 2), // 2 days ago
    designCount: 3,
  },
];

describe('HistoryPanel', () => {
  const mockOnClose = vi.fn();
  const mockOnSelectConversation = vi.fn();
  const mockOnNewConversation = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    document.body.style.overflow = '';
  });

  const renderPanel = (props: Partial<React.ComponentProps<typeof HistoryPanel>> = {}) => {
    return render(
      <HistoryPanel
        isOpen={true}
        onClose={mockOnClose}
        conversations={mockConversations}
        onSelectConversation={mockOnSelectConversation}
        {...props}
      />
    );
  };

  describe('visibility', () => {
    it('renders when open', () => {
      renderPanel({ isOpen: true });
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has correct transform when closed', () => {
      renderPanel({ isOpen: false });
      const panel = screen.getByRole('dialog');
      expect(panel).toHaveClass('-translate-x-full');
    });

    it('has correct transform when open', () => {
      renderPanel({ isOpen: true });
      const panel = screen.getByRole('dialog');
      expect(panel).toHaveClass('translate-x-0');
    });
  });

  describe('header', () => {
    it('displays History title', () => {
      renderPanel();
      expect(screen.getByText('History')).toBeInTheDocument();
    });

    it('has close button', () => {
      renderPanel();
      expect(screen.getByLabelText('Close history panel')).toBeInTheDocument();
    });

    it('calls onClose when close button clicked', () => {
      renderPanel();
      fireEvent.click(screen.getByLabelText('Close history panel'));
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe('new conversation button', () => {
    it('renders new conversation button when callback provided', () => {
      renderPanel({ onNewConversation: mockOnNewConversation });
      expect(screen.getByText('New Design')).toBeInTheDocument();
    });

    it('does not render new conversation button when no callback', () => {
      renderPanel({ onNewConversation: undefined });
      expect(screen.queryByText('New Design')).not.toBeInTheDocument();
    });

    it('calls onNewConversation and closes panel when clicked', () => {
      renderPanel({ onNewConversation: mockOnNewConversation });
      fireEvent.click(screen.getByText('New Design'));
      expect(mockOnNewConversation).toHaveBeenCalled();
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe('conversation list', () => {
    it('displays all conversations', () => {
      renderPanel();
      expect(screen.getByText('Raspberry Pi Case')).toBeInTheDocument();
      expect(screen.getByText('Phone Stand')).toBeInTheDocument();
      expect(screen.getByText('Cable Organizer')).toBeInTheDocument();
    });

    it('displays conversation previews', () => {
      renderPanel();
      expect(screen.getByText('Create a case for Raspberry Pi 4')).toBeInTheDocument();
    });

    it('displays design count', () => {
      renderPanel();
      // The design count is shown as a number next to an icon
      const designCounts = screen.getAllByText('2');
      expect(designCounts.length).toBeGreaterThan(0);
    });

    it('calls onSelectConversation when conversation clicked', () => {
      renderPanel();
      fireEvent.click(screen.getByText('Raspberry Pi Case'));
      expect(mockOnSelectConversation).toHaveBeenCalledWith('1');
    });

    it('closes panel after selecting conversation', () => {
      renderPanel();
      fireEvent.click(screen.getByText('Raspberry Pi Case'));
      expect(mockOnClose).toHaveBeenCalled();
    });

    it('highlights active conversation', () => {
      renderPanel({ activeConversationId: '2' });
      const activeButton = screen.getByText('Phone Stand').closest('button');
      expect(activeButton).toHaveClass('bg-primary-50');
    });
  });

  describe('empty state', () => {
    it('displays empty state when no conversations', () => {
      renderPanel({ conversations: [] });
      expect(screen.getByText('No conversations yet')).toBeInTheDocument();
    });

    it('displays helpful message in empty state', () => {
      renderPanel({ conversations: [] });
      expect(screen.getByText('Start a new design to get started')).toBeInTheDocument();
    });
  });

  describe('loading state', () => {
    it('displays loading skeletons when loading', () => {
      renderPanel({ isLoading: true });
      const loadingElements = screen.getAllByRole('status');
      expect(loadingElements.length).toBeGreaterThan(0);
    });

    it('does not display conversations when loading', () => {
      renderPanel({ isLoading: true });
      expect(screen.queryByText('Raspberry Pi Case')).not.toBeInTheDocument();
    });
  });

  describe('keyboard navigation', () => {
    it('closes panel on Escape key', () => {
      renderPanel();
      fireEvent.keyDown(document, { key: 'Escape' });
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe('backdrop', () => {
    it('closes panel when backdrop clicked', () => {
      const { container } = renderPanel();
      const backdrop = container.querySelector('[aria-hidden="true"]');
      expect(backdrop).toBeInTheDocument();
      fireEvent.click(backdrop!);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe('accessibility', () => {
    it('has dialog role', () => {
      renderPanel();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('has aria-modal attribute', () => {
      renderPanel();
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    });

    it('has aria-label', () => {
      renderPanel();
      expect(screen.getByRole('dialog')).toHaveAttribute(
        'aria-label',
        'Conversation history'
      );
    });

    it('has navigation landmark for conversation list', () => {
      renderPanel();
      expect(screen.getByRole('navigation')).toHaveAttribute(
        'aria-label',
        'Conversation history'
      );
    });
  });

  describe('relative time formatting', () => {
    it('displays "30m ago" for recent conversations', () => {
      renderPanel();
      expect(screen.getByText('30m ago')).toBeInTheDocument();
    });

    it('displays hours ago format', () => {
      renderPanel();
      expect(screen.getByText('3h ago')).toBeInTheDocument();
    });

    it('displays days ago format', () => {
      renderPanel();
      expect(screen.getByText('2d ago')).toBeInTheDocument();
    });
  });
});
