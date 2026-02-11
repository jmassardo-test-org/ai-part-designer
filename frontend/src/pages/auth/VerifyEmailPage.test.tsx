/**
 * Tests for VerifyEmailPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError } from 'axios';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VerifyEmailPage } from './VerifyEmailPage';
import { authApi } from '@/lib/auth';

// Mock auth API
vi.mock('@/lib/auth', () => ({
  authApi: {
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
  },
}));

const renderVerifyEmailPage = (token: string | null = 'valid-token') => {
  const initialEntry = token ? `/verify-email?token=${token}` : '/verify-email';
  
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state while verifying', () => {
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderVerifyEmailPage();

    expect(screen.getByText(/verifying/i)).toBeInTheDocument();
  });

  it('shows loading spinner while verifying', () => {
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    );

    renderVerifyEmailPage();

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('verifies email with token', async () => {
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email verified',
    });

    renderVerifyEmailPage('test-token');

    await waitFor(() => {
      expect(authApi.verifyEmail).toHaveBeenCalledWith({
        token: 'test-token',
      });
    });
  });

  it('shows success message after verification', async () => {
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email verified',
    });

    renderVerifyEmailPage();

    await waitFor(() => {
      expect(screen.getByText(/email verified/i)).toBeInTheDocument();
    });
  });

  it('shows success icon after verification', async () => {
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email verified',
    });

    renderVerifyEmailPage();

    await waitFor(() => {
      // Success state shows h1 with "Email verified!" text
      expect(screen.getByText(/email verified/i)).toBeInTheDocument();
      // There should be an SVG icon in the document
      expect(document.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('shows continue to login link after success', async () => {
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email verified',
    });

    renderVerifyEmailPage();

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /continue to login/i })).toBeInTheDocument();
    });
  });

  it('shows check email message when no token', () => {
    renderVerifyEmailPage(null);

    expect(screen.getByText(/check your email/i)).toBeInTheDocument();
  });

  it('shows mail icon when no token', () => {
    renderVerifyEmailPage(null);

    // There should be an SVG icon (Mail icon)
    expect(document.querySelector('svg')).toBeInTheDocument();
  });

  it('shows resend link when no token', () => {
    renderVerifyEmailPage(null);

    expect(screen.getByText(/didn't receive/i) || screen.getByText(/resend/i)).toBeTruthy();
  });

  it('resends verification email', async () => {
    const user = userEvent.setup();
    
    (authApi.resendVerification as ReturnType<typeof vi.fn>).mockResolvedValue({});

    renderVerifyEmailPage(null);

    const resendButton = screen.getByRole('button', { name: /resend/i });
    await user.click(resendButton);

    await waitFor(() => {
      expect(authApi.resendVerification).toHaveBeenCalled();
    });
  });

  it('shows success message after resend', async () => {
    const user = userEvent.setup();
    
    (authApi.resendVerification as ReturnType<typeof vi.fn>).mockResolvedValue({});

    renderVerifyEmailPage(null);

    const resendButton = screen.getByRole('button', { name: /resend/i });
    await user.click(resendButton);

    await waitFor(() => {
      expect(screen.getByText(/verification email sent/i)).toBeInTheDocument();
    });
  });

  it('shows error state on verification failure', async () => {
    const axiosError = new AxiosError('Token expired');
    Object.assign(axiosError, { response: { data: { detail: 'Token expired' }, status: 400, statusText: 'Bad Request', headers: {}, config: {} } });
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockRejectedValue(axiosError);

    renderVerifyEmailPage();

    await waitFor(() => {
      expect(screen.getByText(/verification failed/i)).toBeInTheDocument();
    });
  });

  it('shows error message on verification failure', async () => {
    const axiosError = new AxiosError('Token expired');
    Object.assign(axiosError, { response: { data: { detail: 'Token expired' }, status: 400, statusText: 'Bad Request', headers: {}, config: {} } });
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockRejectedValue(axiosError);

    renderVerifyEmailPage();

    await waitFor(() => {
      expect(screen.getByText(/token expired/i)).toBeInTheDocument();
    });
  });

  it('shows error icon on failure', async () => {
    const axiosError = new AxiosError('Error');
    Object.assign(axiosError, { response: { data: { detail: 'Error' }, status: 400, statusText: 'Bad Request', headers: {}, config: {} } });
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockRejectedValue(axiosError);

    renderVerifyEmailPage();

    await waitFor(() => {
      // Error state should show an SVG icon
      expect(screen.getByText(/verification failed/i)).toBeInTheDocument();
      expect(document.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('shows go to login link on error', async () => {
    const axiosError = new AxiosError('Error');
    Object.assign(axiosError, { response: { data: { detail: 'Error' }, status: 400, statusText: 'Bad Request', headers: {}, config: {} } });
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockRejectedValue(axiosError);

    renderVerifyEmailPage();

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /go to login/i })).toBeInTheDocument();
    });
  });

  it('shows request new verification link on error', async () => {
    const axiosError = new AxiosError('Error');
    Object.assign(axiosError, { response: { data: { detail: 'Error' }, status: 400, statusText: 'Bad Request', headers: {}, config: {} } });
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockRejectedValue(axiosError);

    renderVerifyEmailPage();

    await waitFor(() => {
      expect(screen.getByText(/request new verification/i) || screen.getByText(/resend/i)).toBeTruthy();
    });
  });

  it('handles generic error message', async () => {
    (authApi.verifyEmail as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Network error')
    );

    renderVerifyEmailPage();

    await waitFor(() => {
      expect(screen.getByText(/unexpected error/i)).toBeInTheDocument();
    });
  });

  it('shows sending state during resend', async () => {
    const user = userEvent.setup();
    
    (authApi.resendVerification as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    );

    renderVerifyEmailPage(null);

    const resendButton = screen.getByRole('button', { name: /resend/i });
    await user.click(resendButton);

    await waitFor(() => {
      expect(screen.getByText(/sending/i)).toBeInTheDocument();
    });
  });

  it('disables resend button during sending', async () => {
    const user = userEvent.setup();
    
    (authApi.resendVerification as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    );

    renderVerifyEmailPage(null);

    const resendButton = screen.getByRole('button', { name: /resend/i });
    await user.click(resendButton);

    await waitFor(() => {
      expect(resendButton).toBeDisabled();
    });
  });
});
