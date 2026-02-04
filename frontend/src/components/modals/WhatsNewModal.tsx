/**
 * WhatsNewModal Component
 * 
 * Displays release notes and new features to users.
 * Shows automatically on first visit after update.
 */

import { X, Sparkles, Zap, Palette, Command, Bell, CreditCard, Lock } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface Feature {
  icon: React.ElementType;
  title: string;
  description: string;
  isNew?: boolean;
}

interface WhatsNewModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Current version */
  version?: string;
}

// =============================================================================
// Constants
// =============================================================================

const CURRENT_VERSION = '1.0.0';
const STORAGE_KEY = 'whats-new-seen-version';

const FEATURES: Feature[] = [
  {
    icon: Sparkles,
    title: 'AI-Powered Design Generation',
    description: 'Describe what you need in natural language, and our AI creates CAD-ready 3D models instantly.',
    isNew: true,
  },
  {
    icon: CreditCard,
    title: 'Pro & Enterprise Plans',
    description: 'Unlock unlimited designs, priority processing, and advanced features with our new subscription tiers.',
    isNew: true,
  },
  {
    icon: Lock,
    title: 'Social Login',
    description: 'Sign in quickly with Google or GitHub. Link multiple accounts for flexibility.',
    isNew: true,
  },
  {
    icon: Zap,
    title: 'Real-time Updates',
    description: 'See job progress and notifications instantly with our new WebSocket-powered live updates.',
    isNew: true,
  },
  {
    icon: Command,
    title: 'Slash Commands',
    description: 'Power users can use /commands for quick actions. Try /help to see all available commands.',
    isNew: true,
  },
  {
    icon: Palette,
    title: 'Industrial Theme',
    description: 'A professional dark theme designed for extended use, with light mode available for bright environments.',
    isNew: true,
  },
  {
    icon: Bell,
    title: 'Notification Center',
    description: 'Never miss an update. All your notifications in one convenient place.',
    isNew: true,
  },
];

// =============================================================================
// Hooks
// =============================================================================

/**
 * Hook to manage "What's New" modal visibility
 */
export function useWhatsNewModal(): {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  shouldShow: boolean;
} {
  const [isOpen, setIsOpen] = useState(false);
  const [shouldShow, setShouldShow] = useState(false);

  useEffect(() => {
    const seenVersion = localStorage.getItem(STORAGE_KEY);
    if (seenVersion !== CURRENT_VERSION) {
      setShouldShow(true);
    }
  }, []);

  const open = () => setIsOpen(true);
  
  const close = () => {
    setIsOpen(false);
    localStorage.setItem(STORAGE_KEY, CURRENT_VERSION);
    setShouldShow(false);
  };

  return { isOpen, open, close, shouldShow };
}

// =============================================================================
// Component
// =============================================================================

export function WhatsNewModal({
  isOpen,
  onClose,
  version = CURRENT_VERSION,
}: WhatsNewModalProps): JSX.Element | null {
  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, onClose]);

  // Prevent body scroll when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-labelledby="whats-new-title"
      >
        <div
          className={cn(
            'relative w-full max-w-2xl max-h-[90vh] overflow-hidden',
            'bg-white dark:bg-gray-800 rounded-xl shadow-2xl',
            'animate-in fade-in zoom-in-95 duration-200'
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="relative px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-cyan-500">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <div>
                <h2
                  id="whats-new-title"
                  className="text-xl font-bold text-gray-900 dark:text-white"
                >
                  What's New in v{version}
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Check out the latest features and improvements
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="absolute top-4 right-4 p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Content */}
          <div className="overflow-y-auto max-h-[60vh] p-6">
            <div className="space-y-4">
              {FEATURES.map((feature, index) => (
                <FeatureCard key={index} feature={feature} />
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <div className="flex items-center justify-between">
              <a
                href="/changelog"
                className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
              >
                View full changelog
              </a>
              <button
                onClick={onClose}
                className={cn(
                  'px-6 py-2 rounded-lg font-medium transition-colors',
                  'bg-primary-600 hover:bg-primary-700 text-white'
                )}
              >
                Got it!
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// =============================================================================
// Subcomponents
// =============================================================================

function FeatureCard({ feature }: { feature: Feature }): JSX.Element {
  const Icon = feature.icon;

  return (
    <div
      className={cn(
        'flex items-start gap-4 p-4 rounded-lg',
        'bg-gray-50 dark:bg-gray-700/50',
        'border border-gray-100 dark:border-gray-700'
      )}
    >
      <div
        className={cn(
          'flex-shrink-0 w-10 h-10 rounded-lg flex items-center justify-center',
          'bg-primary-100 dark:bg-primary-900/30'
        )}
      >
        <Icon className="h-5 w-5 text-primary-600 dark:text-primary-400" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {feature.title}
          </h3>
          {feature.isNew && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
              New
            </span>
          )}
        </div>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
          {feature.description}
        </p>
      </div>
    </div>
  );
}

export default WhatsNewModal;
