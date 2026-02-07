/**
 * Tests for OAuthButtons component.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { OAuthButtons } from './OAuthButtons';

// Mock OAuth API
const mockInitiateLogin = vi.fn();
vi.mock('@/lib/api/oauth', () => ({
  oauthApi: {
    initiateLogin: (provider: string, redirectUri?: string) => mockInitiateLogin(provider, redirectUri),
  },
}));

describe('OAuthButtons', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockInitiateLogin.mockResolvedValue({
      authorization_url: 'https://oauth.provider.com/auth',
      state: 'test-state',
    });

    // Mock window.location
    const originalLocation = window.location;
    delete (window as unknown as { location?: Location }).location;
    (window as unknown as { location: Location }).location = { ...originalLocation, href: '' } as Location;
  });

  it('renders Google and GitHub buttons', () => {
    render(<OAuthButtons />);

    expect(screen.getByRole('button', { name: /continue with google/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /continue with github/i })).toBeInTheDocument();
  });

  it('renders in grid mode by default', () => {
    const { container } = render(<OAuthButtons />);

    const buttonContainer = container.firstChild as HTMLElement;
    expect(buttonContainer).toHaveClass('grid-cols-2');
  });

  it('renders in stack mode when specified', () => {
    const { container } = render(<OAuthButtons mode="stack" />);

    const buttonContainer = container.firstChild as HTMLElement;
    expect(buttonContainer).toHaveClass('flex-col');
  });

  it('initiates Google OAuth flow on click', async () => {
    const user = userEvent.setup();
    render(<OAuthButtons />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    await user.click(googleButton);

    await waitFor(() => {
      expect(mockInitiateLogin).toHaveBeenCalledWith('google', undefined);
    });
  });

  it('initiates GitHub OAuth flow on click', async () => {
    const user = userEvent.setup();
    render(<OAuthButtons />);

    const githubButton = screen.getByRole('button', { name: /continue with github/i });
    await user.click(githubButton);

    await waitFor(() => {
      expect(mockInitiateLogin).toHaveBeenCalledWith('github', undefined);
    });
  });

  it('passes redirect URI to OAuth API', async () => {
    const user = userEvent.setup();
    render(<OAuthButtons redirectUri="/dashboard" />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    await user.click(googleButton);

    await waitFor(() => {
      expect(mockInitiateLogin).toHaveBeenCalledWith('google', '/dashboard');
    });
  });

  it('shows loading state while initiating OAuth', async () => {
    const user = userEvent.setup();
    // Make the mock hang to show loading
    mockInitiateLogin.mockImplementation(() => new Promise(() => {}));

    render(<OAuthButtons />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    await user.click(googleButton);

    // Button should be disabled during loading
    expect(googleButton).toBeDisabled();
  });

  it('disables all buttons when one is loading', async () => {
    const user = userEvent.setup();
    mockInitiateLogin.mockImplementation(() => new Promise(() => {}));

    render(<OAuthButtons />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    const githubButton = screen.getByRole('button', { name: /continue with github/i });
    
    await user.click(googleButton);

    expect(googleButton).toBeDisabled();
    expect(githubButton).toBeDisabled();
  });

  it('calls onError callback on failure', async () => {
    const user = userEvent.setup();
    const onError = vi.fn();
    mockInitiateLogin.mockRejectedValue(new Error('OAuth failed'));

    render(<OAuthButtons onError={onError} />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    await user.click(googleButton);

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith('Failed to initiate google login');
    });
  });

  it('buttons are disabled when disabled prop is true', () => {
    render(<OAuthButtons disabled />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    const githubButton = screen.getByRole('button', { name: /continue with github/i });

    expect(googleButton).toBeDisabled();
    expect(githubButton).toBeDisabled();
  });

  it('redirects to authorization URL after successful initiation', async () => {
    const user = userEvent.setup();
    mockInitiateLogin.mockResolvedValue({
      authorization_url: 'https://accounts.google.com/o/oauth2/auth',
      state: 'test-state-123',
    });

    render(<OAuthButtons />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    await user.click(googleButton);

    await waitFor(() => {
      expect(window.location.href).toBe('https://accounts.google.com/o/oauth2/auth');
    });
  });

  it('displays Google icon', () => {
    render(<OAuthButtons />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    // The button should contain an SVG with the Google colors
    const svg = googleButton.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('displays GitHub icon', () => {
    render(<OAuthButtons />);

    const githubButton = screen.getByRole('button', { name: /continue with github/i });
    const svg = githubButton.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has correct button type to prevent form submission', () => {
    render(<OAuthButtons />);

    const googleButton = screen.getByRole('button', { name: /continue with google/i });
    const githubButton = screen.getByRole('button', { name: /continue with github/i });

    expect(googleButton).toHaveAttribute('type', 'button');
    expect(githubButton).toHaveAttribute('type', 'button');
  });
});
