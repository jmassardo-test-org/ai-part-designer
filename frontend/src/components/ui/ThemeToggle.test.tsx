/**
 * Tests for ThemeToggle Component
 */

import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ThemeToggle } from './ThemeToggle';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock matchMedia
const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
  matches: query === '(prefers-color-scheme: dark)',
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}));

Object.defineProperty(window, 'matchMedia', { value: matchMediaMock });

const renderWithTheme = (
  ui: React.ReactElement,
  defaultTheme: 'light' | 'dark' = 'dark'
) => {
  return render(
    <ThemeProvider defaultTheme={defaultTheme}>{ui}</ThemeProvider>
  );
};

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    document.documentElement.classList.remove('light', 'dark');
  });

  describe('simple toggle button', () => {
    it('renders toggle button', () => {
      renderWithTheme(<ThemeToggle />);
      
      const button = screen.getByRole('button');
      expect(button).toBeInTheDocument();
    });

    it('has correct aria-label for dark mode', () => {
      renderWithTheme(<ThemeToggle />, 'dark');
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Switch to light mode');
    });

    it('has correct aria-label for light mode', () => {
      renderWithTheme(<ThemeToggle />, 'light');
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Switch to dark mode');
    });

    it('toggles theme on click', () => {
      renderWithTheme(<ThemeToggle />, 'dark');
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      // After toggle, should switch to light mode
      expect(document.documentElement.classList.contains('light')).toBe(true);
    });

    it('shows sun icon in dark mode', () => {
      renderWithTheme(<ThemeToggle />, 'dark');
      
      // Sun icon should be visible (for switching to light)
      const button = screen.getByRole('button');
      expect(button.querySelector('svg')).toBeInTheDocument();
    });

    it('shows moon icon in light mode', () => {
      renderWithTheme(<ThemeToggle />, 'light');
      
      const button = screen.getByRole('button');
      expect(button.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('size variants', () => {
    it('renders small size', () => {
      renderWithTheme(<ThemeToggle size="sm" />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-8', 'w-8');
    });

    it('renders medium size (default)', () => {
      renderWithTheme(<ThemeToggle size="md" />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-10', 'w-10');
    });

    it('renders large size', () => {
      renderWithTheme(<ThemeToggle size="lg" />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('h-12', 'w-12');
    });
  });

  describe('dropdown mode', () => {
    it('renders dropdown trigger when showDropdown is true', () => {
      renderWithTheme(<ThemeToggle showDropdown />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveAttribute('aria-label', 'Select theme');
      expect(button).toHaveAttribute('aria-haspopup', 'true');
    });

    it('opens dropdown on click', () => {
      renderWithTheme(<ThemeToggle showDropdown />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      expect(screen.getByRole('menu')).toBeInTheDocument();
    });

    it('shows all theme options in dropdown', () => {
      renderWithTheme(<ThemeToggle showDropdown />);
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      expect(screen.getByText('Light')).toBeInTheDocument();
      expect(screen.getByText('Dark')).toBeInTheDocument();
      expect(screen.getByText('System')).toBeInTheDocument();
    });

    it('selects theme option and closes dropdown', () => {
      renderWithTheme(<ThemeToggle showDropdown />, 'dark');
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      const lightOption = screen.getByText('Light');
      fireEvent.click(lightOption);
      
      // Dropdown should close
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
      
      // Theme should change
      expect(document.documentElement.classList.contains('light')).toBe(true);
    });

    it('shows checkmark on current theme', () => {
      renderWithTheme(<ThemeToggle showDropdown />, 'dark');
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      // Dark option should have checkmark
      const darkOption = screen.getByText('Dark').closest('button');
      expect(darkOption).toHaveTextContent('✓');
    });

    it('closes dropdown when clicking outside', () => {
      const { container: _container } = renderWithTheme(
        <div>
          <ThemeToggle showDropdown />
          <div data-testid="outside">Outside</div>
        </div>
      );
      
      const button = screen.getByRole('button');
      fireEvent.click(button);
      
      expect(screen.getByRole('menu')).toBeInTheDocument();
      
      // Click outside
      fireEvent.mouseDown(screen.getByTestId('outside'));
      
      expect(screen.queryByRole('menu')).not.toBeInTheDocument();
    });
  });

  describe('custom className', () => {
    it('applies custom className', () => {
      renderWithTheme(<ThemeToggle className="custom-class" />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('custom-class');
    });
  });

  describe('accessibility', () => {
    it('is keyboard accessible', () => {
      renderWithTheme(<ThemeToggle />);
      
      const button = screen.getByRole('button');
      button.focus();
      
      expect(document.activeElement).toBe(button);
    });

    it('has focus visible styles', () => {
      renderWithTheme(<ThemeToggle />);
      
      const button = screen.getByRole('button');
      expect(button).toHaveClass('focus-visible:ring-2');
    });
  });
});
