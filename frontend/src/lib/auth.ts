/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Auth API client.
 *
 * Handles authentication, login, registration, and password management.
 */

/** Auth API methods. */
export const authApi: any = {
  async login(email: string, password: string): Promise<{ token: string; user: unknown }> {
    const resp = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!resp.ok) throw new Error(`Login failed: ${resp.status}`);
    return resp.json();
  },
  async register(email: string, password: string, name: string): Promise<{ token: string; user: unknown }> {
    const resp = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    });
    if (!resp.ok) throw new Error(`Registration failed: ${resp.status}`);
    return resp.json();
  },
  async forgotPassword(email: string): Promise<{ message: string }> {
    const resp = await fetch('/api/v1/auth/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (!resp.ok) throw new Error(`Forgot password request failed: ${resp.status}`);
    return resp.json();
  },
  async resetPassword(token: string, password: string): Promise<{ message: string }> {
    const resp = await fetch('/api/v1/auth/reset-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, password }),
    });
    if (!resp.ok) throw new Error(`Reset password failed: ${resp.status}`);
    return resp.json();
  },
  async verifyEmail(token: string): Promise<{ message: string }> {
    const resp = await fetch('/api/v1/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    if (!resp.ok) throw new Error(`Email verification failed: ${resp.status}`);
    return resp.json();
  },
  async resendVerification(email: string): Promise<{ message: string }> {
    const resp = await fetch('/api/v1/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (!resp.ok) throw new Error(`Resend verification failed: ${resp.status}`);
    return resp.json();
  },
  async getMe(token: string): Promise<unknown> {
    const resp = await fetch('/api/v1/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resp.ok) throw new Error(`Get user failed: ${resp.status}`);
    return resp.json();
  },
};
