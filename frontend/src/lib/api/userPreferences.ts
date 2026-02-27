/**
 * User preferences API - theme and other user settings.
 * Used for syncing theme preference across devices when logged in (US-16003).
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
}

/** Get current user's preferences. */
export async function getUserPreferences(token: string): Promise<UserPreferences> {
  const resp = await fetch(`${API_BASE}/users/me/preferences`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Failed to get preferences: ${resp.status}`);
  return resp.json();
}

/** Update current user's preferences. */
export async function updateUserPreferences(
  updates: Partial<UserPreferences>,
  token: string
): Promise<UserPreferences> {
  const resp = await fetch(`${API_BASE}/users/me/preferences`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(updates),
  });
  if (!resp.ok) throw new Error(`Failed to update preferences: ${resp.status}`);
  return resp.json();
}
