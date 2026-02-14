/**
 * Onboarding API client tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './client';
import { onboardingApi } from './onboarding';

// Mock the api client
vi.mock('./client', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('onboardingApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getStatus', () => {
    it('returns onboarding status for in-progress user', async () => {
      const mockStatus = {
        completed: false,
        completed_at: null,
        current_step: 2,
        total_steps: 5,
        step_name: 'upload_component',
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockStatus,
      });

      const result = await onboardingApi.getStatus();

      expect(api.get).toHaveBeenCalledWith('/onboarding/status');
      expect(result.completed).toBe(false);
      expect(result.current_step).toBe(2);
      expect(result.step_name).toBe('upload_component');
    });

    it('returns completed onboarding status', async () => {
      const mockStatus = {
        completed: true,
        completed_at: '2025-01-27T10:00:00Z',
        current_step: 5,
        total_steps: 5,
        step_name: 'completed',
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockStatus,
      });

      const result = await onboardingApi.getStatus();

      expect(result.completed).toBe(true);
      expect(result.completed_at).toBe('2025-01-27T10:00:00Z');
    });

    it('returns initial onboarding status for new user', async () => {
      const mockStatus = {
        completed: false,
        completed_at: null,
        current_step: 1,
        total_steps: 5,
        step_name: 'welcome',
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockStatus,
      });

      const result = await onboardingApi.getStatus();

      expect(result.current_step).toBe(1);
      expect(result.step_name).toBe('welcome');
    });
  });

  describe('completeStep', () => {
    it('completes a step without data', async () => {
      const mockResponse = {
        current_step: 3,
        total_steps: 5,
        step_name: 'generate_design',
        completed: false,
        message: 'Step 2 completed',
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await onboardingApi.completeStep(2);

      expect(api.post).toHaveBeenCalledWith('/onboarding/step/2', { step_data: {} });
      expect(result.current_step).toBe(3);
      expect(result.message).toBe('Step 2 completed');
    });

    it('completes a step with step data', async () => {
      const mockResponse = {
        current_step: 4,
        total_steps: 5,
        step_name: 'explore_templates',
        completed: false,
        message: 'Component uploaded',
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await onboardingApi.completeStep(3, {
        component_id: 'comp-123',
        component_type: 'raspberry-pi',
      });

      expect(api.post).toHaveBeenCalledWith('/onboarding/step/3', {
        step_data: {
          component_id: 'comp-123',
          component_type: 'raspberry-pi',
        },
      });
      expect(result.step_name).toBe('explore_templates');
    });

    it('completes final step and marks onboarding complete', async () => {
      const mockResponse = {
        current_step: 5,
        total_steps: 5,
        step_name: 'completed',
        completed: true,
        message: 'Onboarding completed!',
      };

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await onboardingApi.completeStep(5);

      expect(result.completed).toBe(true);
      expect(result.message).toBe('Onboarding completed!');
    });

    it('handles completing already completed step', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Step already completed')
      );

      await expect(onboardingApi.completeStep(1)).rejects.toThrow(
        'Step already completed'
      );
    });

    it('handles skipping ahead too far', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Cannot skip steps')
      );

      await expect(onboardingApi.completeStep(5)).rejects.toThrow(
        'Cannot skip steps'
      );
    });
  });

  describe('skip', () => {
    it('skips onboarding entirely', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { message: 'Onboarding skipped' },
      });

      const result = await onboardingApi.skip();

      expect(api.post).toHaveBeenCalledWith('/onboarding/skip');
      expect(result.message).toBe('Onboarding skipped');
    });

    it('handles already skipped onboarding', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Onboarding already completed or skipped')
      );

      await expect(onboardingApi.skip()).rejects.toThrow(
        'Onboarding already completed or skipped'
      );
    });
  });

  describe('reset', () => {
    it('resets onboarding for testing', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { message: 'Onboarding reset successfully' },
      });

      const result = await onboardingApi.reset();

      expect(api.post).toHaveBeenCalledWith('/onboarding/reset');
      expect(result.message).toBe('Onboarding reset successfully');
    });
  });

  describe('getSteps', () => {
    it('returns list of onboarding steps', async () => {
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

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockSteps,
      });

      const result = await onboardingApi.getSteps();

      expect(api.get).toHaveBeenCalledWith('/onboarding/steps');
      expect(result.total_steps).toBe(5);
      expect(result.steps).toHaveLength(5);
      expect(result.steps[0].name).toBe('welcome');
      expect(result.steps[4].name).toBe('completed');
    });
  });

  describe('getMetrics', () => {
    it('returns onboarding metrics for admin', async () => {
      const mockMetrics = {
        total_users: 1000,
        completed_count: 600,
        skipped_count: 150,
        in_progress_count: 200,
        not_started_count: 50,
        completion_rate: 0.6,
        skip_rate: 0.15,
        step_distribution: {
          'welcome': 50,
          'upload_component': 80,
          'generate_design': 70,
          'explore_templates': 40,
          'completed': 600,
        },
        avg_completion_time_hours: 2.5,
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockMetrics,
      });

      const result = await onboardingApi.getMetrics();

      expect(api.get).toHaveBeenCalledWith('/onboarding/metrics');
      expect(result.total_users).toBe(1000);
      expect(result.completion_rate).toBe(0.6);
      expect(result.avg_completion_time_hours).toBe(2.5);
    });

    it('handles null avg_completion_time for new deployments', async () => {
      const mockMetrics = {
        total_users: 5,
        completed_count: 0,
        skipped_count: 0,
        in_progress_count: 5,
        not_started_count: 0,
        completion_rate: 0,
        skip_rate: 0,
        step_distribution: {},
        avg_completion_time_hours: null,
      };

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockMetrics,
      });

      const result = await onboardingApi.getMetrics();

      expect(result.avg_completion_time_hours).toBeNull();
    });

    it('handles unauthorized access to metrics', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Admin access required')
      );

      await expect(onboardingApi.getMetrics()).rejects.toThrow(
        'Admin access required'
      );
    });
  });
});
