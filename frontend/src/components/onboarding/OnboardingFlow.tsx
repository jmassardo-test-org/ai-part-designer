/**
 * Onboarding Flow - New user tutorial experience.
 *
 * Features:
 * - Welcome screen after first login
 * - Step-by-step feature tour
 * - Interactive tooltips highlighting UI elements
 * - Skip option
 * - Track completion in user profile via API
 */

import {
  ChevronRight,
  ChevronLeft,
  Sparkles,
  Box,
  FileBox,
  Wand2,
  FolderOpen,
  Users,
  Download,
  Check,
  Play,
} from 'lucide-react';
import { useState, useEffect, useCallback, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { onboardingApi } from '@/lib/api/onboarding';

// =============================================================================
// Types
// =============================================================================

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: ReactNode;
  target?: string; // CSS selector for highlight
  position?: 'top' | 'bottom' | 'left' | 'right';
  action?: {
    label: string;
    path?: string;
    onClick?: () => void;
  };
}

// =============================================================================
// Onboarding Steps Definition
// =============================================================================

const ONBOARDING_STEPS: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to AssemblematicAI! 🎉',
    description:
      "We're excited to have you! Let's take a quick tour to help you create amazing 3D parts with AI.",
    icon: <Sparkles className="w-12 h-12 text-primary-500" />,
  },
  {
    id: 'templates',
    title: 'Start with Templates',
    description:
      'Browse our library of parametric templates. Customize dimensions, materials, and features to create exactly what you need.',
    icon: <Box className="w-12 h-12 text-blue-500" />,
    target: '[data-tour="templates"]',
    position: 'bottom',
    action: {
      label: 'Browse Templates',
      path: '/templates',
    },
  },
  {
    id: 'generate',
    title: 'AI-Powered Generation',
    description:
      'Describe what you want to create in natural language. Our AI will generate a 3D model matching your description.',
    icon: <Wand2 className="w-12 h-12 text-purple-500" />,
    target: '[data-tour="create"]',
    position: 'bottom',
    action: {
      label: 'Try AI Generation',
      path: '/generate',
    },
  },
  {
    id: 'files',
    title: 'Manage Your Files',
    description:
      'Upload existing CAD files, organize designs into projects, and track version history for all your work.',
    icon: <FileBox className="w-12 h-12 text-green-500" />,
    target: '[data-tour="files"]',
    position: 'bottom',
    action: {
      label: 'View Files',
      path: '/files',
    },
  },
  {
    id: 'projects',
    title: 'Organize with Projects',
    description:
      'Group related designs into projects. Keep your work organized and easy to find.',
    icon: <FolderOpen className="w-12 h-12 text-yellow-500" />,
    target: '[data-tour="projects"]',
    position: 'bottom',
  },
  {
    id: 'collaboration',
    title: 'Collaborate with Others',
    description:
      'Share designs with teammates, add comments, and work together on complex projects.',
    icon: <Users className="w-12 h-12 text-indigo-500" />,
    target: '[data-tour="shared"]',
    position: 'bottom',
  },
  {
    id: 'export',
    title: 'Export for Manufacturing',
    description:
      'Download your designs in STEP, STL, 3MF, and other formats. Ready for 3D printing or CNC machining.',
    icon: <Download className="w-12 h-12 text-teal-500" />,
  },
  {
    id: 'complete',
    title: "You're All Set!",
    description:
      "You're ready to start designing. Create your first project or explore our templates to get started.",
    icon: <Check className="w-12 h-12 text-green-500" />,
    action: {
      label: 'Start Designing',
      path: '/generate',
    },
  },
];

// =============================================================================
// Onboarding Provider Component
// =============================================================================

interface OnboardingProviderProps {
  children: ReactNode;
}

