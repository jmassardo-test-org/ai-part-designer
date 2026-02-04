/**
 * Tests for WhatsNewModal Component
 */

import { render, screen, fireEvent, renderHook, act } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { WhatsNewModal, useWhatsNewModal } from './WhatsNewModal';

describe('WhatsNewModal', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    document.body.style.overflow = '';
  });

  describe('rendering', () => {
    it('renders when isOpen is true', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(<WhatsNewModal isOpen={false} onClose={mockOnClose} />);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('displays the version number', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} version="1.0.0" />);
      expect(screen.getByText(/What's New in v1.0.0/)).toBeInTheDocument();
    });

    it('displays feature list', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      expect(screen.getByText('AI-Powered Design Generation')).toBeInTheDocument();
      expect(screen.getByText('Pro & Enterprise Plans')).toBeInTheDocument();
      expect(screen.getByText('Social Login')).toBeInTheDocument();
    });

    it('shows New badges on features', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      const newBadges = screen.getAllByText('New');
      expect(newBadges.length).toBeGreaterThan(0);
    });
  });

  describe('interactions', () => {
    it('calls onClose when close button is clicked', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      
      const closeButton = screen.getByLabelText('Close');
      fireEvent.click(closeButton);
      
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when "Got it!" button is clicked', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      
      const gotItButton = screen.getByText('Got it!');
      fireEvent.click(gotItButton);
      
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('calls onClose when backdrop is clicked', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      
      // Click the backdrop (first fixed element with bg-black)
      const backdrop = document.querySelector('.bg-black\\/60');
      if (backdrop) {
        fireEvent.click(backdrop);
        expect(mockOnClose).toHaveBeenCalledTimes(1);
      }
    });

    it('calls onClose when Escape key is pressed', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      
      fireEvent.keyDown(document, { key: 'Escape' });
      
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it('does not close when clicking inside the modal content', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      
      const modalContent = screen.getByText('AI-Powered Design Generation');
      fireEvent.click(modalContent);
      
      expect(mockOnClose).not.toHaveBeenCalled();
    });
  });

  describe('body scroll', () => {
    it('disables body scroll when open', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      expect(document.body.style.overflow).toBe('hidden');
    });

    it('re-enables body scroll when closed', () => {
      const { rerender } = render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      expect(document.body.style.overflow).toBe('hidden');
      
      rerender(<WhatsNewModal isOpen={false} onClose={mockOnClose} />);
      expect(document.body.style.overflow).toBe('');
    });
  });

  describe('accessibility', () => {
    it('has proper dialog role', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true');
    });

    it('has accessible title', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      const dialog = screen.getByRole('dialog');
      expect(dialog).toHaveAttribute('aria-labelledby', 'whats-new-title');
    });

    it('close button has accessible label', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      expect(screen.getByLabelText('Close')).toBeInTheDocument();
    });
  });

  describe('changelog link', () => {
    it('displays link to full changelog', () => {
      render(<WhatsNewModal isOpen={true} onClose={mockOnClose} />);
      const link = screen.getByText('View full changelog');
      expect(link).toHaveAttribute('href', '/changelog');
    });
  });
});

describe('useWhatsNewModal', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('returns initial closed state', () => {
    const { result } = renderHook(() => useWhatsNewModal());
    expect(result.current.isOpen).toBe(false);
  });

  it('opens modal when open is called', () => {
    const { result } = renderHook(() => useWhatsNewModal());
    
    act(() => {
      result.current.open();
    });
    
    expect(result.current.isOpen).toBe(true);
  });

  it('closes modal and saves version when close is called', () => {
    const { result } = renderHook(() => useWhatsNewModal());
    
    act(() => {
      result.current.open();
    });
    
    act(() => {
      result.current.close();
    });
    
    expect(result.current.isOpen).toBe(false);
    expect(localStorage.getItem('whats-new-seen-version')).toBe('1.0.0');
  });

  it('shouldShow is true when version not seen', () => {
    const { result } = renderHook(() => useWhatsNewModal());
    expect(result.current.shouldShow).toBe(true);
  });

  it('shouldShow is false when current version already seen', () => {
    localStorage.setItem('whats-new-seen-version', '1.0.0');
    const { result } = renderHook(() => useWhatsNewModal());
    expect(result.current.shouldShow).toBe(false);
  });

  it('shouldShow becomes false after closing', () => {
    const { result } = renderHook(() => useWhatsNewModal());
    expect(result.current.shouldShow).toBe(true);
    
    act(() => {
      result.current.close();
    });
    
    expect(result.current.shouldShow).toBe(false);
  });
});
