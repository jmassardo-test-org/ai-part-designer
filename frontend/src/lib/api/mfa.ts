/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * MFA (Multi-Factor Authentication) API client.
 *
 * Handles MFA setup, verification, and management.
 */

/** Response from MFA setup initiation. */
export interface MFASetupResponse {
  [key: string]: any;
  secret: string;
  qr_code_url: string;
  backup_codes: string[];
}

/** MFA API methods. */
export const mfaApi: any = {
  async setupMFA(token?: string): Promise<MFASetupResponse> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/auth/mfa/setup', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`MFA setup failed: ${resp.status}`);
    return resp.json();
  },
  async verifyMFA(code: string, token?: string): Promise<{ success: boolean }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/auth/mfa/verify', {
      method: 'POST',
      headers,
      body: JSON.stringify({ code }),
    });
    if (!resp.ok) throw new Error(`MFA verification failed: ${resp.status}`);
    return resp.json();
  },
  async disableMFA(code: string, token?: string): Promise<{ success: boolean }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/auth/mfa/disable', {
      method: 'POST',
      headers,
      body: JSON.stringify({ code }),
    });
    if (!resp.ok) throw new Error(`MFA disable failed: ${resp.status}`);
    return resp.json();
  },
  async confirmSetup(code: string, token?: string): Promise<{ success: boolean; backup_codes?: string[] }> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/auth/mfa/confirm', {
      method: 'POST',
      headers,
      body: JSON.stringify({ code }),
    });
    if (!resp.ok) throw new Error(`MFA confirm failed: ${resp.status}`);
    return resp.json();
  },
};
