/**
 * Tests for MFA Verification Page
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import MFAVerificationPage from './MFAVerificationPage';

// Mock the hooks and API
vi.mock('@/lib/api/mfa', () => ({
  mfaApi: {
    loginWithMFA: vi.fn(),
  },
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    login: vi.fn(),
  }),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({
      state: { email: 'test@example.com' },
    }),
  };
});

import { mfaApi } from '@/lib/api/mfa';

describe('MFAVerificationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders MFA verification form', () => {
    render(
      <BrowserRouter>
        <MFAVerificationPage />
      </BrowserRouter>
    );
    
    expect(screen.getByText(/two-factor authentication/i)).toBeInTheDocument();
  });

  it('renders TOTP tab by default', () => {
    render(
      <BrowserRouter>
        <MFAVerificationPage />
      </BrowserRouter>
    );
    
    expect(screen.getByRole('tab', { name: /authenticator/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /backup code/i })).toBeInTheDocument();
  });

  it('disables verify button when code is too short', () => {
    render(
      <BrowserRouter>
        <MFAVerificationPage />
      </BrowserRouter>
    );
    
    const input = screen.getByPlaceholderText(/000000/i);
    fireEvent.change(input, { target: { value: '123' } });
    
    // Find the verify button - it should be disabled when code is not 6 digits
    const buttons = screen.getAllByRole('button');
    const verifyButton = buttons.find(btn => btn.textContent?.includes('Verify'));
    expect(verifyButton).toBeDefined();
    expect(verifyButton).toBeDisabled();
  });

  it('submits TOTP code successfully', async () => {
    (mfaApi.loginWithMFA as ReturnType<typeof vi.fn>).mockResolvedValue({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh',
    });
    
    render(
      <BrowserRouter>
        <MFAVerificationPage />
      </BrowserRouter>
    );
    
    const input = screen.getByPlaceholderText(/000000/i);
    fireEvent.change(input, { target: { value: '123456' } });
    
    const button = screen.getByRole('button', { name: /verify/i });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mfaApi.loginWithMFA).toHaveBeenCalledWith({
        email: 'test@example.com',
        code: '123456',
      });
    });
  });

  it('handles API error gracefully', async () => {
    (mfaApi.loginWithMFA as ReturnType<typeof vi.fn>).mockRejectedValue({
      response: { data: { detail: 'Invalid code' } },
    });
    
    render(
      <BrowserRouter>
        <MFAVerificationPage />
      </BrowserRouter>
    );
    
    const input = screen.getByPlaceholderText(/000000/i);
    fireEvent.change(input, { target: { value: '123456' } });
    
    const button = screen.getByRole('button', { name: /verify/i });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(screen.getByText(/invalid code/i)).toBeInTheDocument();
    });
  });

  it('can switch to backup code tab', async () => {
    render(
      <BrowserRouter>
        <MFAVerificationPage />
      </BrowserRouter>
    );
    
    const backupTab = screen.getByRole('tab', { name: /backup code/i });
    fireEvent.click(backupTab);
    
    // Wait for tab switch
    await waitFor(() => {
      expect(screen.getByLabelText(/backup code/i)).toBeInTheDocument();
    });
  });

  it('only allows numeric input for TOTP', async () => {
    render(
      <BrowserRouter>
        <MFAVerificationPage />
      </BrowserRouter>
    );
    
    const input = screen.getByPlaceholderText(/000000/i) as HTMLInputElement;
    fireEvent.change(input, { target: { value: 'abc123' } });
    
    // Should only contain digits (abc is stripped, 123 remains)
    await waitFor(() => {
      expect(input.value).toBe('123');
    });
  });
});
