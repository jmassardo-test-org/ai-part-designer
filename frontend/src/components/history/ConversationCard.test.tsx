/**
 * Tests for ConversationCard Component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  ConversationCard,
  ConversationCardData,
  formatRelativeTime,
  extractTitleFromPrompt,
  extractPreviewFromPrompt,
} from './ConversationCard';

// =============================================================================
// Test Utilities
// =============================================================================

const mockConversation: ConversationCardData = {
  id: 'conv-1',
  title: 'Hexagonal motor mount',
  preview: 'with integrated cooling channels',
  timestamp: new Date(Date.now() - 3600000), // 1 hour ago
  designCount: 3,
  thumbnailUrl: 'https://example.com/thumbnail.png',
  isActive: false,
};

const createConversation = (overrides: Partial<ConversationCardData> = {}): ConversationCardData => ({
  ...mockConversation,
  ...overrides,
});

// =============================================================================
// Tests: formatRelativeTime
// =============================================================================

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-15T12:00:00'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "Just now" for times less than 1 minute ago', () => {
    const date = new Date(Date.now() - 30000); // 30 seconds ago
    expect(formatRelativeTime(date)).toBe('Just now');
  });

  it('returns minutes for times less than 1 hour ago', () => {
    const date = new Date(Date.now() - 15 * 60000); // 15 minutes ago
    expect(formatRelativeTime(date)).toBe('15m ago');
  });

  it('returns hours for times less than 24 hours ago', () => {
    const date = new Date(Date.now() - 5 * 3600000); // 5 hours ago
    expect(formatRelativeTime(date)).toBe('5h ago');
  });

  it('returns "Yesterday" for dates 1 day ago', () => {
    const date = new Date(Date.now() - 86400000); // 1 day ago
    expect(formatRelativeTime(date)).toBe('Yesterday');
  });

  it('returns days for dates less than 1 week ago', () => {
    const date = new Date(Date.now() - 4 * 86400000); // 4 days ago
    expect(formatRelativeTime(date)).toBe('4d ago');
  });

  it('returns "1 week ago" for dates 1 week ago', () => {
    const date = new Date(Date.now() - 7 * 86400000); // 7 days ago
    expect(formatRelativeTime(date)).toBe('1 week ago');
  });

  it('returns weeks for dates less than 4 weeks ago', () => {
    const date = new Date(Date.now() - 14 * 86400000); // 2 weeks ago
    expect(formatRelativeTime(date)).toBe('2 weeks ago');
  });

  it('returns formatted date for older dates', () => {
    // More than 4 weeks ago - use a date far enough back
    const date = new Date(Date.now() - 60 * 86400000); // 60 days ago
    const result = formatRelativeTime(date);
    expect(result).toMatch(/\w+ \d+/); // Should be "Nov 16" or similar
  });

  it('includes year for dates from previous year', () => {
    // Use a fixed date from 2022 (mocked time is Jan 2024)
    const date = new Date('2022-06-15T12:00:00.000Z');
    const result = formatRelativeTime(date);
    expect(result).toMatch(/Jun \d+, 2022/);
  });
});

// =============================================================================
// Tests: extractTitleFromPrompt
// =============================================================================

describe('extractTitleFromPrompt', () => {
  it('returns first line of prompt', () => {
    const prompt = 'Design a motor mount\nwith cooling channels';
    expect(extractTitleFromPrompt(prompt)).toBe('Design a motor mount');
  });

  it('truncates long first lines', () => {
    const prompt = 'This is a very long title that exceeds the maximum allowed length for display';
    const result = extractTitleFromPrompt(prompt);
    expect(result.length).toBeLessThanOrEqual(50);
    expect(result).toContain('...');
  });

  it('returns "Untitled Design" for empty prompts', () => {
    expect(extractTitleFromPrompt('')).toBe('Untitled Design');
  });

  it('returns "Untitled Design" for whitespace-only prompts', () => {
    expect(extractTitleFromPrompt('   \n   ')).toBe('Untitled Design');
  });

  it('handles single-line prompts', () => {
    const prompt = 'Simple design request';
    expect(extractTitleFromPrompt(prompt)).toBe('Simple design request');
  });
});

// =============================================================================
// Tests: extractPreviewFromPrompt
// =============================================================================

describe('extractPreviewFromPrompt', () => {
  it('returns content after first line', () => {
    const prompt = 'Design a motor mount\nwith cooling channels\nand M4 mounting holes';
    expect(extractPreviewFromPrompt(prompt)).toBe('with cooling channels and M4 mounting holes');
  });

  it('truncates long previews', () => {
    const prompt = 'Title\n' + 'a'.repeat(100);
    const result = extractPreviewFromPrompt(prompt);
    expect(result.length).toBeLessThanOrEqual(80);
    expect(result).toContain('...');
  });

  it('returns empty string for single-line prompts', () => {
    expect(extractPreviewFromPrompt('Single line')).toBe('');
  });

  it('returns empty string for empty prompts', () => {
    expect(extractPreviewFromPrompt('')).toBe('');
  });
});

// =============================================================================
// Tests: ConversationCard Component
// =============================================================================

describe('ConversationCard', () => {
  describe('rendering', () => {
    it('renders the conversation title', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.getByText('Hexagonal motor mount')).toBeInTheDocument();
    });

    it('renders the preview text', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.getByText('with integrated cooling channels')).toBeInTheDocument();
    });

    it('renders the thumbnail when provided', () => {
      render(<ConversationCard conversation={mockConversation} />);
      const img = screen.getByAltText('Design preview');
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute('src', 'https://example.com/thumbnail.png');
    });

    it('renders a placeholder when no thumbnail', () => {
      const conv = createConversation({ thumbnailUrl: undefined });
      render(<ConversationCard conversation={conv} />);
      expect(screen.queryByAltText('Design preview')).not.toBeInTheDocument();
    });

    it('renders design count', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.getByText(/3 designs/i)).toBeInTheDocument();
    });

    it('renders singular design for count of 1', () => {
      const conv = createConversation({ designCount: 1 });
      render(<ConversationCard conversation={conv} />);
      expect(screen.getByText(/1 design$/i)).toBeInTheDocument();
    });

    it('does not render design count when 0', () => {
      const conv = createConversation({ designCount: 0 });
      render(<ConversationCard conversation={conv} />);
      expect(screen.queryByText(/design/i)).not.toBeInTheDocument();
    });

    it('hides preview when showPreview is false', () => {
      render(<ConversationCard conversation={mockConversation} showPreview={false} />);
      expect(screen.queryByText('with integrated cooling channels')).not.toBeInTheDocument();
    });
  });

  describe('sizes', () => {
    it('renders small size', () => {
      const { container } = render(<ConversationCard conversation={mockConversation} size="sm" />);
      expect(container.querySelector('article')).toHaveClass('p-2');
    });

    it('renders medium size (default)', () => {
      const { container } = render(<ConversationCard conversation={mockConversation} />);
      expect(container.querySelector('article')).toHaveClass('p-3');
    });

    it('renders large size', () => {
      const { container } = render(<ConversationCard conversation={mockConversation} size="lg" />);
      expect(container.querySelector('article')).toHaveClass('p-4');
    });
  });

  describe('active state', () => {
    it('applies active styles when isActive is true', () => {
      const conv = createConversation({ isActive: true });
      const { container } = render(<ConversationCard conversation={conv} />);
      const article = container.querySelector('article');
      expect(article).toHaveClass('bg-primary-50');
    });

    it('sets aria-current when active', () => {
      const conv = createConversation({ isActive: true });
      render(<ConversationCard conversation={conv} />);
      expect(screen.getByRole('article')).toHaveAttribute('aria-current', 'true');
    });

    it('does not set aria-current when not active', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.getByRole('article')).not.toHaveAttribute('aria-current');
    });
  });

  describe('interactivity', () => {
    it('calls onClick when clicked', () => {
      const onClick = vi.fn();
      render(<ConversationCard conversation={mockConversation} onClick={onClick} />);
      
      fireEvent.click(screen.getByRole('button'));
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('has role="button" when onClick is provided', () => {
      const onClick = vi.fn();
      render(<ConversationCard conversation={mockConversation} onClick={onClick} />);
      expect(screen.getByRole('button')).toBeInTheDocument();
    });

    it('does not have role="button" when no onClick', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('handles Enter key press', () => {
      const onClick = vi.fn();
      render(<ConversationCard conversation={mockConversation} onClick={onClick} />);
      
      fireEvent.keyDown(screen.getByRole('button'), { key: 'Enter' });
      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('has cursor-pointer when clickable', () => {
      const onClick = vi.fn();
      const { container } = render(<ConversationCard conversation={mockConversation} onClick={onClick} />);
      expect(container.querySelector('article')).toHaveClass('cursor-pointer');
    });

    it('is focusable when clickable', () => {
      const onClick = vi.fn();
      render(<ConversationCard conversation={mockConversation} onClick={onClick} />);
      expect(screen.getByRole('button')).toHaveAttribute('tabIndex', '0');
    });
  });

  describe('custom className', () => {
    it('applies custom className', () => {
      const { container } = render(
        <ConversationCard conversation={mockConversation} className="custom-class" />
      );
      expect(container.querySelector('article')).toHaveClass('custom-class');
    });
  });

  describe('timestamp formatting', () => {
    beforeEach(() => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2024-01-15T12:00:00'));
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('displays relative timestamp', () => {
      const conv = createConversation({
        timestamp: new Date(Date.now() - 2 * 3600000), // 2 hours ago
      });
      render(<ConversationCard conversation={conv} />);
      expect(screen.getByText('2h ago')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('uses semantic article element', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.getByRole('article')).toBeInTheDocument();
    });

    it('uses heading for title', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('Hexagonal motor mount');
    });

    it('has descriptive alt text for thumbnail', () => {
      render(<ConversationCard conversation={mockConversation} />);
      expect(screen.getByAltText('Design preview')).toBeInTheDocument();
    });
  });
});
