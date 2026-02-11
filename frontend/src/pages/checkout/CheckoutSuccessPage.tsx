/**
 * Checkout Success Page.
 *
 * Displayed after successful Stripe checkout. Shows confirmation
 * with subscription details and next steps.
 */

import confetti from 'canvas-confetti';
import { CheckCircle, Sparkles, Zap, ArrowRight, Loader2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { subscriptionsApi, SubscriptionStatus } from '@/lib/api/subscriptions';

// =============================
// Types
// =============================

interface PremiumFeature {
  icon: React.ReactNode;
  title: string;
  description: string;
}

// =============================
// Constants
// =============================

const PREMIUM_FEATURES: PremiumFeature[] = [
  {
    icon: <Zap className="w-5 h-5 text-yellow-400" />,
    title: 'Unlimited Generations',
    description: 'Create as many designs as you need without limits',
  },
  {
    icon: <Sparkles className="w-5 h-5 text-cyan-400" />,
    title: 'Priority Processing',
    description: 'Your jobs are processed first in the queue',
  },
  {
    icon: <ArrowRight className="w-5 h-5 text-green-400" />,
    title: 'STEP Export',
    description: 'Export your designs in industry-standard STEP format',
  },
];

// =============================
// Helper Functions
// =============================

function formatDate(dateString: string | null): string {
  if (!dateString) return 'N/A';
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

function triggerConfetti() {
  // Fire confetti from both sides
  const duration = 3000;
  const end = Date.now() + duration;

  const colors = ['#22d3ee', '#3b82f6', '#8b5cf6', '#10b981'];

  (function frame() {
    confetti({
      particleCount: 3,
      angle: 60,
      spread: 55,
      origin: { x: 0, y: 0.7 },
      colors,
    });
    confetti({
      particleCount: 3,
      angle: 120,
      spread: 55,
      origin: { x: 1, y: 0.7 },
      colors,
    });

    if (Date.now() < end) {
      requestAnimationFrame(frame);
    }
  })();
}

// =============================
// Main Component
// =============================

export function CheckoutSuccessPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Trigger confetti animation on mount
    triggerConfetti();

    // Fetch subscription status to confirm
    async function fetchSubscription() {
      try {
        const status = await subscriptionsApi.getCurrentSubscription();
        setSubscription(status);
      } catch (err) {
        console.error('Failed to fetch subscription:', err);
        setError('Unable to verify subscription. Please check your dashboard.');
      } finally {
        setIsLoading(false);
      }
    }

    fetchSubscription();
  }, [sessionId]);

  const tierName = subscription?.tier === 'pro' 
    ? 'Pro' 
    : subscription?.tier === 'enterprise' 
      ? 'Enterprise' 
      : 'Premium';

  return (
    <div className="min-h-screen bg-gray-900 flex items-center justify-center px-4 py-12">
      <div className="max-w-lg w-full">
        {/* Success Card */}
        <div className="bg-gray-800 rounded-2xl p-8 text-center shadow-xl border border-gray-700">
          {/* Success Icon */}
          <div className="mx-auto w-20 h-20 rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 flex items-center justify-center mb-6">
            <CheckCircle className="w-10 h-10 text-white" />
          </div>

          {/* Heading */}
          <h1 className="text-3xl font-bold text-white mb-2">
            Welcome to {tierName}!
          </h1>
          <p className="text-gray-400 mb-6">
            Your subscription is now active. Enjoy your premium features!
          </p>

          {/* Subscription Details */}
          {isLoading ? (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-6 h-6 animate-spin text-cyan-500" />
            </div>
          ) : error ? (
            <div className="text-yellow-400 text-sm mb-6">{error}</div>
          ) : subscription && (
            <div className="bg-gray-900/50 rounded-lg p-4 mb-6 text-left">
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400">Plan</span>
                <span className="text-white font-medium capitalize">
                  {subscription.tier}
                </span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-400">Status</span>
                <span className={cn(
                  'font-medium',
                  subscription.is_active ? 'text-green-400' : 'text-yellow-400'
                )}>
                  {subscription.is_active ? 'Active' : subscription.status}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Next Billing</span>
                <span className="text-white">
                  {formatDate(subscription.current_period_end)}
                </span>
              </div>
            </div>
          )}

          {/* Premium Features */}
          <div className="border-t border-gray-700 pt-6 mb-6">
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-4">
              Features Unlocked
            </h2>
            <div className="space-y-3">
              {PREMIUM_FEATURES.map((feature, index) => (
                <div 
                  key={index}
                  className="flex items-center gap-3 text-left p-3 rounded-lg bg-gray-900/30"
                >
                  <div className="flex-shrink-0">{feature.icon}</div>
                  <div>
                    <div className="text-white font-medium text-sm">
                      {feature.title}
                    </div>
                    <div className="text-gray-500 text-xs">
                      {feature.description}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CTAs */}
          <div className="space-y-3">
            <Link
              to="/create"
              className="block w-full py-3 px-4 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 text-white font-medium hover:from-cyan-600 hover:to-blue-600 transition-all"
            >
              Start Creating
            </Link>
            <Link
              to="/dashboard"
              className="block w-full py-3 px-4 rounded-lg bg-gray-700 text-white font-medium hover:bg-gray-600 transition-colors"
            >
              Go to Dashboard
            </Link>
          </div>
        </div>

        {/* Additional Info */}
        <p className="text-center text-gray-500 text-sm mt-6">
          A receipt has been sent to your email.{' '}
          <Link to="/settings" className="text-cyan-400 hover:underline">
            Manage subscription
          </Link>
        </p>
      </div>
    </div>
  );
}

export default CheckoutSuccessPage;
