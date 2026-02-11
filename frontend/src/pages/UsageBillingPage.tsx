/**
 * Usage & Billing Page
 *
 * Displays credit balance, usage statistics, quota usage,
 * and subscription management.
 */

import {
  CreditCard,
  Zap,
  HardDrive,
  FolderKanban,
  Activity,
  Clock,
  TrendingUp,
  TrendingDown,
  Crown,
  Check,
  Loader2,
  AlertCircle,
  ArrowUpRight,
  Sparkles,
  ExternalLink,
  XCircle,
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { subscriptionsApi, SubscriptionStatus } from '@/lib/api/subscriptions';
import {
  usageApi,
  UsageDashboard,
  SubscriptionTier,
  CreditTransaction,
} from '@/lib/api/usage';

// =============================================================================
// Helper Functions
// =============================================================================

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function getTransactionIcon(type: string) {
  switch (type) {
    case 'generation':
      return <Sparkles className="h-4 w-4 text-blue-500" />;
    case 'refinement':
      return <Activity className="h-4 w-4 text-purple-500" />;
    case 'export_2d':
      return <ArrowUpRight className="h-4 w-4 text-green-500" />;
    case 'monthly_refill':
      return <Zap className="h-4 w-4 text-yellow-500" />;
    case 'purchase':
      return <CreditCard className="h-4 w-4 text-emerald-500" />;
    default:
      return <Activity className="h-4 w-4 text-gray-500" />;
  }
}

// =============================================================================
// Components
// =============================================================================

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  className?: string;
}

function StatCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  trendValue,
  className,
}: StatCardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800',
        className
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            {title}
          </p>
          <p className="mt-2 text-3xl font-semibold text-gray-900 dark:text-white">
            {value}
          </p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {subtitle}
            </p>
          )}
          {trend && trendValue && (
            <div
              className={cn('mt-2 flex items-center text-sm', {
                'text-green-600': trend === 'up',
                'text-red-600': trend === 'down',
                'text-gray-500': trend === 'neutral',
              })}
            >
              {trend === 'up' ? (
                <TrendingUp className="mr-1 h-4 w-4" />
              ) : trend === 'down' ? (
                <TrendingDown className="mr-1 h-4 w-4" />
              ) : null}
              {trendValue}
            </div>
          )}
        </div>
        <div className="rounded-lg bg-gray-100 p-3 dark:bg-gray-700">{icon}</div>
      </div>
    </div>
  );
}

interface ProgressBarProps {
  value: number;
  max: number;
  label: string;
  valueLabel: string;
  color?: 'blue' | 'green' | 'yellow' | 'red';
}

