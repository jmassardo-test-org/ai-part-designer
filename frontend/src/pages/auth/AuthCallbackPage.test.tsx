/**
 * Tests for AuthCallbackPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AuthCallbackPage } from './AuthCallbackPage';

// Mock AuthContext
const mockRefreshUser = vi.fn();
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    refreshUser: mockRefreshUser,
  }),
}));

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

const renderWithRouter = (searchParams = '') => {
  return render(
    <MemoryRouter initialEntries={[`/auth/callback${searchParams}`]}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/dashboard" element={<div>Dashboard</div>} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('AuthCallbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    mockRefreshUser.mockResolvedValue(undefined);
  });

  describe('Successful authentication', () => {
    it('stores tokens in localStorage', async () => {
      renderWithRouter('?access_token=test-access&refresh_token=test-refresh');

      await waitFor(() => {
        expect(localStorageMock.setItem).toHaveBeenCalledWith('access_token', 'test-access');
        expect(localStorageMock.setItem).toHaveBeenCalledWith('refresh_token', 'test-refresh');
      });
    });

    it('shows welcome back message for returning user', async () => {
      renderWithRouter('?access_token=test-access&refresh_token=test-refresh');

      await waitFor(() => {
        expect(screen.getByText(/welcome back/i)).toBeInTheDocument();
      });
    });

    it('shows new user welcome message', async () => {
      renderWithRouter('?access_token=test-access&refresh_token=test-refresh&is_new_user=true');

      await waitFor(() => {
        expect(screen.getByText(/welcome to assemblematic/i)).toBeInTheDocument();
      });
    });

    it('refreshes user data after successful login', async () => {
      renderWithRouter('?access_token=test-access&refresh_token=test-refresh');

      await waitFor(() => {
        expect(mockRefreshUser).toHaveBeenCalled();
      });
    });

    it('shows success message with redirect info', async () => {
      renderWithRouter('?access_token=test-access&refresh_token=test-refresh');

      await waitFor(() => {
        expect(screen.getByText(/redirecting/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error handling', () => {
    it('handles generic OAuth error', async () => {
      renderWithRouter('?error=oauth_error&message=Something+went+wrong');

      await waitFor(() => {
        expect(screen.getByText(/oauth provider error/i)).toBeInTheDocument();
        expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      });
    });

    it('handles access denied error', async () => {
      renderWithRouter('?error=access_denied');

      await waitFor(() => {
        expect(screen.getByText(/access denied/i)).toBeInTheDocument();
        expect(screen.getByText(/cancelled/i)).toBeInTheDocument();
      });
    });

    it('handles server error code', async () => {
      renderWithRouter('?error=server_error');

      await waitFor(() => {
        expect(screen.getByText('Server Error')).toBeInTheDocument();
      });
    });

    it('handles email conflict error', async () => {
      renderWithRouter('?error=email_conflict');

      await waitFor(() => {
        expect(screen.getByText(/account already exists/i)).toBeInTheDocument();
      });
    });

    it('handles provider unavailable error', async () => {
      renderWithRouter('?error=provider_unavailable');

      await waitFor(() => {
        expect(screen.getByText(/provider unavailable/i)).toBeInTheDocument();
      });
    });

    it('handles missing tokens as server error', async () => {
      renderWithRouter('?access_token=test-access'); // Missing refresh token

      await waitFor(() => {
        expect(screen.getByText('Server Error')).toBeInTheDocument();
      });
    });

    it('shows retry button on error', async () => {
      renderWithRouter('?error=oauth_error');

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
      });
    });

    it('shows email sign-in link on error', async () => {
      renderWithRouter('?error=oauth_error');

      await waitFor(() => {
        expect(screen.getByRole('link', { name: /sign in with email/i })).toBeInTheDocument();
      });
    });

    it('navigates to login on retry button click', async () => {
      const user = userEvent.setup();
      renderWithRouter('?error=oauth_error');

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
      });

      const retryButton = screen.getByRole('button', { name: /try again/i });
      await user.click(retryButton);

      await waitFor(() => {
        expect(screen.getByText('Login Page')).toBeInTheDocument();
      });
    });

    it('handles unknown error code gracefully', async () => {
      renderWithRouter('?error=unknown_error_code');

      await waitFor(() => {
        expect(screen.getByText(/authentication failed/i)).toBeInTheDocument();
      });
    });

    it('displays error detail message when provided', async () => {
      renderWithRouter('?error=oauth_error&message=Custom+error+detail');

      await waitFor(() => {
        expect(screen.getByText(/custom error detail/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error during token processing', () => {
    it('handles refreshUser failure', async () => {
      mockRefreshUser.mockRejectedValue(new Error('Failed to refresh'));

      renderWithRouter('?access_token=test-access&refresh_token=test-refresh');

      await waitFor(() => {
        expect(screen.getByText('Server Error')).toBeInTheDocument();
      });
    });
  });
});
