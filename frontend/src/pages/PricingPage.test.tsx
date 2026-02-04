/**
 * PricingPage Tests.
 *
 * Tests for the pricing page including plan display, billing toggle,
 * and checkout initiation.
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import * as subscriptionsApi from '@/lib/api/subscriptions';
import PricingPage from './PricingPage';

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

// Mock the subscriptions API
vi.mock('@/lib/api/subscriptions', async () => {
  const actual = await vi.importActual('@/lib/api/subscriptions');
  return {
    ...actual,
    subscriptionsApi: {
      getPlans: vi.fn(),
      redirectToCheckout: vi.fn(),
    },
  };
});

// Mock the useAuth hook
const mockUser = { id: '1', email: 'test@test.com', tier: 'free' };
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
  }),
}));

// Mock plans data
const mockPlans = [
  {
    slug: 'free',
    name: 'Free',
    description: 'Get started with AssemblematicAI',
    monthly_credits: 10,
    max_concurrent_jobs: 1,
    max_storage_gb: 1,
    max_projects: 3,
    max_designs_per_project: 10,
    max_file_size_mb: 10,
    features: {
      ai_generation: true,
      export_2d: false,
      collaboration: false,
      priority_queue: false,
      custom_templates: false,
      api_access: false,
    },
    price_monthly: 0,
    price_yearly: 0,
    stripe_price_id_monthly: null,
    stripe_price_id_yearly: null,
  },
  {
    slug: 'pro',
    name: 'Pro',
    description: 'For professionals and power users',
    monthly_credits: 100,
    max_concurrent_jobs: 5,
    max_storage_gb: 50,
    max_projects: -1,
    max_designs_per_project: -1,
    max_file_size_mb: 100,
    features: {
      ai_generation: true,
      export_2d: true,
      collaboration: false,
      priority_queue: true,
      custom_templates: true,
      api_access: false,
    },
    price_monthly: 19,
    price_yearly: 190,
    stripe_price_id_monthly: 'price_pro_monthly',
    stripe_price_id_yearly: 'price_pro_yearly',
  },
  {
    slug: 'enterprise',
    name: 'Enterprise',
    description: 'For teams and organizations',
    monthly_credits: 1000,
    max_concurrent_jobs: 20,
    max_storage_gb: 500,
    max_projects: -1,
    max_designs_per_project: -1,
    max_file_size_mb: 500,
    features: {
      ai_generation: true,
      export_2d: true,
      collaboration: true,
      priority_queue: true,
      custom_templates: true,
      api_access: true,
    },
    price_monthly: 99,
    price_yearly: 990,
    stripe_price_id_monthly: 'price_enterprise_monthly',
    stripe_price_id_yearly: 'price_enterprise_yearly',
  },
];

const renderPage = () => {
  return render(
    <MemoryRouter>
      <PricingPage />
    </MemoryRouter>
  );
};

describe('PricingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (subscriptionsApi.subscriptionsApi.getPlans as any).mockResolvedValue(mockPlans);
  });

  describe('Plan Display', () => {
    it('renders loading state initially', () => {
      renderPage();
      expect(document.querySelector('.animate-spin')).toBeTruthy();
    });

    it('renders all three plans after loading', async () => {
      renderPage();

      await waitFor(() => {
        // Look for plan names in headings
        expect(screen.getAllByText('Free').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Pro').length).toBeGreaterThanOrEqual(1);
        expect(screen.getAllByText('Enterprise').length).toBeGreaterThanOrEqual(1);
      });
    });

    it('displays plan descriptions', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Get started with AssemblematicAI')).toBeInTheDocument();
        expect(screen.getByText('For professionals and power users')).toBeInTheDocument();
      });
    });

    it('shows "Most Popular" badge on Pro plan', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Most Popular')).toBeInTheDocument();
      });
    });

    it('displays monthly prices by default', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('$0')).toBeInTheDocument();
        expect(screen.getByText('$19')).toBeInTheDocument();
      });
    });

    it('displays plan limits correctly', async () => {
      renderPage();

      await waitFor(() => {
        // Check for some limits
        expect(screen.getByText('10')).toBeInTheDocument(); // Free credits
        expect(screen.getByText('1 GB')).toBeInTheDocument(); // Free storage
      });
    });
  });

  describe('Billing Toggle', () => {
    it('renders monthly/yearly toggle', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Monthly')).toBeInTheDocument();
        expect(screen.getByText(/Yearly/)).toBeInTheDocument();
      });
    });

    it('shows yearly savings badge', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/Save 20%/i)).toBeInTheDocument();
      });
    });
  });

  describe('Current Plan Highlighting', () => {
    it('highlights current plan for logged-in user', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Current Plan')).toBeInTheDocument();
      });
    });

    it('shows disabled button for current tier', async () => {
      renderPage();

      await waitFor(() => {
        const currentPlanButtons = screen.getAllByRole('button', { name: /current plan/i });
        expect(currentPlanButtons.length).toBeGreaterThan(0);
        expect(currentPlanButtons[0]).toBeDisabled();
      });
    });

    it('shows upgrade button for higher tiers', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /upgrade to pro/i })).toBeInTheDocument();
      });
    });
  });

  describe('Checkout Flow', () => {
    it('shows "Contact Sales" for Enterprise tier', async () => {
      renderPage();

      await waitFor(() => {
        // Contact Sales link may appear multiple times
        expect(screen.getAllByRole('link', { name: /contact sales/i }).length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  describe('Feature Comparison', () => {
    it('renders feature comparison table', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Compare Features')).toBeInTheDocument();
      });
    });

    it('shows feature names', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('AI Part Generation')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when API fails', async () => {
      (subscriptionsApi.subscriptionsApi.getPlans as any).mockRejectedValue(new Error('API Error'));

      renderPage();

      await waitFor(() => {
        expect(screen.getByText(/failed to load pricing plans/i)).toBeInTheDocument();
      }, { timeout: 3000 });
    });
  });

  describe('FAQ Section', () => {
    it('renders FAQ section', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Frequently Asked Questions')).toBeInTheDocument();
      });
    });

    it('displays FAQ questions', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('What file formats can I export?')).toBeInTheDocument();
        expect(screen.getByText('Can I cancel my subscription anytime?')).toBeInTheDocument();
        expect(screen.getByText('What AI models power the generation?')).toBeInTheDocument();
      });
    });

    it('expands FAQ answer when question is clicked', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('What file formats can I export?')).toBeInTheDocument();
      });

      // Click on the first FAQ question
      const firstQuestion = screen.getByText('What file formats can I export?');
      fireEvent.click(firstQuestion);

      // Answer should now be visible
      expect(screen.getByText(/We support STEP files for CNC machining/)).toBeInTheDocument();
    });

    it('collapses FAQ answer when clicked again', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('What file formats can I export?')).toBeInTheDocument();
      });

      const firstQuestion = screen.getByText('What file formats can I export?');
      
      // Open
      fireEvent.click(firstQuestion);
      expect(screen.getByText(/We support STEP files/)).toBeInTheDocument();

      // Close
      fireEvent.click(firstQuestion);
      expect(screen.queryByText(/We support STEP files/)).not.toBeInTheDocument();
    });

    it('only shows one expanded FAQ at a time', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('What file formats can I export?')).toBeInTheDocument();
      });

      // Open first FAQ
      const firstQuestion = screen.getByText('What file formats can I export?');
      fireEvent.click(firstQuestion);
      expect(screen.getByText(/We support STEP files/)).toBeInTheDocument();

      // Open second FAQ - first should close
      const secondQuestion = screen.getByText('Can I cancel my subscription anytime?');
      fireEvent.click(secondQuestion);
      
      // Second answer visible
      expect(screen.getByText(/You can cancel your subscription at any time/)).toBeInTheDocument();
      // First answer should be hidden
      expect(screen.queryByText(/We support STEP files/)).not.toBeInTheDocument();
    });
  });

  describe('Navigation and CTA', () => {
    it('renders header with logo and navigation links', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /sign in/i })).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /get started/i })).toBeInTheDocument();
      });
    });

    it('renders CTA section with signup button', async () => {
      renderPage();

      await waitFor(() => {
        expect(screen.getByText('Ready to get started?')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /start free trial/i })).toBeInTheDocument();
      });
    });

    it('renders footer with navigation links', async () => {
      renderPage();

      await waitFor(() => {
        const footerLinks = screen.getAllByRole('link');
        const linkTexts = footerLinks.map(link => link.textContent);
        
        expect(linkTexts).toContain('Demo');
        expect(linkTexts).toContain('Terms');
        expect(linkTexts).toContain('Privacy');
        expect(linkTexts).toContain('Contact');
      });
    });
  });
});
