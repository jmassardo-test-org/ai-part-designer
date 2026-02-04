/**
 * Terms of Service Page Tests.
 */

import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect } from 'vitest';
import { TermsPage } from './TermsPage';

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
const renderWithRouter = (ui: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {ui}
    </BrowserRouter>
  );
};

describe('TermsPage', () => {
  describe('Rendering', () => {
    it('renders the terms page with header', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getByText('Terms of Service')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /get started/i })).toBeInTheDocument();
    });

    it('displays last updated date', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });

    it('renders table of contents', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getByText('Contents')).toBeInTheDocument();
      // These texts appear in both TOC and section headers, use getAllByText
      expect(screen.getAllByText('1. Acceptance of Terms').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('2. AI Technology Disclosure').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('11. Contact Us').length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('AI Disclosure Section', () => {
    it('renders AI technology disclosure section', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getByText('Important AI Disclosure')).toBeInTheDocument();
      expect(screen.getByText('AI Models Used')).toBeInTheDocument();
    });

    it('lists AI models used', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getByText(/Ollama \(Local Models\)/)).toBeInTheDocument();
      expect(screen.getByText(/OpenAI API/)).toBeInTheDocument();
      expect(screen.getByText(/CadQuery/)).toBeInTheDocument();
    });

    it('explains AI limitations', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getByText('AI Limitations')).toBeInTheDocument();
      expect(screen.getByText(/AI-generated outputs may contain errors/)).toBeInTheDocument();
    });

    it('states data is not used for training', () => {
      renderWithRouter(<TermsPage />);

      // The text is split by <strong> tag, so find the paragraph that contains this info
      // Use queryAllByText to find all matching elements and verify at least one exists
      const matches = screen.queryAllByText((content, element) => {
        const text = element?.textContent || '';
        return text.includes('NOT') && text.includes('use your designs') && element?.tagName === 'P';
      });
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Key Sections', () => {
    it('renders account terms section', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getAllByText(/3. Account Terms/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders acceptable use section', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getAllByText(/4. Acceptable Use/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders intellectual property section', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getAllByText(/5. Intellectual Property/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders subscriptions section', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getAllByText(/6. Subscriptions & Billing/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders liability section', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getAllByText(/7. Limitation of Liability/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders termination section', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getAllByText(/9. Termination/).length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Contact Information', () => {
    it('displays contact information', () => {
      renderWithRouter(<TermsPage />);

      expect(screen.getByText('AssemblematicAI Legal Team')).toBeInTheDocument();
      expect(screen.getByText(/legal@assemblematicai.com/)).toBeInTheDocument();
    });
  });

  describe('Footer', () => {
    it('renders footer with navigation links', () => {
      renderWithRouter(<TermsPage />);

      const footerLinks = screen.getAllByRole('link');
      const linkTexts = footerLinks.map(link => link.textContent);

      expect(linkTexts).toContain('Demo');
      expect(linkTexts).toContain('Pricing');
      expect(linkTexts).toContain('Terms');
      expect(linkTexts).toContain('Privacy');
      expect(linkTexts).toContain('Contact');
    });
  });

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      renderWithRouter(<TermsPage />);

      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toHaveTextContent('Terms of Service');

      const h2s = screen.getAllByRole('heading', { level: 2 });
      expect(h2s.length).toBeGreaterThan(0);
    });

    it('has anchor links for navigation', () => {
      renderWithRouter(<TermsPage />);

      const tocLinks = screen.getAllByRole('link');
      const anchorLinks = tocLinks.filter(link => 
        link.getAttribute('href')?.startsWith('#')
      );
      
      expect(anchorLinks.length).toBeGreaterThan(0);
    });
  });
});
