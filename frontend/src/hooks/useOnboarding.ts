/**
 * Onboarding hook.
 *
 * Provides onboarding status and step management.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { onboardingApi, OnboardingStatus, OnboardingStep } from '@/lib/api/onboarding';

interface UseOnboardingResult {
  /** Current onboarding status */
  status: OnboardingStatus | null;
  /** List of onboarding steps */
  steps: OnboardingStep[];
  /** Whether onboarding is loading */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Whether onboarding is needed */
  needsOnboarding: boolean;
  /** Complete a specific step */
  completeStep: (step: number, data?: Record<string, unknown>) => Promise<void>;
  /** Skip onboarding entirely */
  skipOnboarding: () => Promise<void>;
  /** Reset onboarding (for testing) */
  resetOnboarding: () => Promise<void>;
  /** Refresh onboarding status */
  refresh: () => Promise<void>;
}

export function useOnboarding(): UseOnboardingResult {
  const { user, isLoading: isAuthLoading } = useAuth();
  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [steps, setSteps] = useState<OnboardingStep[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!user) {
      setStatus(null);
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      const [statusData, stepsData] = await Promise.all([
        onboardingApi.getStatus(),
        onboardingApi.getSteps(),
      ]);
      setStatus(statusData);
      setSteps(stepsData.steps);
    } catch (err) {
      console.error('Failed to fetch onboarding status:', err);
      setError('Failed to load onboarding status');
    } finally {
      setIsLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!isAuthLoading) {
      fetchStatus();
    }
  }, [fetchStatus, isAuthLoading]);

  const completeStep = useCallback(
    async (step: number, data?: Record<string, unknown>) => {
      try {
        setError(null);
        const response = await onboardingApi.completeStep(step, data);
        setStatus((prev) =>
          prev
            ? {
                ...prev,
                current_step: response.current_step,
                step_name: response.step_name,
                completed: response.completed,
              }
            : null
        );
      } catch (err) {
        console.error('Failed to complete onboarding step:', err);
        setError('Failed to complete step');
        throw err;
      }
    },
    []
  );

  const skipOnboarding = useCallback(async () => {
    try {
      setError(null);
      await onboardingApi.skip();
      setStatus((prev) =>
        prev
          ? {
              ...prev,
              completed: true,
              current_step: prev.total_steps,
            }
          : null
      );
    } catch (err) {
      console.error('Failed to skip onboarding:', err);
      setError('Failed to skip onboarding');
      throw err;
    }
  }, []);

  const resetOnboarding = useCallback(async () => {
    try {
      setError(null);
      await onboardingApi.reset();
      await fetchStatus();
    } catch (err) {
      console.error('Failed to reset onboarding:', err);
      setError('Failed to reset onboarding');
      throw err;
    }
  }, [fetchStatus]);

  // Determine if onboarding is needed
  const needsOnboarding = Boolean(user && status && !status.completed);

  return {
    status,
    steps,
    isLoading: isLoading || isAuthLoading,
    error,
    needsOnboarding,
    completeStep,
    skipOnboarding,
    resetOnboarding,
    refresh: fetchStatus,
  };
}

export default useOnboarding;
