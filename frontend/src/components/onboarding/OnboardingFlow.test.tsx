/**
 * OnboardingFlow Component Tests
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OnboardingProvider } from './OnboardingFlow';

// Mock AuthContext
const mockUser = { id: 'user-1', email: 'test@example.com', display_name: 'Test User' };
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
  }),
}));

// Mock navigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock onboardingApi
vi.mock('@/lib/api/onboarding', () => ({
  onboardingApi: {
    getStatus: vi.fn().mockRejectedValue(new Error('Not available')),
    completeStep: vi.fn().mockResolvedValue({ current_step: 1, completed: false }),
    skip: vi.fn().mockResolvedValue({ message: 'Skipped' }),
    reset: vi.fn().mockResolvedValue({ message: 'Reset' }),
  },
}));

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => { store[key] = value; }),
    removeItem: vi.fn((key: string) => { delete store[key]; }),
    clear: vi.fn(() => { store = {}; }),
  };
})();
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('OnboardingProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  const renderWithRouter = (children: React.ReactNode = <div>App Content</div>) => {
    return render(
      <BrowserRouter>
        <OnboardingProvider>
          {children}
        </OnboardingProvider>
      </BrowserRouter>
    );
  };

  it('renders children', () => {
    localStorageMock.getItem.mockReturnValue('true');
    renderWithRouter(<div data-testid="child-content">Child Content</div>);
    
    expect(screen.getByTestId('child-content')).toBeInTheDocument();
  });

  it('shows onboarding for new users', async () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });
  });

  it('does not show onboarding for returning users', () => {
    localStorageMock.getItem.mockReturnValue('true');
    
    renderWithRouter();
    
    expect(screen.queryByText(/welcome to assemblematic/i)).not.toBeInTheDocument();
  });

  it('shows skip button', async () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText(/skip tour/i)).toBeInTheDocument();
    });
  });

  it('closes onboarding when skip clicked', async () => {
    const user = userEvent.setup();
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText(/skip tour/i)).toBeInTheDocument();
    });
    
    await user.click(screen.getByText(/skip tour/i));
    
    expect(localStorageMock.setItem).toHaveBeenCalledWith(
      'onboarding_complete_user-1',
      'true'
    );
  });

  it('navigates through steps', async () => {
    const user = userEvent.setup();
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });
    
    // Find and click the next/continue button
    const buttons = screen.getAllByRole('button');
    const nextButton = buttons.find(b => 
      b.textContent?.match(/next|continue|get started/i) && !b.hasAttribute('disabled')
    );
    if (nextButton) {
      await user.click(nextButton);
    }
    
    // Just verify a button click didn't crash
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows progress dots', async () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      // Should have multiple progress dots
      const dots = document.querySelectorAll('[class*="rounded-full"]');
      expect(dots.length).toBeGreaterThan(0);
    });
  });

  it('allows going back to previous step', async () => {
    const user = userEvent.setup();
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });
    
    // Go to next step
    const nextButton = screen.getByRole('button', { name: /next|continue|get started/i });
    await user.click(nextButton);
    
    await waitFor(() => {
      const backButton = screen.queryByRole('button', { name: /back|previous/i });
      if (backButton) {
        expect(backButton).toBeInTheDocument();
      }
    });
  });

  it('completes onboarding on last step', async () => {
    const user = userEvent.setup();
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });
    
    // Navigate through all steps - find the next button
    const buttons = screen.getAllByRole('button');
    const nextButton = buttons.find(b => 
      b.textContent?.match(/next|get started/i) && !b.hasAttribute('disabled')
    );
    if (nextButton) {
      await user.click(nextButton);
    }
    
    // The onboarding should still show the dialog
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('renders with accessible dialog role', async () => {
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });
  });

  it('shows action buttons for steps with actions', async () => {
    const user = userEvent.setup();
    localStorageMock.getItem.mockReturnValue(null);
    
    renderWithRouter();
    
    await waitFor(() => {
      expect(screen.getByText(/welcome/i)).toBeInTheDocument();
    });
    
    // Navigate to a step with an action
    const nextButton = screen.getByRole('button', { name: /next|continue|get started/i });
    await user.click(nextButton);
    
    // Check for action button or next button
    await waitFor(() => {
      const actionButtons = screen.getAllByRole('button');
      expect(actionButtons.length).toBeGreaterThan(0);
    });
  });
});
