/**
 * useTierGate Hook Tests.
 *
 * Tests for the tier gating hook.
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useTierGate } from './useTierGate';

// Mock useAuth
let mockUser: object | null = null;

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: !!mockUser,
    isLoading: false,
  }),
}));

describe('useTierGate', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = null;
  });

  describe('Tier Detection', () => {
    it('returns free tier for unauthenticated user', () => {
      mockUser = null;
      const { result } = renderHook(() => useTierGate());

      expect(result.current.tier).toBe('free');
      expect(result.current.isPremium).toBe(false);
      expect(result.current.isEnterprise).toBe(false);
    });

    it('returns free tier for free user', () => {
      mockUser = { id: '1', tier: 'free' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.tier).toBe('free');
      expect(result.current.isPremium).toBe(false);
    });

    it('returns pro tier for pro user', () => {
      mockUser = { id: '1', tier: 'pro' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.tier).toBe('pro');
      expect(result.current.isPremium).toBe(true);
      expect(result.current.isEnterprise).toBe(false);
    });

    it('returns enterprise tier for enterprise user', () => {
      mockUser = { id: '1', tier: 'enterprise' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.tier).toBe('enterprise');
      expect(result.current.isPremium).toBe(true);
      expect(result.current.isEnterprise).toBe(true);
    });

    it('uses subscription_tier if tier is not available', () => {
      mockUser = { id: '1', subscription_tier: 'pro' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.tier).toBe('pro');
    });
  });

  describe('hasFeature', () => {
    it('returns false for pro features on free tier', () => {
      mockUser = { id: '1', tier: 'free' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.hasFeature('step_export')).toBe(false);
      expect(result.current.hasFeature('priority_queue')).toBe(false);
      expect(result.current.hasFeature('unlimited_generations')).toBe(false);
    });

    it('returns true for pro features on pro tier', () => {
      mockUser = { id: '1', tier: 'pro' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.hasFeature('step_export')).toBe(true);
      expect(result.current.hasFeature('priority_queue')).toBe(true);
      expect(result.current.hasFeature('unlimited_generations')).toBe(true);
    });

    it('returns false for enterprise features on pro tier', () => {
      mockUser = { id: '1', tier: 'pro' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.hasFeature('api_access')).toBe(false);
      expect(result.current.hasFeature('team_collaboration')).toBe(false);
    });

    it('returns true for all features on enterprise tier', () => {
      mockUser = { id: '1', tier: 'enterprise' };
      const { result } = renderHook(() => useTierGate());

      expect(result.current.hasFeature('step_export')).toBe(true);
      expect(result.current.hasFeature('priority_queue')).toBe(true);
      expect(result.current.hasFeature('api_access')).toBe(true);
      expect(result.current.hasFeature('team_collaboration')).toBe(true);
    });
  });

  describe('gateFeature', () => {
    it('returns true and does not show paywall for allowed feature', () => {
      mockUser = { id: '1', tier: 'pro' };
      const { result } = renderHook(() => useTierGate());

      let allowed: boolean;
      act(() => {
        allowed = result.current.gateFeature('step_export');
      });

      expect(allowed!).toBe(true);
      expect(result.current.paywallOpen).toBe(false);
    });

    it('returns false and shows paywall for blocked feature', () => {
      mockUser = { id: '1', tier: 'free' };
      const { result } = renderHook(() => useTierGate());

      let allowed: boolean;
      act(() => {
        allowed = result.current.gateFeature('step_export');
      });

      expect(allowed!).toBe(false);
      expect(result.current.paywallOpen).toBe(true);
      expect(result.current.paywallFeature).toBe('step_export');
    });

    it('sets correct required tier for pro feature', () => {
      mockUser = { id: '1', tier: 'free' };
      const { result } = renderHook(() => useTierGate());

      act(() => {
        result.current.gateFeature('step_export');
      });

      expect(result.current.requiredTier).toBe('pro');
    });

    it('sets correct required tier for enterprise feature', () => {
      mockUser = { id: '1', tier: 'pro' };
      const { result } = renderHook(() => useTierGate());

      act(() => {
        result.current.gateFeature('api_access');
      });

      expect(result.current.requiredTier).toBe('enterprise');
    });
  });

  describe('closePaywall', () => {
    it('closes paywall and clears feature', () => {
      mockUser = { id: '1', tier: 'free' };
      const { result } = renderHook(() => useTierGate());

      // Open paywall
      act(() => {
        result.current.gateFeature('step_export');
      });

      expect(result.current.paywallOpen).toBe(true);

      // Close paywall
      act(() => {
        result.current.closePaywall();
      });

      expect(result.current.paywallOpen).toBe(false);
      expect(result.current.paywallFeature).toBeNull();
    });
  });
});
