/**
 * Toast Notification Context and Components.
 * 
 * Provides a global toast notification system with:
 * - Success, error, warning, info variants
 * - Auto-dismiss with configurable duration
 * - Manual dismiss
 * - Queue multiple toasts
 * - Accessible (ARIA live region)
 */

import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  Info,
  X,
} from 'lucide-react';
import {
  createContext,
  useContext,
  useCallback,
  useState,
  useEffect,
  ReactNode,
} from 'react';
import { createPortal } from 'react-dom';

// =============================================================================
// Types
// =============================================================================

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  duration?: number;
  dismissible?: boolean;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => string;
  removeToast: (id: string) => void;
  success: (title: string, message?: string) => string;
  error: (title: string, message?: string) => string;
  warning: (title: string, message?: string) => string;
  info: (title: string, message?: string) => string;
}

// =============================================================================
// Context
// =============================================================================

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

// =============================================================================
// Provider
// =============================================================================

interface ToastProviderProps {
  children: ReactNode;
  maxToasts?: number;
  defaultDuration?: number;
}

export function ToastProvider({
  children,
  maxToasts = 5,
  defaultDuration = 5000,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  // Generate unique ID
  const generateId = () => `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

  // Add toast
  const addToast = useCallback((toast: Omit<Toast, 'id'>): string => {
    const id = generateId();
    const newToast: Toast = {
      id,
      duration: defaultDuration,
      dismissible: true,
      ...toast,
    };

    setToasts((prev) => {
      // Limit to maxToasts
      const updated = [newToast, ...prev];
      return updated.slice(0, maxToasts);
    });

    return id;
  }, [maxToasts, defaultDuration]);

  // Remove toast
  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Convenience methods
  const success = useCallback((title: string, message?: string) => {
    return addToast({ type: 'success', title, message });
  }, [addToast]);

  const error = useCallback((title: string, message?: string) => {
    return addToast({ type: 'error', title, message, duration: 8000 });
  }, [addToast]);

  const warning = useCallback((title: string, message?: string) => {
    return addToast({ type: 'warning', title, message });
  }, [addToast]);

  const info = useCallback((title: string, message?: string) => {
    return addToast({ type: 'info', title, message });
  }, [addToast]);

  const value = {
    toasts,
    addToast,
    removeToast,
    success,
    error,
    warning,
    info,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

// =============================================================================
// Toast Container
// =============================================================================

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  // Create portal for toasts
  if (typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
      aria-atomic="false"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>,
    document.body
  );
}

// =============================================================================
// Toast Item
// =============================================================================

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

function ToastItem({ toast, onRemove }: ToastItemProps) {
  const [isExiting, setIsExiting] = useState(false);

  // Auto-dismiss
  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const timer = setTimeout(() => {
        handleDismiss();
      }, toast.duration);

      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toast.duration, toast.id]);

  // Handle dismiss with animation
  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => {
      onRemove(toast.id);
    }, 200); // Match animation duration
  };

  // Icon and colors by type
  const config = {
    success: {
      icon: CheckCircle,
      bg: 'bg-green-50',
      border: 'border-green-200',
      iconColor: 'text-green-500',
      titleColor: 'text-green-800',
      messageColor: 'text-green-700',
    },
    error: {
      icon: XCircle,
      bg: 'bg-red-50',
      border: 'border-red-200',
      iconColor: 'text-red-500',
      titleColor: 'text-red-800',
      messageColor: 'text-red-700',
    },
    warning: {
      icon: AlertTriangle,
      bg: 'bg-yellow-50',
      border: 'border-yellow-200',
      iconColor: 'text-yellow-500',
      titleColor: 'text-yellow-800',
      messageColor: 'text-yellow-700',
    },
    info: {
      icon: Info,
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      iconColor: 'text-blue-500',
      titleColor: 'text-blue-800',
      messageColor: 'text-blue-700',
    },
  };

  const { icon: Icon, bg, border, iconColor, titleColor, messageColor } = config[toast.type];

  return (
    <div
      role="alert"
      className={`
        pointer-events-auto
        flex items-start gap-3 p-4 rounded-lg shadow-lg border
        ${bg} ${border}
        transition-all duration-200
        ${isExiting ? 'opacity-0 translate-x-4' : 'opacity-100 translate-x-0'}
        animate-in slide-in-from-right-4
      `}
    >
      <Icon className={`w-5 h-5 ${iconColor} flex-shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        <p className={`font-medium ${titleColor}`}>{toast.title}</p>
        {toast.message && (
          <p className={`text-sm mt-1 ${messageColor}`}>{toast.message}</p>
        )}
      </div>
      {toast.dismissible && (
        <button
          onClick={handleDismiss}
          className={`flex-shrink-0 p-1 rounded hover:bg-black/5 ${titleColor}`}
          aria-label="Dismiss notification"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

// =============================================================================
// Standalone Toast Function (for use outside React)
// =============================================================================

let toastFunction: ToastContextValue | null = null;

// eslint-disable-next-line react-refresh/only-export-components
export function setToastRef(ref: ToastContextValue) {
  toastFunction = ref;
}

// eslint-disable-next-line react-refresh/only-export-components
export function toast(type: ToastType, title: string, message?: string): string | undefined {
  if (!toastFunction) {
    console.warn('Toast not initialized. Make sure ToastProvider is mounted.');
    return undefined;
  }
  return toastFunction.addToast({ type, title, message });
}

toast.success = (title: string, message?: string) => toast('success', title, message);
toast.error = (title: string, message?: string) => toast('error', title, message);
toast.warning = (title: string, message?: string) => toast('warning', title, message);
toast.info = (title: string, message?: string) => toast('info', title, message);
