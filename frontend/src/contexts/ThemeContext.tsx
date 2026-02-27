/**
 * Theme Context - Provides theming functionality across the application.
 * 
 * Supports dark mode (default), light mode, and system preference.
 * Theme persists to localStorage and syncs with user preferences API.
 */

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  useMemo,
} from 'react';

// =============================================================================
// Types
// =============================================================================

export type Theme = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

interface ThemeContextValue {
  /** Current theme setting (may be 'system') */
  theme: Theme;
  /** Resolved theme after system preference ('light' or 'dark') */
  resolvedTheme: ResolvedTheme;
  /** Set the theme */
  setTheme: (theme: Theme) => void;
  /** Toggle between light and dark (ignores system) */
  toggleTheme: () => void;
  /** Whether theme is currently being loaded */
  isLoading: boolean;
}

interface ThemeProviderProps {
  children: React.ReactNode;
  /** Default theme if none stored */
  defaultTheme?: Theme;
  /** Storage key for localStorage */
  storageKey?: string;
  /** Attribute to set on document element */
  attribute?: 'class' | 'data-theme';
}

// =============================================================================
// Constants
// =============================================================================

const STORAGE_KEY = 'assemblematic-ai-theme';
const THEME_ATTRIBUTE = 'class';

// =============================================================================
// Context
// =============================================================================

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

// =============================================================================
// Provider Component
// =============================================================================

export function ThemeProvider({
  children,
  defaultTheme = 'dark',
  storageKey = STORAGE_KEY,
  attribute = THEME_ATTRIBUTE,
}: ThemeProviderProps): JSX.Element {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Try to get theme from localStorage
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(storageKey);
      if (stored === 'light' || stored === 'dark' || stored === 'system') {
        return stored;
      }
    }
    return defaultTheme;
  });
  
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>('dark');
  const [isLoading, setIsLoading] = useState(true);

  // Get system preference
  const getSystemTheme = useCallback((): ResolvedTheme => {
    if (typeof window === 'undefined') return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches
      ? 'dark'
      : 'light';
  }, []);

  // Resolve theme based on setting
  const resolveTheme = useCallback(
    (themeSetting: Theme): ResolvedTheme => {
      if (themeSetting === 'system') {
        return getSystemTheme();
      }
      return themeSetting;
    },
    [getSystemTheme]
  );

  // Apply theme to document
  const applyTheme = useCallback(
    (resolved: ResolvedTheme) => {
      const root = document.documentElement;

      if (attribute === 'class') {
        root.classList.remove('light', 'dark');
        root.classList.add(resolved);
      } else {
        root.setAttribute('data-theme', resolved);
      }

      // Also set color-scheme for native elements
      root.style.colorScheme = resolved;
    },
    [attribute]
  );

  // Set theme and persist
  const setTheme = useCallback(
    (newTheme: Theme) => {
      setThemeState(newTheme);
      localStorage.setItem(storageKey, newTheme);

      const resolved = resolveTheme(newTheme);
      setResolvedTheme(resolved);
      applyTheme(resolved);
    },
    [storageKey, resolveTheme, applyTheme]
  );

  // Toggle between light and dark
  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  }, [resolvedTheme, setTheme]);

  // Initial setup
  useEffect(() => {
    const resolved = resolveTheme(theme);
    setResolvedTheme(resolved);
    applyTheme(resolved);
    setIsLoading(false);
  }, [theme, resolveTheme, applyTheme]);

  // Listen for system theme changes
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleChange = (e: MediaQueryListEvent) => {
      const newResolved = e.matches ? 'dark' : 'light';
      setResolvedTheme(newResolved);
      applyTheme(newResolved);
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme, applyTheme]);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
      toggleTheme,
      isLoading,
    }),
    [theme, resolvedTheme, setTheme, toggleTheme, isLoading]
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// =============================================================================
// Utility Hook for Theme-Aware Values
// =============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export function useThemeValue<T>(lightValue: T, darkValue: T): T {
  const { resolvedTheme } = useTheme();
  return resolvedTheme === 'light' ? lightValue : darkValue;
}

export default ThemeContext;
