/**
 * Pricing Page.
 * 
 * Displays subscription plans with feature comparison and upgrade CTAs.
 */

import { Check, X, Loader2, Zap, Building, Sparkles, ChevronDown, ArrowRight, HelpCircle } from 'lucide-react';
import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { subscriptionsApi, SubscriptionPlan } from '@/lib/api/subscriptions';
import { cn } from '@/lib/utils';
import { LogoLight, LogoIcon } from '@/components/brand';
import { ThemeToggle } from '@/components/ui/ThemeToggle';

// =============================
// Types
// =============================

interface PricingCardProps {
  plan: SubscriptionPlan;
  isCurrentPlan: boolean;
  billingInterval: 'monthly' | 'yearly';
  onUpgrade: (planSlug: string) => void;
  isLoading: boolean;
}

// =============================
// Pricing Card Component
// =============================

function PricingCard({ 
  plan, 
  isCurrentPlan, 
  billingInterval, 
  onUpgrade,
  isLoading,
}: PricingCardProps) {
  const price = billingInterval === 'yearly' ? plan.price_yearly : plan.price_monthly;
  const monthlyPrice = billingInterval === 'yearly' ? price / 12 : price;
  const isPro = plan.slug === 'pro';
  const isFree = plan.slug === 'free';
  const isEnterprise = plan.slug === 'enterprise';

  const getIcon = () => {
    if (isFree) return <Zap className="w-6 h-6" />;
    if (isPro) return <Sparkles className="w-6 h-6" />;
    return <Building className="w-6 h-6" />;
  };

  return (
    <div
      className={cn(
        'relative flex flex-col rounded-2xl border-2 p-6 shadow-sm transition-all duration-200',
        isPro 
          ? 'border-cyan-500 bg-gradient-to-b from-cyan-900/20 to-transparent scale-105 z-10' 
          : 'border-gray-700 bg-gray-800/50 hover:border-gray-600',
        isCurrentPlan && 'ring-2 ring-cyan-400 ring-offset-2 ring-offset-gray-900'
      )}
    >
      {/* Popular badge */}
      {isPro && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="bg-gradient-to-r from-cyan-500 to-blue-500 text-white text-xs font-semibold px-3 py-1 rounded-full">
            Most Popular
          </span>
        </div>
      )}

      {/* Header */}
      <div className="mb-4">
        <div className={cn(
          'w-12 h-12 rounded-xl flex items-center justify-center mb-4',
          isPro ? 'bg-cyan-500/20 text-cyan-400' : 'bg-gray-700 text-gray-400'
        )}>
          {getIcon()}
        </div>
        <h3 className="text-xl font-bold text-white">{plan.name}</h3>
        <p className="text-gray-400 text-sm mt-1">{plan.description || 'Get started'}</p>
      </div>

      {/* Price */}
      <div className="mb-6">
        {isEnterprise ? (
          <div className="text-3xl font-bold text-white">Custom</div>
        ) : (
          <>
            <div className="flex items-baseline gap-1">
              <span className="text-4xl font-bold text-white">
                ${Math.round(monthlyPrice)}
              </span>
              <span className="text-gray-400">/month</span>
            </div>
            {billingInterval === 'yearly' && !isFree && (
              <p className="text-sm text-green-400 mt-1">
                Save ${Math.round((plan.price_monthly * 12) - plan.price_yearly)}/year
              </p>
            )}
          </>
        )}
      </div>

      {/* Limits */}
      <div className="space-y-3 mb-6 flex-grow">
        <LimitItem 
          label="Monthly generations" 
          value={plan.monthly_credits === -1 ? 'Unlimited' : plan.monthly_credits} 
        />
        <LimitItem 
          label="Projects" 
          value={plan.max_projects === -1 ? 'Unlimited' : plan.max_projects} 
        />
        <LimitItem 
          label="Storage" 
          value={`${plan.max_storage_gb} GB`} 
        />
        <LimitItem 
          label="Concurrent jobs" 
          value={plan.max_concurrent_jobs} 
        />
      </div>

      {/* CTA Button */}
      {isCurrentPlan ? (
        <button
          disabled
          className="w-full py-3 px-4 rounded-lg bg-gray-700 text-gray-400 font-medium cursor-not-allowed"
        >
          Current Plan
        </button>
      ) : isEnterprise ? (
        <a
          href="mailto:sales@aipartdesigner.com?subject=Enterprise%20Inquiry"
          className="w-full py-3 px-4 rounded-lg bg-gray-700 text-white font-medium text-center hover:bg-gray-600 transition-colors"
        >
          Contact Sales
        </a>
      ) : isFree ? (
        <button
          disabled
          className="w-full py-3 px-4 rounded-lg bg-gray-700 text-gray-400 font-medium cursor-not-allowed"
        >
          Free Forever
        </button>
      ) : (
        <button
          onClick={() => onUpgrade(plan.slug)}
          disabled={isLoading}
          className={cn(
            'w-full py-3 px-4 rounded-lg font-medium transition-all duration-200',
            isPro
              ? 'bg-gradient-to-r from-cyan-500 to-blue-500 text-white hover:from-cyan-600 hover:to-blue-600'
              : 'bg-gray-700 text-white hover:bg-gray-600',
            isLoading && 'opacity-50 cursor-not-allowed'
          )}
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              Processing...
            </span>
          ) : (
            `Upgrade to ${plan.name}`
          )}
        </button>
      )}
    </div>
  );
}

function LimitItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-400">{label}</span>
      <span className="text-white font-medium">{value}</span>
    </div>
  );
}

// =============================
// Feature Comparison Component
// =============================

function FeatureComparison({ plans }: { plans: SubscriptionPlan[] }) {
  const features = [
    { key: 'ai_generation', label: 'AI Part Generation' },
    { key: 'export_2d', label: '2D Drawing Export' },
    { key: 'collaboration', label: 'Team Collaboration' },
    { key: 'priority_queue', label: 'Priority Processing' },
    { key: 'custom_templates', label: 'Custom Templates' },
    { key: 'api_access', label: 'API Access' },
  ];

  return (
    <div className="mt-16">
      <h2 className="text-2xl font-bold text-white text-center mb-8">
        Compare Features
      </h2>
      
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-700">
              <th className="py-4 px-6 text-left text-gray-400 font-medium">Feature</th>
              {plans.map(plan => (
                <th key={plan.slug} className="py-4 px-6 text-center text-white font-medium">
                  {plan.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {features.map(feature => (
              <tr key={feature.key} className="border-b border-gray-800">
                <td className="py-4 px-6 text-gray-300">{feature.label}</td>
                {plans.map(plan => (
                  <td key={plan.slug} className="py-4 px-6 text-center">
                    {plan.features[feature.key] ? (
                      <Check className="w-5 h-5 text-green-400 mx-auto" />
                    ) : (
                      <X className="w-5 h-5 text-gray-600 mx-auto" />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// =============================
// FAQ Section Component
// =============================

interface FAQItem {
  question: string;
  answer: string;
}

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What file formats can I export?',
    answer: 'We support STEP files for CNC machining and professional CAD tools, and STL files for 3D printing. Both formats are production-ready with precise tolerances.',
  },
  {
    question: 'Can I cancel my subscription anytime?',
    answer: 'Yes! You can cancel your subscription at any time. Your access will continue until the end of your billing period. No cancellation fees.',
  },
  {
    question: 'What AI models power the generation?',
    answer: 'We use a combination of advanced language models including Ollama for local processing and OpenAI for complex generations. All AI processing follows strict data privacy guidelines.',
  },
  {
    question: 'Is my design data secure?',
    answer: 'Absolutely. All designs are encrypted at rest and in transit. We do not use your designs to train AI models. Enterprise plans include additional security features like SSO and audit logs.',
  },
  {
    question: 'What counts as a "generation"?',
    answer: 'Each time you use AI to create or modify a part, it counts as one generation. Previewing, exporting, or downloading existing designs does not count against your limit.',
  },
  {
    question: 'Do unused credits roll over?',
    answer: 'Monthly credits reset at the beginning of each billing cycle and do not roll over. This ensures fair usage across all users.',
  },
  {
    question: 'Can I upgrade or downgrade my plan?',
    answer: 'Yes, you can change your plan at any time. Upgrades take effect immediately with prorated billing. Downgrades take effect at the next billing cycle.',
  },
  {
    question: 'Do you offer discounts for startups or education?',
    answer: 'Yes! We offer special pricing for startups, educational institutions, and non-profits. Contact our sales team for details.',
  },
];

function FAQSection() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="mt-16">
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 mb-4">
          <HelpCircle className="h-5 w-5 text-cyan-400" />
          <span className="text-sm font-medium text-cyan-400">FAQ</span>
        </div>
        <h2 className="text-2xl font-bold text-white">
          Frequently Asked Questions
        </h2>
        <p className="mt-2 text-gray-400">
          Everything you need to know about our pricing and features.
        </p>
      </div>

      <div className="max-w-3xl mx-auto">
        <div className="space-y-3">
          {FAQ_ITEMS.map((item, index) => (
            <div
              key={index}
              className="bg-gray-800/50 border border-gray-700 rounded-xl overflow-hidden"
            >
              <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-800/80 transition-colors"
              >
                <span className="font-medium text-white pr-4">{item.question}</span>
                <ChevronDown
                  className={cn(
                    'h-5 w-5 text-gray-400 flex-shrink-0 transition-transform',
                    openIndex === index && 'rotate-180'
                  )}
                />
              </button>
              {openIndex === index && (
                <div className="px-4 pb-4">
                  <p className="text-gray-400 text-sm leading-relaxed">
                    {item.answer}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// =============================
// Main Pricing Page
// =============================

export default function PricingPage() {
  const { user } = useAuth();
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [billingInterval, setBillingInterval] = useState<'monthly' | 'yearly'>('monthly');
  const [isLoading, setIsLoading] = useState(true);
  const [upgradeLoading, setUpgradeLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get current tier from user
  const currentTier = user?.subscription_tier || user?.tier || 'free';

  // Fetch plans
  useEffect(() => {
    async function fetchPlans() {
      try {
        const data = await subscriptionsApi.getPlans();
        setPlans(data);
      } catch (err) {
        console.error('Failed to fetch plans:', err);
        setError('Failed to load pricing plans');
      } finally {
        setIsLoading(false);
      }
    }
    fetchPlans();
  }, []);

  // Handle upgrade
  const handleUpgrade = async (planSlug: string) => {
    if (!user) {
      // Redirect to login
      window.location.href = '/login?redirect=/pricing';
      return;
    }

    setUpgradeLoading(planSlug);
    try {
      await subscriptionsApi.redirectToCheckout(planSlug, billingInterval);
    } catch (err) {
      console.error('Failed to start checkout:', err);
      setError('Failed to start checkout. Please try again.');
      setUpgradeLoading(null);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center">
              <LogoLight size="md" />
            </Link>

            <div className="flex items-center gap-4">
              <ThemeToggle size="sm" />
              <Link
                to="/login"
                className="text-gray-300 hover:text-white font-medium"
              >
                Sign in
              </Link>
              <Link to="/register" className="btn-primary btn-md">
                Get started
              </Link>
            </div>
          </div>
        </div>
      </header>

      <div className="py-12 px-4">
        <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-gray-400 text-lg max-w-2xl mx-auto">
            Choose the plan that fits your needs. Upgrade or downgrade anytime.
          </p>
        </div>

        {/* Billing Toggle */}
        <div className="flex items-center justify-center gap-4 mb-12">
          <span className={cn(
            'text-sm font-medium',
            billingInterval === 'monthly' ? 'text-white' : 'text-gray-400'
          )}>
            Monthly
          </span>
          <button
            onClick={() => setBillingInterval(prev => prev === 'monthly' ? 'yearly' : 'monthly')}
            className={cn(
              'relative w-14 h-7 rounded-full transition-colors',
              billingInterval === 'yearly' ? 'bg-cyan-500' : 'bg-gray-600'
            )}
          >
            <div
              className={cn(
                'absolute top-1 w-5 h-5 rounded-full bg-white transition-transform',
                billingInterval === 'yearly' ? 'translate-x-8' : 'translate-x-1'
              )}
            />
          </button>
          <span className={cn(
            'text-sm font-medium',
            billingInterval === 'yearly' ? 'text-white' : 'text-gray-400'
          )}>
            Yearly
            <span className="ml-2 text-xs text-green-400">Save 20%</span>
          </span>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-8 p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200 text-center">
            {error}
          </div>
        )}

        {/* Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
          {plans.map(plan => (
            <PricingCard
              key={plan.slug}
              plan={plan}
              isCurrentPlan={plan.slug === currentTier}
              billingInterval={billingInterval}
              onUpgrade={handleUpgrade}
              isLoading={upgradeLoading === plan.slug}
            />
          ))}
        </div>

        {/* Feature Comparison */}
        <FeatureComparison plans={plans} />

        {/* FAQ Section */}
        <FAQSection />

        {/* CTA Section */}
        <div className="mt-16 text-center">
          <div className="bg-gradient-to-r from-cyan-600 to-blue-600 rounded-2xl p-12">
            <h2 className="text-2xl font-bold text-white mb-4">
              Ready to get started?
            </h2>
            <p className="text-cyan-100 mb-8 max-w-xl mx-auto">
              Join thousands of engineers and makers already using AssemblematicAI
              to accelerate their design workflow.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link to="/register" className="btn bg-white text-cyan-600 hover:bg-gray-100 btn-lg">
                Start Free Trial
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <a 
                href="mailto:sales@assemblematicai.com?subject=Enterprise%20Inquiry"
                className="btn bg-white/10 text-white hover:bg-white/20 btn-lg border border-white/20"
              >
                Contact Sales
              </a>
            </div>
          </div>
        </div>

        {/* Footer links */}
        <div className="mt-12 text-center">
          <p className="text-gray-400">
            Have questions?{' '}
            <Link to="/contact" className="text-cyan-400 hover:underline">
              Contact our team
            </Link>
            {' '}or check our{' '}
            <Link to="/docs" className="text-cyan-400 hover:underline">
              documentation
            </Link>
          </p>
        </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-12 mt-16">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <LogoIcon size={24} />
              <span className="font-semibold text-white">AssemblematicAI</span>
            </div>
            <div className="flex gap-6 text-sm text-gray-400">
              <Link to="/demo" className="hover:text-white">Demo</Link>
              <Link to="/pricing" className="hover:text-white">Pricing</Link>
              <Link to="/terms" className="hover:text-white">Terms</Link>
              <Link to="/privacy" className="hover:text-white">Privacy</Link>
              <Link to="/contact" className="hover:text-white">Contact</Link>
            </div>
          </div>
          <p className="mt-8 text-center text-sm text-gray-500">
            © 2026 AssemblematicAI. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
