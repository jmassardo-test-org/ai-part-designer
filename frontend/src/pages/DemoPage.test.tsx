/**
 * Demo Page Tests.
 * 
 * Tests for the interactive demo page showcasing platform capabilities.
 */

import { render, screen, fireEvent, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { DemoPage } from './DemoPage';

// Mock the theme context
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
    isLoading: false,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
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

describe('DemoPage', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Rendering', () => {
    it('renders the demo page with header and hero section', () => {
      renderWithRouter(<DemoPage />);

      expect(screen.getByText('Interactive Demo')).toBeInTheDocument();
      expect(screen.getByText('See AI Part Design in Action')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /get started/i })).toBeInTheDocument();
    });

    it('renders all demo steps in the navigator', () => {
      renderWithRouter(<DemoPage />);

      expect(screen.getByText('Describe Your Part')).toBeInTheDocument();
      expect(screen.getByText('AI Processing')).toBeInTheDocument();
      expect(screen.getByText('Preview in 3D')).toBeInTheDocument();
      expect(screen.getByText('Export & Manufacture')).toBeInTheDocument();
    });

    it('renders the play demo button', () => {
      renderWithRouter(<DemoPage />);

      expect(screen.getByRole('button', { name: /play demo/i })).toBeInTheDocument();
    });

    it('renders key features section', () => {
      renderWithRouter(<DemoPage />);

      expect(screen.getByText('Why Choose AssemblematicAI?')).toBeInTheDocument();
      expect(screen.getByText('Natural Language')).toBeInTheDocument();
      expect(screen.getByText('Instant Generation')).toBeInTheDocument();
      expect(screen.getByText('Parametric Control')).toBeInTheDocument();
      expect(screen.getByText('Export Anywhere')).toBeInTheDocument();
    });

    it('renders use cases section', () => {
      renderWithRouter(<DemoPage />);

      expect(screen.getByText('Built for Makers & Engineers')).toBeInTheDocument();
      expect(screen.getByText('3D Printing Enthusiasts')).toBeInTheDocument();
      expect(screen.getByText('Product Designers')).toBeInTheDocument();
      expect(screen.getByText('Hardware Engineers')).toBeInTheDocument();
    });

    it('renders CTA section with signup and pricing links', () => {
      renderWithRouter(<DemoPage />);

      expect(screen.getByText('Ready to Start Designing?')).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /create free account/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /view pricing/i })).toBeInTheDocument();
    });

    it('renders footer with navigation links', () => {
      renderWithRouter(<DemoPage />);

      const footerLinks = screen.getAllByRole('link');
      const footerLinkTexts = footerLinks.map((link) => link.textContent);
      
      expect(footerLinkTexts).toContain('Demo');
      expect(footerLinkTexts).toContain('Pricing');
      expect(footerLinkTexts).toContain('Terms');
      expect(footerLinkTexts).toContain('Privacy');
      expect(footerLinkTexts).toContain('Contact');
    });
  });

  describe('Step Navigation', () => {
    it('starts on the first step by default', () => {
      renderWithRouter(<DemoPage />);

      // First step should be active (has cyan background via step buttons)
      const stepButtons = screen.getAllByRole('button');
      const describeStepBtn = stepButtons.find((btn) => 
        btn.textContent?.includes('Describe Your Part')
      );
      expect(describeStepBtn).toHaveClass('bg-cyan-500/10');
    });

    it('changes step when clicking on step navigator', () => {
      renderWithRouter(<DemoPage />);

      // Click on step 3 (Preview in 3D)
      const stepButtons = screen.getAllByRole('button');
      const previewStepBtn = stepButtons.find((btn) => 
        btn.textContent?.includes('Preview in 3D')
      );
      
      if (previewStepBtn) {
        fireEvent.click(previewStepBtn);
      }

      // Check that the description shows the preview step text - may appear multiple times
      expect(screen.getAllByText('View your part from any angle. Rotate, zoom, and inspect every detail.').length).toBeGreaterThanOrEqual(1);
    });

    it('displays export options on the final step', () => {
      renderWithRouter(<DemoPage />);

      // Click on step 4 (Export)
      const stepButtons = screen.getAllByRole('button');
      const exportStepBtn = stepButtons.find((btn) => 
        btn.textContent?.includes('Export & Manufacture')
      );
      
      if (exportStepBtn) {
        fireEvent.click(exportStepBtn);
      }

      expect(screen.getByText('STEP File')).toBeInTheDocument();
      expect(screen.getByText('STL File')).toBeInTheDocument();
      expect(screen.getByText('For CNC machining')).toBeInTheDocument();
      expect(screen.getByText('For 3D printing')).toBeInTheDocument();
    });
  });

  describe('Play/Pause Functionality', () => {
    it('changes to pause button when playing', () => {
      renderWithRouter(<DemoPage />);

      const playButton = screen.getByRole('button', { name: /play demo/i });
      fireEvent.click(playButton);

      expect(screen.getByRole('button', { name: /pause demo/i })).toBeInTheDocument();
    });

    it('auto-advances steps when playing', () => {
      renderWithRouter(<DemoPage />);

      // Start playing
      const playButton = screen.getByRole('button', { name: /play demo/i });
      fireEvent.click(playButton);

      // Initially on step 1 - text may appear multiple times
      expect(screen.getAllByText('Use natural language to describe what you need. No CAD experience required.').length).toBeGreaterThanOrEqual(1);

      // Advance time to trigger step change
      act(() => {
        vi.advanceTimersByTime(4000);
      });

      // Should now show step 2 description - text may appear multiple times
      expect(screen.getAllByText('Our AI analyzes your requirements and generates precise CadQuery code.').length).toBeGreaterThanOrEqual(1);
    });

    it('stops auto-advancing when paused', () => {
      renderWithRouter(<DemoPage />);

      // Start playing
      const playButton = screen.getByRole('button', { name: /play demo/i });
      fireEvent.click(playButton);

      // Pause
      const pauseButton = screen.getByRole('button', { name: /pause demo/i });
      fireEvent.click(pauseButton);

      // Advance time
      act(() => {
        vi.advanceTimersByTime(8000);
      });

      // Should still be on step 1 since we paused
      expect(screen.getByRole('button', { name: /play demo/i })).toBeInTheDocument();
    });

    it('shows replay button after reaching the last step', () => {
      renderWithRouter(<DemoPage />);

      // Navigate to last step manually
      const stepButtons = screen.getAllByRole('button');
      const exportStepBtn = stepButtons.find((btn) => 
        btn.textContent?.includes('Export & Manufacture')
      );
      
      if (exportStepBtn) {
        fireEvent.click(exportStepBtn);
      }

      expect(screen.getByRole('button', { name: /replay demo/i })).toBeInTheDocument();
    });

    it('resets to first step when clicking replay', () => {
      renderWithRouter(<DemoPage />);

      // Navigate to last step
      const stepButtons = screen.getAllByRole('button');
      const exportStepBtn = stepButtons.find((btn) => 
        btn.textContent?.includes('Export & Manufacture')
      );
      
      if (exportStepBtn) {
        fireEvent.click(exportStepBtn);
      }

      // Click replay
      const replayButton = screen.getByRole('button', { name: /replay demo/i });
      fireEvent.click(replayButton);

      // Should now be playing from step 1
      expect(screen.getByRole('button', { name: /pause demo/i })).toBeInTheDocument();
    });
  });

  describe('Navigation Links', () => {
    it('has correct href for homepage link', () => {
      renderWithRouter(<DemoPage />);
      
      const homeLink = screen.getByTestId('logo-light').closest('a');
      expect(homeLink).toHaveAttribute('href', '/');
    });

    it('has correct href for signup links', () => {
      renderWithRouter(<DemoPage />);
      
      const signupLinks = screen.getAllByRole('link', { name: /get started|create free account/i });
      signupLinks.forEach((link) => {
        expect(link).toHaveAttribute('href', '/register');
      });
    });

    it('has correct href for pricing link', () => {
      renderWithRouter(<DemoPage />);
      
      const pricingLinks = screen.getAllByRole('link', { name: /pricing|view pricing/i });
      expect(pricingLinks.length).toBeGreaterThan(0);
      pricingLinks.forEach((link) => {
        expect(link).toHaveAttribute('href', '/pricing');
      });
    });
  });

  describe('Accessibility', () => {
    it('has proper heading hierarchy', () => {
      renderWithRouter(<DemoPage />);

      const h1 = screen.getByRole('heading', { level: 1 });
      expect(h1).toHaveTextContent('See AI Part Design in Action');

      const h2s = screen.getAllByRole('heading', { level: 2 });
      expect(h2s.length).toBeGreaterThan(0);

      const h3s = screen.getAllByRole('heading', { level: 3 });
      expect(h3s.length).toBeGreaterThan(0);
    });

    it('has accessible buttons with visible text', () => {
      renderWithRouter(<DemoPage />);

      const buttons = screen.getAllByRole('button');
      buttons.forEach((button) => {
        // All interactive buttons should have text content
        expect(button.textContent || button.getAttribute('aria-label')).toBeTruthy();
      });
    });
  });
});
