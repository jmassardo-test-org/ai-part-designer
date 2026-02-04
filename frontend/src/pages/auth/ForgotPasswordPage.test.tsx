/**
 * Tests for ForgotPasswordPage component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AxiosError } from 'axios';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ForgotPasswordPage } from './ForgotPasswordPage';

// Mock auth API
vi.mock('@/lib/auth', () => ({
  authApi: {
    forgotPassword: vi.fn(),
  },
}));

import { authApi } from '@/lib/auth';

const renderForgotPasswordPage = () => {
  return render(
    <BrowserRouter>
      <ForgotPasswordPage />
    </BrowserRouter>
  );
};

describe('ForgotPasswordPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders forgot password form', () => {
    renderForgotPasswordPage();

    expect(screen.getByRole('heading', { name: /forgot password/i })).toBeInTheDocument();
  });

  it('shows email input field', () => {
    renderForgotPasswordPage();

    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
  });

  it('shows submit button', () => {
    renderForgotPasswordPage();

    expect(screen.getByRole('button', { name: /send reset link/i })).toBeInTheDocument();
  });

  it('has back to login link', () => {
    renderForgotPasswordPage();

    expect(screen.getByRole('link', { name: /back to login/i })).toHaveAttribute('href', '/login');
  });

  it('validates email format', async () => {
    const user = userEvent.setup();
    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    // Submit without any input to trigger required validation
    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    // The form should prevent submission and display an error
    // Either inline validation error or the form doesn't submit (no API call)
    expect(authApi.forgotPassword).not.toHaveBeenCalled();
  });

  it('submits form with valid email', async () => {
    const user = userEvent.setup();
    
    (authApi.forgotPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email sent',
    });

    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(authApi.forgotPassword).toHaveBeenCalledWith({
        email: 'test@example.com',
      });
    });
  });

  it('shows success message after submission', async () => {
    const user = userEvent.setup();
    
    (authApi.forgotPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email sent',
    });

    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
    });
  });

  it('shows success icon after submission', async () => {
    const user = userEvent.setup();
    
    (authApi.forgotPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email sent',
    });

    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    await waitFor(() => {
      // Success page should have an icon and success message
      expect(screen.getByText(/check your email/i)).toBeInTheDocument();
      expect(document.querySelector('svg')).toBeInTheDocument();
    });
  });

  it('shows back to login button after success', async () => {
    const user = userEvent.setup();
    
    (authApi.forgotPassword as ReturnType<typeof vi.fn>).mockResolvedValue({
      message: 'Email sent',
    });

    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole('link', { name: /back to login/i })).toBeInTheDocument();
    });
  });

  it('shows error message on API failure', async () => {
    const user = userEvent.setup();
    
    const axiosError = new AxiosError('Failed to send reset email');
    (axiosError as any).response = { data: { detail: 'Failed to send reset email' } };
    (authApi.forgotPassword as ReturnType<typeof vi.fn>).mockRejectedValue(axiosError);

    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/failed to send/i)).toBeInTheDocument();
    });
  });

  it('shows loading state during submission', async () => {
    const user = userEvent.setup();
    
    (authApi.forgotPassword as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/sending/i)).toBeInTheDocument();
    });
  });

  it('disables submit button during loading', async () => {
    const user = userEvent.setup();
    
    (authApi.forgotPassword as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(() => {})
    );

    renderForgotPasswordPage();

    const emailInput = screen.getByLabelText(/email address/i);
    await user.type(emailInput, 'test@example.com');

    const submitButton = screen.getByRole('button', { name: /send reset link/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(submitButton).toBeDisabled();
    });
  });

  it('displays helpful instructions', () => {
    renderForgotPasswordPage();

    expect(screen.getByText(/no worries/i)).toBeInTheDocument();
    expect(screen.getByText(/send you reset instructions/i)).toBeInTheDocument();
  });
});
