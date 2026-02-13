/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Onboarding API client.
 *
 * Handles user onboarding flow and progress tracking.
 */

/** An individual onboarding step. */
export interface OnboardingStep {
  [key: string]: any;
  id: string;
  title: string;
  description: string;
  completed: boolean;
  order: number;
}

/** Current onboarding status for a user. */
export interface OnboardingStatus {
  [key: string]: any;
  completed: boolean;
  current_step: number;
  steps: OnboardingStep[];
  skipped: boolean;
}

/** Onboarding API methods. */
export const onboardingApi: any = {
  async getStatus(token?: string): Promise<OnboardingStatus> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/onboarding/status', { headers });
    if (!resp.ok) throw new Error(`Failed to get onboarding status: ${resp.status}`);
    return resp.json();
  },
  async completeStep(stepId: string, token?: string): Promise<OnboardingStatus> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/onboarding/steps/${stepId}/complete`, {
      method: 'POST',
      headers,
    });
    if (!resp.ok) throw new Error(`Failed to complete step: ${resp.status}`);
    return resp.json();
  },
  async skipOnboarding(token?: string): Promise<void> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/onboarding/skip', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to skip onboarding: ${resp.status}`);
  },
  async resetOnboarding(token?: string): Promise<OnboardingStatus> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/onboarding/reset', { method: 'POST', headers });
    if (!resp.ok) throw new Error(`Failed to reset onboarding: ${resp.status}`);
    return resp.json();
  },
};
