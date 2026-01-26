/**
 * Tests for ResetPasswordPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AxiosError } from 'axios';
import { ResetPasswordPage } from './ResetPasswordPage';

// Mock auth API
vi.mock('@/lib/auth', () => ({
  authApi: {
    resetPassword: vi.fn(),
  },
}));

import { authApi } from '@/lib/auth';

const renderResetPasswordPage = (token: string | null = 'valid-token') => {
  const initialEntry = token ? `/reset-password?token=${token}` : '/reset-password';
  
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
        <Route path="/forgot-password" element={<div>Forgot Password Page</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders reset password form with valid token', () => {
    renderResetPasswordPage();

    expect(screen.getByRole('heading', { name: /set new password/i })).toBeInTheDocument();
  });

  it('shows password input fields', () => {
    renderResetPasswordPage();

    expect(screen.getByLabelText(/new password/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it('shows reset button', () => {
    renderResetPasswordPage();

    expect(screen.getByRole('button', { name: /reset password/i })).toBeInTheDocument();
  });

  it('shows invalid token message when no token provided', () => {
    renderResetPasswordPage(null);

    expect(screen.getByText(/invalid reset link/i)).toBeInTheDocument();
  });

  it('shows request new link button for invalid token', () => {
    renderResetPasswordPage(null);

    expect(screen.getByRole('link', { name: /request new link/i })).toHaveAttribute('href', '/forgot-password');
  });

  it('validates password length', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'short');
    await user.type(confirmInput, 'short');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it('validates password has lowercase letter', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'PASSWORD123!');
    await user.type(confirmInput, 'PASSWORD123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/lowercase/i)).toBeInTheDocument();
    });
  });

  it('validates password has uppercase letter', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'password123!');
    await user.type(confirmInput, 'password123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/uppercase/i)).toBeInTheDocument();
    });
  });

  it('validates password has number', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'Password!');
    await user.type(confirmInput, 'Password!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/number/i)).toBeInTheDocument();
    });
  });

  it('validates password has special character', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'Password123');
    await user.type(confirmInput, 'Password123');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/special character/i)).toBeInTheDocument();
    });
  });

  it('validates passwords match', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'Password123!');
    await user.type(confirmInput, 'DifferentPassword123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
    });
  });

  it('submits form with valid password', async () => {
    const user = userEvent.setup();
    
    (authApi.resetPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Password reset',
    });

    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'NewPassword123!');
    await user.type(confirmInput, 'NewPassword123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(authApi.resetPassword).toHaveBeenCalledWith({
        token: 'valid-token',
        new_password: 'NewPassword123!',
      });
    });
  });

  it('shows success message after reset', async () => {
    const user = userEvent.setup();
    
    (authApi.resetPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Password reset',
    });

    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'NewPassword123!');
    await user.type(confirmInput, 'NewPassword123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/password reset!/i)).toBeInTheDocument();
    });
  });

  it('shows success icon after reset', async () => {
    const user = userEvent.setup();
    
    (authApi.resetPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Password reset',
    });

    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'NewPassword123!');
    await user.type(confirmInput, 'NewPassword123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      // Success state shows success message and icon
      expect(screen.getByText(/password reset/i)).toBeInTheDocument();
      expect(document.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('shows go to login link after success', async () => {
    const user = userEvent.setup();
    
    (authApi.resetPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Password reset',
    });

    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'NewPassword123!');
    await user.type(confirmInput, 'NewPassword123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /go to login/i })).toBeInTheDocument();
    });
  });

  it('shows error message on API failure', async () => {
    const user = userEvent.setup();
    
    const axiosError = new AxiosError('Token expired');
    (axiosError as any).response = { data: { detail: 'Token expired' } };
    (authApi.resetPassword as ReturnType<typeof vi.fn>).mockRejectedValue(axiosError);

    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'NewPassword123!');
    await user.type(confirmInput, 'NewPassword123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/token expired/i)).toBeInTheDocument();
    });
  });

  it('toggles password visibility', async () => {
    const user = userEvent.setup();
    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    expect(passwordInput).toHaveAttribute('type', 'password');

    // Find toggle button
    const toggleButton = passwordInput.parentElement?.querySelector('button');
    if (toggleButton) {
      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'text');

      await user.click(toggleButton);
      expect(passwordInput).toHaveAttribute('type', 'password');
    }
  });

  it('shows loading state during submission', async () => {
    const user = userEvent.setup();
    
    (authApi.resetPassword as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    );

    renderResetPasswordPage();

    const passwordInput = screen.getByLabelText(/new password/i);
    const confirmInput = screen.getByLabelText(/confirm password/i);

    await user.type(passwordInput, 'NewPassword123!');
    await user.type(confirmInput, 'NewPassword123!');

    const submitButton = screen.getByRole('button', { name: /reset password/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/resetting/i)).toBeInTheDocument();
    });
  });
});
