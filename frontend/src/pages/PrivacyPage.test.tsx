/**
 * Privacy Policy Page Tests.
 */

import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect } from 'vitest';
import { PrivacyPage } from './PrivacyPage';

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

describe('PrivacyPage', () => {
  describe('Rendering', () => {
    it('renders the privacy page with header', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('Privacy Policy')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /get started/i })).toBeInTheDocument();
    });

    it('displays last updated date', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText(/Last updated:/)).toBeInTheDocument();
    });

    it('renders table of contents', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('Contents')).toBeInTheDocument();
      // These texts appear in both TOC and section headers, use getAllByText
      expect(screen.getAllByText('1. Overview').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('4. AI Data Processing').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('13. Contact Us').length).toBeGreaterThanOrEqual(1);
    });

    it('displays privacy commitment message', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('Your Privacy Matters')).toBeInTheDocument();
    });
  });

  describe('Data Collection Section', () => {
    it('explains what data is collected', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('Information You Provide')).toBeInTheDocument();
      // Verify the section contains account information text
      const matches = screen.queryAllByText((_content, element) => {
        const text = element?.textContent || '';
        return text.includes('Account Information') && element?.tagName === 'LI';
      });
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });

    it('explains automatic data collection', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('Information We Collect Automatically')).toBeInTheDocument();
      expect(screen.getByText(/Usage Data:/)).toBeInTheDocument();
      expect(screen.getByText(/Device Information:/)).toBeInTheDocument();
    });
  });

  describe('AI Data Processing Section', () => {
    it('explains Ollama data processing', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('Ollama (Self-Hosted Models)')).toBeInTheDocument();
      expect(screen.getByText(/Runs on our secure servers/)).toBeInTheDocument();
    });

    it('explains OpenAI data processing', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('OpenAI API (When Used)')).toBeInTheDocument();
      expect(screen.getByText(/Enterprise Data Processing Agreement/)).toBeInTheDocument();
    });

    it('states data is not used for training', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText(/never use your designs.*to train any AI models/)).toBeInTheDocument();
    });
  });

  describe('User Rights Section (GDPR/CCPA)', () => {
    it('displays user rights cards', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('Right to Access')).toBeInTheDocument();
      expect(screen.getByText('Right to Rectification')).toBeInTheDocument();
      expect(screen.getByText('Right to Deletion')).toBeInTheDocument();
      expect(screen.getByText('Right to Portability')).toBeInTheDocument();
      expect(screen.getByText('Right to Restrict')).toBeInTheDocument();
      expect(screen.getByText('Right to Object')).toBeInTheDocument();
    });

    it('mentions CCPA rights for California residents', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText('California Residents (CCPA)')).toBeInTheDocument();
      expect(screen.getByText(/Right to know what personal information is collected/)).toBeInTheDocument();
    });

    it('states personal information is not sold', () => {
      renderWithRouter(<PrivacyPage />);

      // Text is split across elements, use getAllByText with function matcher
      expect(screen.getAllByText((_content, element) => 
        element?.textContent?.toLowerCase().includes('do not sell') || false
      ).length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Security Section', () => {
    it('explains security measures', () => {
      renderWithRouter(<PrivacyPage />);

      expect(screen.getByText(/Encryption:/)).toBeInTheDocument();
      expect(screen.getByText(/Access Controls:/)).toBeInTheDocument();
      expect(screen.getByText(/TLS 1.3.*AES-256/)).toBeInTheDocument();
    });
  });

  describe('Data Retention Section', () => {
    it('explains data retention periods', () => {
      renderWithRouter(<PrivacyPage />);

      // Text is within strong elements, use queryAllByText to find at least one match
      const matches = screen.queryAllByText((_content, element) => {
        const text = element?.textContent || '';
        return text.includes('Account Data') && element?.tagName === 'LI';
      });
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Contact Information', () => {
    it('displays Data Protection Officer contact', () => {
      renderWithRouter(<PrivacyPage />);

      // Multiple mentions of DPO, use getAllByText
      expect(screen.getAllByText((_content, element) => 
        element?.textContent?.includes('Data Protection Officer') || false
      ).length).toBeGreaterThanOrEqual(1);
    });
  });

  describe('Footer', () => {
    it('renders footer with navigation links', () => {
      renderWithRouter(<PrivacyPage />);

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
      renderWithRouter(<PrivacyPage />);

      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toHaveTextContent('Privacy Policy');

      const h2s = screen.getAllByRole('heading', { level: 2 });
      expect(h2s.length).toBeGreaterThan(0);
    });

    it('has anchor links for navigation', () => {
      renderWithRouter(<PrivacyPage />);

      const tocLinks = screen.getAllByRole('link');
      const anchorLinks = tocLinks.filter(link => 
        link.getAttribute('href')?.startsWith('#')
      );
      
      expect(anchorLinks.length).toBeGreaterThan(0);
    });
  });
});
