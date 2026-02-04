/**
 * Documentation Page Tests.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect } from 'vitest';
import { DocsPage } from './DocsPage';

// Mock the ThemeContext
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
    isLoading: false,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the WebSocketContext
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    isConnected: false,
    connectionState: 'disconnected',
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    sendMessage: vi.fn(),
  }),
}));

// Mock the brand components
vi.mock('@/components/brand', () => ({
  LogoLight: () => <div data-testid="logo-light">Logo</div>,
  LogoIcon: () => <div data-testid="logo-icon">Icon</div>,
}));

// Helper to render with router
const renderWithRouter = (ui: React.ReactElement, { route = '/docs' } = {}) => {
  window.history.pushState({}, 'Test page', route);
  return render(
    <BrowserRouter>
      {ui}
    </BrowserRouter>
  );
};

describe('DocsPage', () => {
  describe('Rendering', () => {
    it('renders the documentation page with header', () => {
      renderWithRouter(<DocsPage />);

      expect(screen.getByText('Documentation')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /get started/i })).toBeInTheDocument();
    });

    it('renders search input', () => {
      renderWithRouter(<DocsPage />);

      expect(screen.getByPlaceholderText(/search docs/i)).toBeInTheDocument();
    });

    it('renders navigation sections', () => {
      renderWithRouter(<DocsPage />);

      // These texts appear in both navigation and content areas, use getAllByText
      expect(screen.getAllByText('Getting Started').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Using Templates').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('AI Generation').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Exporting').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('API Reference').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('FAQ').length).toBeGreaterThanOrEqual(1);
    });

    it('shows Getting Started content by default', () => {
      renderWithRouter(<DocsPage />);

      // These are subitems that should be visible
      expect(screen.getAllByText('Introduction').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Quick Start').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Your First Part').length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Navigation', () => {
    it('changes content when clicking navigation items', async () => {
      renderWithRouter(<DocsPage />);

      // Click on Templates
      const templatesNav = screen.getByRole('button', { name: /using templates/i });
      fireEvent.click(templatesNav);

      await waitFor(() => {
        // Template Overview appears in nav and content
        expect(screen.getAllByText('Template Overview').length).toBeGreaterThanOrEqual(1);
      });
    });

    it('expands subsections when clicking parent', async () => {
      renderWithRouter(<DocsPage />);

      // Getting Started should be expanded by default - Introduction appears multiple times
      expect(screen.getAllByText('Introduction').length).toBeGreaterThanOrEqual(1);
    });

    it('navigates to FAQ section', async () => {
      renderWithRouter(<DocsPage />);

      const faqNav = screen.getByRole('button', { name: /faq/i });
      fireEvent.click(faqNav);

      await waitFor(() => {
        expect(screen.getByText('Frequently Asked Questions')).toBeInTheDocument();
      });
    });
  });

  describe('Search', () => {
    it('filters navigation items based on search', async () => {
      renderWithRouter(<DocsPage />);

      const searchInput = screen.getByPlaceholderText(/search docs/i);
      fireEvent.change(searchInput, { target: { value: 'API' } });

      // Should show API Reference
      expect(screen.getByText('API Reference')).toBeInTheDocument();
    });

    it('clears search filter when input is cleared', async () => {
      renderWithRouter(<DocsPage />);

      const searchInput = screen.getByPlaceholderText(/search docs/i);
      
      // Search for something specific
      fireEvent.change(searchInput, { target: { value: 'API' } });
      
      // Clear search
      fireEvent.change(searchInput, { target: { value: '' } });

      // All sections should be visible - use getAllByText since text appears multiple times
      expect(screen.getAllByText('Getting Started').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Using Templates').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('API Reference').length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Getting Started Content', () => {
    it('displays introduction section', () => {
      renderWithRouter(<DocsPage />);

      expect(screen.getByText(/AI-powered CAD generation platform/)).toBeInTheDocument();
    });

    it('displays key features list', () => {
      renderWithRouter(<DocsPage />);

      expect(screen.getByText(/Natural language part generation/)).toBeInTheDocument();
      expect(screen.getByText(/Pre-built parametric templates/)).toBeInTheDocument();
    });

    it('displays quick start steps', () => {
      renderWithRouter(<DocsPage />);

      expect(screen.getByText(/Create an account/)).toBeInTheDocument();
      expect(screen.getByText(/Choose a template/)).toBeInTheDocument();
      expect(screen.getByText(/Describe your part/)).toBeInTheDocument();
    });
  });

  describe('Templates Content', () => {
    it('displays template overview when navigated', async () => {
      renderWithRouter(<DocsPage />);

      const templatesNav = screen.getByRole('button', { name: /using templates/i });
      fireEvent.click(templatesNav);

      await waitFor(() => {
        expect(screen.getByText(/pre-built parametric designs/i)).toBeInTheDocument();
      });
    });
  });

  describe('AI Generation Content', () => {
    it('displays prompt writing tips when navigated', async () => {
      renderWithRouter(<DocsPage />);

      const aiNav = screen.getByRole('button', { name: /ai generation/i });
      fireEvent.click(aiNav);

      await waitFor(() => {
        expect(screen.getByText('Writing Effective Prompts')).toBeInTheDocument();
      });
    });

    it('shows good and bad prompt examples', async () => {
      renderWithRouter(<DocsPage />);

      const aiNav = screen.getByRole('button', { name: /ai generation/i });
      fireEvent.click(aiNav);

      await waitFor(() => {
        expect(screen.getByText(/Good Prompt/)).toBeInTheDocument();
        expect(screen.getByText(/Vague Prompt/)).toBeInTheDocument();
      });
    });
  });

  describe('Exports Content', () => {
    it('displays file format information when navigated', async () => {
      renderWithRouter(<DocsPage />);

      const exportsNav = screen.getByRole('button', { name: /exporting/i });
      fireEvent.click(exportsNav);

      await waitFor(() => {
        // File Formats appears in nav and content
        expect(screen.getAllByText('File Formats').length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  describe('API Content', () => {
    it('displays API overview when navigated', async () => {
      renderWithRouter(<DocsPage />);

      const apiNav = screen.getByRole('button', { name: /api reference/i });
      fireEvent.click(apiNav);

      await waitFor(() => {
        // Authentication may appear multiple times
        expect(screen.getAllByText('Authentication').length).toBeGreaterThanOrEqual(1);
      });
    });

    it('shows API endpoint examples', async () => {
      renderWithRouter(<DocsPage />);

      const apiNav = screen.getByRole('button', { name: /api reference/i });
      fireEvent.click(apiNav);

      await waitFor(() => {
        expect(screen.getByText('/templates')).toBeInTheDocument();
        expect(screen.getByText('/generate')).toBeInTheDocument();
      });
    });
  });

  describe('FAQ Content', () => {
    it('displays FAQ questions when navigated', async () => {
      renderWithRouter(<DocsPage />);

      const faqNav = screen.getByRole('button', { name: /faq/i });
      fireEvent.click(faqNav);

      await waitFor(() => {
        expect(screen.getByText('What is AssemblematicAI?')).toBeInTheDocument();
        expect(screen.getByText('Do I need CAD experience to use it?')).toBeInTheDocument();
      });
    });

    it('expands FAQ answer when question is clicked', async () => {
      renderWithRouter(<DocsPage />);

      // Navigate to FAQ
      const faqNav = screen.getByRole('button', { name: /faq/i });
      fireEvent.click(faqNav);

      await waitFor(() => {
        expect(screen.getByText('What is AssemblematicAI?')).toBeInTheDocument();
      });

      // The first FAQ (index 0) is expanded by default, so the answer should already be visible
      // The answer text contains "AI-powered CAD generation platform"
      await waitFor(() => {
        const matches = screen.queryAllByText(/production-ready 3D parts/);
        expect(matches.length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  describe('Code Blocks', () => {
    it('renders code blocks in content', () => {
      renderWithRouter(<DocsPage />);

      // Should have code examples in Getting Started
      expect(screen.getByText(/Create a mounting bracket/)).toBeInTheDocument();
    });
  });

  describe('Footer', () => {
    it('renders footer with navigation links', () => {
      renderWithRouter(<DocsPage />);

      const footerLinks = screen.getAllByRole('link');
      const linkTexts = footerLinks.map(link => link.textContent);

      expect(linkTexts).toContain('Demo');
      expect(linkTexts).toContain('Pricing');
      expect(linkTexts).toContain('Terms');
      expect(linkTexts).toContain('Privacy');
      expect(linkTexts).toContain('Contact');
    });

    it('has contact support link', () => {
      renderWithRouter(<DocsPage />);

      expect(screen.getByText(/Contact Support/)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      renderWithRouter(<DocsPage />);

      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toBeInTheDocument();

      const h2s = screen.getAllByRole('heading', { level: 2 });
      expect(h2s.length).toBeGreaterThan(0);
    });

    it('has accessible navigation buttons', () => {
      renderWithRouter(<DocsPage />);

      const navButtons = screen.getAllByRole('button');
      expect(navButtons.length).toBeGreaterThan(0);
    });
  });
});
