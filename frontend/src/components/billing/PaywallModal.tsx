/**
 * Paywall Modal Component.
 *
 * Displays when a user tries to access a feature that requires
 * a higher subscription tier. Shows feature benefit and upgrade CTA.
 */

import { Lock, Zap, ArrowRight, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

// =============================
// Types
// =============================

export interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
  feature: string;
  description?: string;
  requiredTier?: 'pro' | 'enterprise';
}

// =============================
// Feature descriptions for paywall
// =============================

const FEATURE_INFO: Record<string, { title: string; description: string; icon: React.ReactNode }> = {
  step_export: {
    title: 'STEP Export',
    description: 'Export your designs in industry-standard STEP format for use in professional CAD software.',
    icon: <ArrowRight className="w-6 h-6" />,
  },
  priority_queue: {
    title: 'Priority Processing',
    description: 'Skip the queue and get your designs generated faster with priority processing.',
    icon: <Zap className="w-6 h-6" />,
  },
  unlimited_generations: {
    title: 'Unlimited Generations',
    description: 'Create as many designs as you need without monthly limits.',
    icon: <Zap className="w-6 h-6" />,
  },
  api_access: {
    title: 'API Access',
    description: 'Integrate AssemblematicAI into your workflow with our REST API.',
    icon: <ArrowRight className="w-6 h-6" />,
  },
  team_collaboration: {
    title: 'Team Collaboration',
    description: 'Invite team members and collaborate on designs together.',
    icon: <ArrowRight className="w-6 h-6" />,
  },
  default: {
    title: 'Premium Feature',
    description: 'Upgrade your plan to access this feature.',
    icon: <Lock className="w-6 h-6" />,
  },
};

// =============================
// Component
// =============================

export function PaywallModal({
  isOpen,
  onClose,
  feature,
  description,
  requiredTier = 'pro',
}: PaywallModalProps) {
  if (!isOpen) return null;

  const featureInfo = FEATURE_INFO[feature] || FEATURE_INFO.default;
  const displayDescription = description || featureInfo.description;
  const tierName = requiredTier === 'enterprise' ? 'Enterprise' : 'Pro';

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div 
        className="mx-4 w-full max-w-md transform rounded-2xl bg-gray-800 p-6 shadow-2xl border border-gray-700"
        onClick={e => e.stopPropagation()}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Icon */}
        <div className="mx-auto w-16 h-16 rounded-full bg-gradient-to-r from-cyan-500/20 to-blue-500/20 flex items-center justify-center mb-4">
          <div className="text-cyan-400">
            {featureInfo.icon}
          </div>
        </div>

        {/* Content */}
        <div className="text-center">
          <h2 className="text-xl font-bold text-white mb-2">
            {featureInfo.title}
          </h2>
          <p className="text-gray-400 mb-6">
            {displayDescription}
          </p>

          {/* Upgrade prompt */}
          <div className="bg-gray-900/50 rounded-lg p-4 mb-6">
            <p className="text-sm text-gray-300">
              This feature is available on{' '}
              <span className={cn(
                'font-semibold',
                requiredTier === 'enterprise' ? 'text-purple-400' : 'text-cyan-400'
              )}>
                {tierName}
              </span>{' '}
              and higher plans.
            </p>
          </div>

          {/* CTAs */}
          <div className="space-y-3">
            <Link
              to="/pricing"
              onClick={onClose}
              className="block w-full py-3 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-medium hover:from-cyan-600 hover:to-blue-600 transition-all"
            >
              Upgrade to {tierName}
            </Link>
            <button
              onClick={onClose}
              className="w-full py-2 px-4 text-gray-400 text-sm hover:text-white transition-colors"
            >
              Maybe later
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PaywallModal;
