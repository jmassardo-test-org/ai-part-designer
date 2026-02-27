/**
 * ThemeSync - Syncs theme preference with user profile when logged in (US-16003).
 *
 * - On mount: fetches theme from API if user is logged in, applies it
 * - On theme change: PATCHes to API when user is logged in
 */

import { useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useTheme } from '@/contexts/ThemeContext';
import { getUserPreferences, updateUserPreferences } from '@/lib/api/userPreferences';

export function ThemeSync(): null {
  const { token } = useAuth();
  const { theme, setTheme } = useTheme();
  const initialLoadDone = useRef(false);
  const skipNextSyncRef = useRef(false);

  // Reset when user logs out so we fetch again on next login
  useEffect(() => {
    if (!token) {
      initialLoadDone.current = false;
    }
  }, [token]);

  // On mount / login: fetch theme from API when logged in
  useEffect(() => {
    if (!token || initialLoadDone.current) return;

    let cancelled = false;
    initialLoadDone.current = true;

    getUserPreferences(token)
      .then((prefs) => {
        if (!cancelled && prefs.theme) {
          skipNextSyncRef.current = true;
          setTheme(prefs.theme as 'light' | 'dark' | 'system');
        }
      })
      .catch(() => {
        // Ignore - localStorage theme will be used
      });

    return () => {
      cancelled = true;
    };
  }, [token, setTheme]);

  // When theme changes: sync to API when logged in (skip right after load from API)
  useEffect(() => {
    if (!token) return;
    if (skipNextSyncRef.current) {
      skipNextSyncRef.current = false;
      return;
    }

    updateUserPreferences({ theme }, token).catch(() => {
      // Ignore - theme is still saved to localStorage
    });
  }, [token, theme]);

  return null;
}
