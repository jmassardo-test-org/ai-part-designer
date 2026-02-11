/**
 * Authentication context provider.
 *
 * Manages user authentication state, token refresh, and provides
 * auth-related functions to the component tree.
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
  type ReactNode,
} from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import type { User, LoginRequest, RegisterRequest } from '@/types/auth';
import { tokenStorage } from '@/lib/api';
import { authApi } from '@/lib/auth';

/** Authentication context value */
interface AuthContextValue {
  /** Current authenticated user */
  user: User | null;
  /** Whether auth state is being loaded */
  isLoading: boolean;
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  /** Current access token (for direct API calls) */
  token: string | null;
  /** Log in with credentials */
  login: (credentials: LoginRequest) => Promise<void>;
  /** Register new account */
  register: (data: RegisterRequest) => Promise<void>;
  /** Log out current user */
  logout: () => Promise<void>;
  /** Refresh user data from server */
  refreshUser: () => Promise<void>;
  /** Update user in state */
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/** Hook to access auth context */
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

/** Auth state provider component */
export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Check for existing session on mount
  useEffect(() => {
    const initAuth = async () => {
      if (!tokenStorage.hasTokens()) {
        setIsLoading(false);
        return;
      }

      try {
        const userData = await authApi.getCurrentUser();
        setUser(userData);
      } catch {
        // Token invalid or expired, clear storage
        tokenStorage.clearTokens();
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  // Login handler
  const login = useCallback(
    async (credentials: LoginRequest) => {
      await authApi.login(credentials);
      
      // Fetch user data after successful login
      const userData = await authApi.getCurrentUser();
      setUser(userData);

      // Redirect to intended destination or dashboard
      const from = (location.state as { from?: Location })?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
    },
    [navigate, location.state]
  );

  // Register handler
  const register = useCallback(
    async (data: RegisterRequest) => {
      await authApi.register(data);
      // After registration, redirect to login with success message
      navigate('/login', { 
        state: { message: 'Registration successful! Please check your email to verify your account.' } 
      });
    },
    [navigate]
  );

  // Logout handler
  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
      navigate('/login', { replace: true });
    }
  }, [navigate]);

  // Refresh user data
  const refreshUser = useCallback(async () => {
    if (!tokenStorage.hasTokens()) {
      return;
    }

    try {
      const userData = await authApi.getCurrentUser();
      setUser(userData);
    } catch {
      setUser(null);
      tokenStorage.clearTokens();
    }
  }, []);

  // Update user in state
  const updateUser = useCallback((updatedUser: User) => {
    setUser(updatedUser);
  }, []);

  // Get current token
  const token = tokenStorage.getAccessToken();

  // Memoize context value
  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      token,
      login,
      register,
      logout,
      refreshUser,
      updateUser,
    }),
    [user, isLoading, token, login, register, logout, refreshUser, updateUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