export function OnboardingProvider({ children }: OnboardingProviderProps) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [hasCheckedOnboarding, setHasCheckedOnboarding] = useState(false);
  const [_isLoading, setIsLoading] = useState(false);

  // Check if user needs onboarding via API
  useEffect(() => {
    const checkOnboarding = async () => {
      if (user && !hasCheckedOnboarding) {
        try {
          const status = await onboardingApi.getStatus();
          if (!status.completed) {
            setCurrentStep(status.current_step);
            setIsOnboarding(true);
          }
        } catch {
          // Fallback to localStorage for development/testing
          const onboardingComplete = localStorage.getItem(`onboarding_complete_${user.id}`);
          if (!onboardingComplete) {
            setIsOnboarding(true);
          }
        }
        setHasCheckedOnboarding(true);
      }
    };
    
    checkOnboarding();
  }, [user, hasCheckedOnboarding]);

  const endOnboarding = useCallback(async () => {
    setIsOnboarding(false);
    setCurrentStep(0);
    if (user) {
      localStorage.setItem(`onboarding_complete_${user.id}`, 'true');
    }
  }, [user]);

  const nextStep = useCallback(async () => {
    const step = ONBOARDING_STEPS[currentStep];
    
    // Navigate if action has path
    if (step.action?.path) {
      navigate(step.action.path);
    }
    
    if (currentStep < ONBOARDING_STEPS.length - 1) {
      const newStep = currentStep + 1;
      setCurrentStep(newStep);
      
      // Track step completion via API
      try {
        await onboardingApi.completeStep(newStep);
      } catch (error) {
        console.error('Failed to track onboarding step:', error);
      }
    } else {
      // Complete final step
      try {
        await onboardingApi.completeStep(ONBOARDING_STEPS.length);
      } catch (error) {
        console.error('Failed to complete onboarding:', error);
      }
      endOnboarding();
    }
  }, [currentStep, navigate, endOnboarding]);

  const prevStep = useCallback(() => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1);
    }
  }, [currentStep]);

  const skipOnboarding = useCallback(async () => {
    setIsLoading(true);
    try {
      await onboardingApi.skip();
    } catch (error) {
      console.error('Failed to skip onboarding:', error);
    } finally {
      setIsLoading(false);
      endOnboarding();
    }
  }, [endOnboarding]);

  return (
    <>
      {children}
      {isOnboarding && (
        <OnboardingModal
          step={ONBOARDING_STEPS[currentStep]}
          currentStep={currentStep}
          totalSteps={ONBOARDING_STEPS.length}
          onNext={nextStep}
          onPrev={prevStep}
          onSkip={skipOnboarding}
          onClose={endOnboarding}
        />
      )}
    </>
  );
}

// =============================================================================
// Onboarding Modal Component
// =============================================================================

interface OnboardingModalProps {
  step: OnboardingStep;
  currentStep: number;
  totalSteps: number;
  onNext: () => void;
  onPrev: () => void;
  onSkip: () => void;
  onClose: () => void;
}

function OnboardingModal({
  step,
  currentStep,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  onClose: _onClose,
}: OnboardingModalProps) {
  const isFirstStep = currentStep === 0;
  const isLastStep = currentStep === totalSteps - 1;

  return createPortal(
    <div className="fixed inset-0 z-[9999] flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Modal */}
      <div
        className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden animate-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
        aria-labelledby="onboarding-title"
      >
        {/* Skip button */}
        {!isLastStep && (
          <button
            onClick={onSkip}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-sm"
          >
            Skip tour
          </button>
        )}

        {/* Content */}
        <div className="p-8 text-center">
          {/* Icon */}
          <div className="flex justify-center mb-6">{step.icon}</div>

          {/* Title */}
          <h2
            id="onboarding-title"
            className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3"
          >
            {step.title}
          </h2>

          {/* Description */}
          <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
            {step.description}
          </p>

          {/* Progress dots */}
          <div className="flex justify-center gap-2 mb-8">
            {Array.from({ length: totalSteps }).map((_, i) => (
              <button
                key={i}
                onClick={() => {}}
                className={`w-2 h-2 rounded-full transition-all ${
                  i === currentStep
                    ? 'bg-primary-600 w-6'
                    : i < currentStep
                    ? 'bg-primary-300 dark:bg-primary-600/50'
                    : 'bg-gray-300 dark:bg-gray-600'
                }`}
                aria-label={`Step ${i + 1}`}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-8 pb-8 flex justify-between items-center">
          <button
            onClick={onPrev}
            disabled={isFirstStep}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg ${
              isFirstStep
                ? 'text-gray-300 dark:text-gray-600 cursor-not-allowed'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
            }`}
          >
            <ChevronLeft className="w-4 h-4" />
            Back
          </button>

          <button
            onClick={onNext}
            className="flex items-center gap-2 px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            {isLastStep ? (
              <>
                <Play className="w-4 h-4" />
                Get Started
              </>
            ) : step.action?.label ? (
              <>
                {step.action.label}
                <ChevronRight className="w-4 h-4" />
              </>
            ) : (
              <>
                Next
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

// =============================================================================
// Restart Onboarding Hook
// =============================================================================

// eslint-disable-next-line react-refresh/only-export-components
export function useOnboardingRestart() {
  const { user } = useAuth();

  const restartOnboarding = useCallback(async () => {
    if (user) {
      try {
        await onboardingApi.reset();
        localStorage.removeItem(`onboarding_complete_${user.id}`);
        window.location.reload();
      } catch (error) {
        console.error('Failed to reset onboarding:', error);
        // Fallback to localStorage reset
        localStorage.removeItem(`onboarding_complete_${user.id}`);
        window.location.reload();
      }
    }
  }, [user]);

  return { restartOnboarding };
}
