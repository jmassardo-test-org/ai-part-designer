/**
 * useOnboarding hook tests.
 */
/* eslint-disable import/order */
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
// Mock modules before importing them
vi.mock('@/lib/api/onboarding', () => ({
  onboardingApi: {
    getStatus: vi.fn(),
    getSteps: vi.fn(),
    completeStep: vi.fn(),
    skip: vi.fn(),
    reset: vi.fn(),
  },
}));

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: vi.fn(),
}));

// Import after mocking
import { useAuth } from '@/contexts/AuthContext';
import { useOnboarding } from '@/hooks/useOnboarding';
import { onboardingApi } from '@/lib/api/onboarding';

describe('useOnboarding', () => {
  const mockOnboardingApi = onboardingApi as unknown as {
    getStatus: ReturnType<typeof vi.fn>;
    getSteps: ReturnType<typeof vi.fn>;
    completeStep: ReturnType<typeof vi.fn>;
    skip: ReturnType<typeof vi.fn>;
    reset: ReturnType<typeof vi.fn>;
  };

  const mockUseAuth = useAuth as ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      user: { id: 'user-123', email: 'test@example.com' },
      isLoading: false,
    });
  });

  const mockStatus = {
    completed: false,
    completed_at: null,
    current_step: 2,
    total_steps: 5,
    step_name: 'upload_component',
  };

  const mockSteps = {
    total_steps: 5,
    steps: [
      { step: 1, name: 'welcome' },
      { step: 2, name: 'upload_component' },
      { step: 3, name: 'generate_design' },
      { step: 4, name: 'explore_templates' },
      { step: 5, name: 'completed' },
    ],
  };

  describe('initial load', () => {
    it('fetches status and steps on mount', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);

      const { result } = renderHook(() => useOnboarding());

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockOnboardingApi.getStatus).toHaveBeenCalled();
      expect(mockOnboardingApi.getSteps).toHaveBeenCalled();
      expect(result.current.status).toEqual(mockStatus);
      expect(result.current.steps).toEqual(mockSteps.steps);
    });

    it('sets needsOnboarding to true when not completed', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.needsOnboarding).toBe(true);
    });

    it('sets needsOnboarding to false when completed', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue({
        ...mockStatus,
        completed: true,
        completed_at: '2025-01-27T10:00:00Z',
      });
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.needsOnboarding).toBe(false);
    });

    it('does not fetch when user is not logged in', async () => {
      mockUseAuth.mockReturnValue({
        user: null,
        isLoading: false,
      });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(mockOnboardingApi.getStatus).not.toHaveBeenCalled();
      expect(result.current.status).toBeNull();
    });

    it('waits for auth to finish loading', () => {
      mockUseAuth.mockReturnValue({
        user: { id: 'user-123', email: 'test@example.com' },
        isLoading: true,
      });
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);

      const { result } = renderHook(() => useOnboarding());

      expect(result.current.isLoading).toBe(true);
      expect(mockOnboardingApi.getStatus).not.toHaveBeenCalled();
    });

    it('handles fetch error', async () => {
      mockOnboardingApi.getStatus.mockRejectedValue(new Error('Network error'));
      mockOnboardingApi.getSteps.mockRejectedValue(new Error('Network error'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBe('Failed to load onboarding status');
      consoleSpy.mockRestore();
    });
  });

  describe('completeStep', () => {
    it('completes a step and updates status', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.completeStep.mockResolvedValue({
        current_step: 3,
        total_steps: 5,
        step_name: 'generate_design',
        completed: false,
        message: 'Step 2 completed',
      });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.completeStep(2);
      });

      expect(mockOnboardingApi.completeStep).toHaveBeenCalledWith(2, undefined);
      expect(result.current.status?.current_step).toBe(3);
      expect(result.current.status?.step_name).toBe('generate_design');
    });

    it('completes a step with data', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.completeStep.mockResolvedValue({
        current_step: 3,
        total_steps: 5,
        step_name: 'generate_design',
        completed: false,
        message: 'Component uploaded',
      });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.completeStep(2, { component_id: 'comp-123' });
      });

      expect(mockOnboardingApi.completeStep).toHaveBeenCalledWith(2, {
        component_id: 'comp-123',
      });
    });

    it('marks as completed when finishing final step', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue({
        ...mockStatus,
        current_step: 5,
        step_name: 'explore_templates',
      });
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.completeStep.mockResolvedValue({
        current_step: 5,
        total_steps: 5,
        step_name: 'completed',
        completed: true,
        message: 'Onboarding completed!',
      });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.completeStep(5);
      });

      expect(result.current.status?.completed).toBe(true);
    });

    it('handles complete step error', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.completeStep.mockRejectedValue(new Error('Step already completed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.completeStep(1);
        })
      ).rejects.toThrow('Step already completed');

      // Error is set before throw, verify console.error was called
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('skipOnboarding', () => {
    it('skips onboarding and marks as completed', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.skip.mockResolvedValue({ message: 'Onboarding skipped' });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await act(async () => {
        await result.current.skipOnboarding();
      });

      expect(mockOnboardingApi.skip).toHaveBeenCalled();
      expect(result.current.status?.completed).toBe(true);
    });

    it('handles skip error', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.skip.mockRejectedValue(new Error('Already skipped'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.skipOnboarding();
        })
      ).rejects.toThrow('Already skipped');

      // Error is set before throw, verify console.error was called
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('resetOnboarding', () => {
    it('resets onboarding and refreshes status', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.reset.mockResolvedValue({ message: 'Onboarding reset' });

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Reset should trigger a refresh, so set up new mock return
      mockOnboardingApi.getStatus.mockResolvedValue({
        completed: false,
        completed_at: null,
        current_step: 1,
        total_steps: 5,
        step_name: 'welcome',
      });

      await act(async () => {
        await result.current.resetOnboarding();
      });

      expect(mockOnboardingApi.reset).toHaveBeenCalled();
      expect(mockOnboardingApi.getStatus).toHaveBeenCalledTimes(2);
    });

    it('handles reset error', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);
      mockOnboardingApi.reset.mockRejectedValue(new Error('Reset failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      await expect(
        act(async () => {
          await result.current.resetOnboarding();
        })
      ).rejects.toThrow('Reset failed');

      // Error is set before throw, verify console.error was called
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });

  describe('refresh', () => {
    it('refreshes status and steps', async () => {
      mockOnboardingApi.getStatus.mockResolvedValue(mockStatus);
      mockOnboardingApi.getSteps.mockResolvedValue(mockSteps);

      const { result } = renderHook(() => useOnboarding());

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Update mock for refresh
      mockOnboardingApi.getStatus.mockResolvedValue({
        ...mockStatus,
        current_step: 4,
        step_name: 'explore_templates',
      });

      await act(async () => {
        await result.current.refresh();
      });

      expect(mockOnboardingApi.getStatus).toHaveBeenCalledTimes(2);
      expect(result.current.status?.current_step).toBe(4);
    });
  });
});