function ProgressBar({
  value,
  max,
  label,
  valueLabel,
  color = 'blue',
}: ProgressBarProps) {
  const percent = max > 0 ? (value / max) * 100 : 0;
  
  const colorClasses = {
    blue: 'bg-blue-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  };

  return (
    <div className="space-y-2">
      <div className="flex justify-between text-sm">
        <span className="font-medium text-gray-700 dark:text-gray-300">
          {label}
        </span>
        <span className="text-gray-500 dark:text-gray-400">{valueLabel}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700">
        <div
          className={cn('h-full rounded-full transition-all', colorClasses[color])}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
    </div>
  );
}

interface TierCardProps {
  tier: SubscriptionTier;
  isCurrent: boolean;
  onSelect?: () => void;
}

function TierCard({ tier, isCurrent, onSelect }: TierCardProps) {
  return (
    <div
      className={cn(
        'relative rounded-lg border p-6',
        isCurrent
          ? 'border-blue-500 bg-blue-50 dark:border-blue-400 dark:bg-blue-900/20'
          : 'border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800'
      )}
    >
      {isCurrent && (
        <div className="absolute -top-3 left-4 rounded-full bg-blue-500 px-3 py-1 text-xs font-medium text-white">
          Current Plan
        </div>
      )}
      
      <div className="flex items-center gap-2">
        <Crown
          className={cn(
            'h-5 w-5',
            tier.slug === 'enterprise'
              ? 'text-purple-500'
              : tier.slug === 'pro'
              ? 'text-yellow-500'
              : 'text-gray-400'
          )}
        />
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {tier.name}
        </h3>
      </div>
      
      {tier.description && (
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          {tier.description}
        </p>
      )}
      
      <div className="mt-4">
        <span className="text-3xl font-bold text-gray-900 dark:text-white">
          ${tier.price_monthly}
        </span>
        <span className="text-gray-500 dark:text-gray-400">/month</span>
      </div>
      
      <ul className="mt-4 space-y-2">
        <li className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <Check className="h-4 w-4 text-green-500" />
          {tier.monthly_credits} credits/month
        </li>
        <li className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <Check className="h-4 w-4 text-green-500" />
          {tier.max_concurrent_jobs} concurrent jobs
        </li>
        <li className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <Check className="h-4 w-4 text-green-500" />
          {tier.max_storage_gb} GB storage
        </li>
        <li className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
          <Check className="h-4 w-4 text-green-500" />
          {tier.max_projects} projects
        </li>
      </ul>
      
      {!isCurrent && (
        <button
          onClick={onSelect}
          className="mt-6 w-full rounded-lg bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          {tier.price_monthly > 0 ? 'Upgrade' : 'Downgrade'}
        </button>
      )}
    </div>
  );
}

interface TransactionRowProps {
  transaction: CreditTransaction;
}

function TransactionRow({ transaction }: TransactionRowProps) {
  const isPositive = transaction.amount > 0;
  
  return (
    <div className="flex items-center justify-between border-b border-gray-100 py-3 last:border-0 dark:border-gray-700">
      <div className="flex items-center gap-3">
        {getTransactionIcon(transaction.transaction_type)}
        <div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">
            {transaction.description}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {formatDate(transaction.created_at)}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p
          className={cn('text-sm font-medium', {
            'text-green-600': isPositive,
            'text-red-600': !isPositive,
          })}
        >
          {isPositive ? '+' : ''}{transaction.amount}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Balance: {transaction.balance_after}
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export function UsageBillingPage() {
  const [dashboard, setDashboard] = useState<UsageDashboard | null>(null);
  const [tiers, setTiers] = useState<SubscriptionTier[]>([]);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'tiers' | 'billing'>('overview');
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setIsLoading(true);
    setError(null);
    
    try {
      const [dashboardData, tiersData, subscriptionData] = await Promise.all([
        usageApi.getDashboard(),
        usageApi.getTiers(),
        subscriptionsApi.getCurrentSubscription(),
      ]);
      
      setDashboard(dashboardData);
      setTiers(tiersData);
      setSubscription(subscriptionData);
    } catch (err) {
      console.error('Failed to load usage data:', err);
      setError('Failed to load usage data. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleOpenBillingPortal() {
    setActionLoading('portal');
    try {
      await subscriptionsApi.redirectToBillingPortal();
    } catch (err) {
      console.error('Failed to open billing portal:', err);
      setError('Failed to open billing portal. Please try again.');
      setActionLoading(null);
    }
  }

  async function handleCancelSubscription() {
    setActionLoading('cancel');
    try {
      const updated = await subscriptionsApi.cancelSubscription(false);
      setSubscription(updated);
      setCancelDialogOpen(false);
    } catch (err) {
      console.error('Failed to cancel subscription:', err);
      setError('Failed to cancel subscription. Please try again.');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleResumeSubscription() {
    setActionLoading('resume');
    try {
      const updated = await subscriptionsApi.resumeSubscription();
      setSubscription(updated);
    } catch (err) {
      console.error('Failed to resume subscription:', err);
      setError('Failed to resume subscription. Please try again.');
    } finally {
      setActionLoading(null);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="text-gray-600 dark:text-gray-400">{error}</p>
        <button
          onClick={loadData}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!dashboard) {
    return null;
  }

  return (
    <div className="container mx-auto max-w-6xl px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Usage & Billing
        </h1>
        <p className="mt-1 text-gray-600 dark:text-gray-400">
          Monitor your usage and manage your subscription
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex border-b border-gray-200 dark:border-gray-700">
        {(['overview', 'transactions', 'tiers', 'billing'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors',
              activeTab === tab
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            )}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Credit Balance"
              value={dashboard.credits.balance}
              subtitle={`${dashboard.credits.credits_per_month}/month`}
              icon={<Zap className="h-6 w-6 text-yellow-500" />}
            />
            <StatCard
              title="Storage Used"
              value={formatBytes(dashboard.quota.storage_used_bytes)}
              subtitle={`of ${formatBytes(dashboard.quota.storage_limit_bytes)}`}
              icon={<HardDrive className="h-6 w-6 text-blue-500" />}
            />
            <StatCard
              title="Active Jobs"
              value={dashboard.quota.active_jobs_count}
              subtitle={`of ${dashboard.quota.max_concurrent_jobs} allowed`}
              icon={<Activity className="h-6 w-6 text-green-500" />}
            />
            <StatCard
              title="Projects"
              value={dashboard.quota.projects_count}
              subtitle={`of ${dashboard.quota.max_projects} allowed`}
              icon={<FolderKanban className="h-6 w-6 text-purple-500" />}
            />
          </div>

          {/* Quota Progress */}
          <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
              Quota Usage
            </h2>
            <div className="space-y-4">
              <ProgressBar
                value={dashboard.quota.storage_used_bytes}
                max={dashboard.quota.storage_limit_bytes}
                label="Storage"
                valueLabel={`${dashboard.quota.storage_used_percent}%`}
                color={dashboard.quota.storage_used_percent > 90 ? 'red' : 'blue'}
              />
              <ProgressBar
                value={dashboard.quota.projects_count}
                max={dashboard.quota.max_projects}
                label="Projects"
                valueLabel={`${dashboard.quota.projects_count}/${dashboard.quota.max_projects}`}
                color="green"
              />
              <ProgressBar
                value={dashboard.quota.active_jobs_count}
                max={dashboard.quota.max_concurrent_jobs}
                label="Concurrent Jobs"
                valueLabel={`${dashboard.quota.active_jobs_count}/${dashboard.quota.max_concurrent_jobs}`}
                color="yellow"
              />
            </div>
          </div>

          {/* Current Plan & Next Refill */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                Current Plan
              </h2>
              <div className="flex items-center gap-3">
                <Crown className="h-8 w-8 text-yellow-500" />
                <div>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">
                    {dashboard.current_tier.name}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    ${dashboard.current_tier.price_monthly}/month
                  </p>
                </div>
              </div>
            </div>
            
            <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
                Next Credit Refill
              </h2>
              <div className="flex items-center gap-3">
                <Clock className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="text-xl font-bold text-gray-900 dark:text-white">
                    {dashboard.credits.next_refill_at
                      ? new Date(dashboard.credits.next_refill_at).toLocaleDateString()
                      : 'N/A'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    +{dashboard.credits.credits_per_month} credits
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Transactions */}
          <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                Recent Transactions
              </h2>
              <button
                onClick={() => setActiveTab('transactions')}
                className="text-sm text-blue-600 hover:text-blue-700"
              >
                View All
              </button>
            </div>
            <div>
              {dashboard.recent_transactions.length === 0 ? (
                <p className="py-4 text-center text-gray-500 dark:text-gray-400">
                  No transactions yet
                </p>
              ) : (
                dashboard.recent_transactions.slice(0, 5).map((t) => (
                  <TransactionRow key={t.id} transaction={t} />
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Transactions Tab */}
      {activeTab === 'transactions' && (
        <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
          <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
            Transaction History
          </h2>
          <div>
            {dashboard.recent_transactions.length === 0 ? (
              <p className="py-8 text-center text-gray-500 dark:text-gray-400">
                No transactions yet
              </p>
            ) : (
              dashboard.recent_transactions.map((t) => (
                <TransactionRow key={t.id} transaction={t} />
              ))
            )}
          </div>
        </div>
      )}

      {/* Tiers Tab */}
      {activeTab === 'tiers' && (
        <div className="grid gap-6 md:grid-cols-3">
          {tiers.map((tier) => (
            <TierCard
              key={tier.id}
              tier={tier}
              isCurrent={tier.is_current}
              onSelect={() => {
                // TODO: Implement tier change flow
                console.log('Selected tier:', tier.slug);
              }}
            />
          ))}
        </div>
      )}

      {/* Billing Tab */}
      {activeTab === 'billing' && subscription && (
        <div className="space-y-6">
          {/* Current Subscription */}
          <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
              Subscription Details
            </h2>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Plan</p>
                  <p className="text-lg font-semibold text-gray-900 capitalize dark:text-white">
                    {subscription.tier}
                  </p>
                </div>
                <div className={cn(
                  'rounded-full px-3 py-1 text-sm font-medium',
                  subscription.is_active 
                    ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                    : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                )}>
                  {subscription.is_active ? 'Active' : subscription.status}
                </div>
              </div>

              {subscription.current_period_end && (
                <div className="flex items-center justify-between border-b border-gray-100 pb-4 dark:border-gray-700">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {subscription.cancel_at_period_end ? 'Access Until' : 'Next Billing Date'}
                    </p>
                    <p className="text-gray-900 dark:text-white">
                      {new Date(subscription.current_period_end).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </p>
                  </div>
                  {subscription.cancel_at_period_end && (
                    <span className="text-sm text-red-600 dark:text-red-400">
                      Cancellation scheduled
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Billing Actions */}
          <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
            <h2 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
              Manage Billing
            </h2>
            
            <div className="space-y-4">
              {/* Billing Portal Button */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    Payment Method
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Update your card or view payment history
                  </p>
                </div>
                <button
                  onClick={handleOpenBillingPortal}
                  disabled={actionLoading === 'portal'}
                  className="flex items-center gap-2 rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  {actionLoading === 'portal' ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <ExternalLink className="h-4 w-4" />
                  )}
                  Manage Payment
                </button>
              </div>

              {/* Cancel/Resume Subscription */}
              {subscription.is_premium && (
                <div className="border-t border-gray-100 pt-4 dark:border-gray-700">
                  {subscription.cancel_at_period_end ? (
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          Resume Subscription
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Your subscription is set to cancel. Resume to keep your plan.
                        </p>
                      </div>
                      <button
                        onClick={handleResumeSubscription}
                        disabled={actionLoading === 'resume'}
                        className="flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                      >
                        {actionLoading === 'resume' ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Check className="h-4 w-4" />
                        )}
                        Keep Subscription
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          Cancel Subscription
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          You'll retain access until the end of your billing period.
                        </p>
                      </div>
                      <button
                        onClick={() => setCancelDialogOpen(true)}
                        className="flex items-center gap-2 rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-900/20"
                      >
                        <XCircle className="h-4 w-4" />
                        Cancel Plan
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Cancel Confirmation Dialog */}
      {cancelDialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="mx-4 w-full max-w-md rounded-lg bg-white p-6 dark:bg-gray-800">
            <div className="mb-4 flex items-center gap-3 text-red-600">
              <AlertCircle className="h-6 w-6" />
              <h3 className="text-lg font-semibold">Cancel Subscription?</h3>
            </div>
            <p className="mb-2 text-gray-600 dark:text-gray-400">
              Are you sure you want to cancel your subscription?
            </p>
            <ul className="mb-6 ml-4 list-disc space-y-1 text-sm text-gray-500 dark:text-gray-400">
              <li>You'll retain access until {subscription?.current_period_end 
                ? new Date(subscription.current_period_end).toLocaleDateString() 
                : 'the end of your billing period'}</li>
              <li>Your designs and projects will be preserved</li>
              <li>You can resubscribe anytime</li>
            </ul>
            <div className="flex gap-3">
              <button
                onClick={() => setCancelDialogOpen(false)}
                className="flex-1 rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
              >
                Keep Subscription
              </button>
              <button
                onClick={handleCancelSubscription}
                disabled={actionLoading === 'cancel'}
                className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 font-medium text-white hover:bg-red-700"
              >
                {actionLoading === 'cancel' ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : null}
                Cancel Subscription
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UsageBillingPage;
