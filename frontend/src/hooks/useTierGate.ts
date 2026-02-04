/**
 * Tier Gate Hook.
 *
 * Provides tier checking and paywall display functionality.
 * Use this hook to gate features based on subscription tier.
 */

import { useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';

// =============================
// Types
// =============================

export type Tier = 'free' | 'pro' | 'enterprise';

export interface TierFeatures {
  unlimited_generations: boolean;
  step_export: boolean;
  priority_queue: boolean;
  api_access: boolean;
  team_collaboration: boolean;
  custom_templates: boolean;
}

export interface UseTierGateReturn {
  /** Current user tier */
  tier: Tier;
  /** Whether user has pro or higher */
  isPremium: boolean;
  /** Whether user has enterprise tier */
  isEnterprise: boolean;
  /** Check if user has access to a feature */
  hasFeature: (feature: keyof TierFeatures) => boolean;
  /** Gate a feature - returns true if accessible, shows paywall if not */
  gateFeature: (feature: keyof TierFeatures) => boolean;
  /** Whether paywall is currently shown */
  paywallOpen: boolean;
  /** Feature that triggered paywall */
  paywallFeature: keyof TierFeatures | null;
  /** Required tier for paywalled feature */
  requiredTier: Tier;
  /** Close the paywall */
  closePaywall: () => void;
}

// =============================
// Tier Feature Matrix
// =============================

const TIER_FEATURES: Record<Tier, TierFeatures> = {
  free: {
    unlimited_generations: false,
    step_export: false,
    priority_queue: false,
    api_access: false,
    team_collaboration: false,
    custom_templates: false,
  },
  pro: {
    unlimited_generations: true,
    step_export: true,
    priority_queue: true,
    api_access: false,
    team_collaboration: false,
    custom_templates: true,
  },
  enterprise: {
    unlimited_generations: true,
    step_export: true,
    priority_queue: true,
    api_access: true,
    team_collaboration: true,
    custom_templates: true,
  },
};

// Feature to minimum required tier mapping
const FEATURE_REQUIRED_TIER: Record<keyof TierFeatures, Tier> = {
  unlimited_generations: 'pro',
  step_export: 'pro',
  priority_queue: 'pro',
  api_access: 'enterprise',
  team_collaboration: 'enterprise',
  custom_templates: 'pro',
};

// =============================
// Hook
// =============================

export function useTierGate(): UseTierGateReturn {
  const { user } = useAuth();
  const [paywallOpen, setPaywallOpen] = useState(false);
  const [paywallFeature, setPaywallFeature] = useState<keyof TierFeatures | null>(null);

  // Get current tier from user
  const tier: Tier = (user?.subscription_tier || user?.tier || 'free') as Tier;
  const isPremium = tier === 'pro' || tier === 'enterprise';
  const isEnterprise = tier === 'enterprise';

  // Check if user has a specific feature
  const hasFeature = useCallback((feature: keyof TierFeatures): boolean => {
    return TIER_FEATURES[tier]?.[feature] ?? false;
  }, [tier]);

  // Gate a feature - returns true if accessible, false and shows paywall if not
  const gateFeature = useCallback((feature: keyof TierFeatures): boolean => {
    if (hasFeature(feature)) {
      return true;
    }
    
    // Show paywall
    setPaywallFeature(feature);
    setPaywallOpen(true);
    return false;
  }, [hasFeature]);

  // Close paywall
  const closePaywall = useCallback(() => {
    setPaywallOpen(false);
    setPaywallFeature(null);
  }, []);

  // Get required tier for current paywalled feature
  const requiredTier = paywallFeature 
    ? FEATURE_REQUIRED_TIER[paywallFeature] 
    : 'pro';

  return {
    tier,
    isPremium,
    isEnterprise,
    hasFeature,
    gateFeature,
    paywallOpen,
    paywallFeature,
    requiredTier,
    closePaywall,
  };
}

export default useTierGate;
