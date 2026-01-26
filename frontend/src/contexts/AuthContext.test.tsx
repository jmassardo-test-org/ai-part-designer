/**
 * Tests for AuthContext.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider, useAuth } from '@/contexts/AuthContext';
import type { ReactNode } from 'react';

// Mock the auth API and token storage
const mockLogin = vi.fn();
const mockGetCurrentUser = vi.fn();
const mockLogout = vi.fn();
const mockRegister = vi.fn();

vi.mock('@/lib/auth', () => ({
  authApi: {
    login: (...args: unknown[]) => mockLogin(...args),
    getCurrentUser: () => mockGetCurrentUser(),
    logout: () => mockLogout(),
    register: (...args: unknown[]) => mockRegister(...args),
  },
}));

const mockHasTokens = vi.fn();
const mockClearTokens = vi.fn();

vi.mock('@/lib/api', () => ({
  tokenStorage: {
    getAccessToken: vi.fn(() => null),
    getRefreshToken: vi.fn(() => null),
    setTokens: vi.fn(),
    clearTokens: () => mockClearTokens(),
    hasTokens: () => mockHasTokens(),
  },
  default: {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}));

const mockNavigate = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: null, pathname: '/' }),
  };
});

const wrapper = ({ children }: { children: ReactNode }) => (
  <BrowserRouter>
    <AuthProvider>{children}</AuthProvider>
  </BrowserRouter>
);

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockHasTokens.mockReturnValue(false);
  });

  it('provides default auth state', async () => {
    mockHasTokens.mockReturnValue(false);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('loads user from existing session', async () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      display_name: 'Test User',
      role: 'user',
      status: 'active',
      subscription_tier: 'free',
      created_at: '2024-01-01',
      email_verified_at: '2024-01-01',
    };

    mockHasTokens.mockReturnValue(true);
    mockGetCurrentUser.mockResolvedValue(mockUser);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('clears session on failed token load', async () => {
    mockHasTokens.mockReturnValue(true);
    mockGetCurrentUser.mockRejectedValue(new Error('Invalid token'));

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.user).toBeNull();
    expect(mockClearTokens).toHaveBeenCalled();
  });

  it('login sets user and navigates', async () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      display_name: 'Test User',
      role: 'user',
      status: 'active',
      subscription_tier: 'free',
      created_at: '2024-01-01',
      email_verified_at: '2024-01-01',
    };

    mockLogin.mockResolvedValue({ access_token: 'token', refresh_token: 'refresh' });
    mockGetCurrentUser.mockResolvedValue(mockUser);
    mockHasTokens.mockReturnValue(false);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.login({ email: 'test@example.com', password: 'password' });
    });

    expect(mockLogin).toHaveBeenCalledWith({ email: 'test@example.com', password: 'password' });
    expect(result.current.user).toEqual(mockUser);
    expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
  });

  it('logout clears user and navigates', async () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      display_name: 'Test User',
      role: 'user',
      status: 'active',
      subscription_tier: 'free',
      created_at: '2024-01-01',
      email_verified_at: '2024-01-01',
    };

    mockHasTokens.mockReturnValue(true);
    mockGetCurrentUser.mockResolvedValue(mockUser);
    mockLogout.mockResolvedValue(undefined);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.user).toEqual(mockUser);
    });

    await act(async () => {
      await result.current.logout();
    });

    expect(result.current.user).toBeNull();
    expect(mockNavigate).toHaveBeenCalledWith('/login', { replace: true });
  });

  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      renderHook(() => useAuth());
    }).toThrow('useAuth must be used within an AuthProvider');

    consoleSpy.mockRestore();
  });
});
