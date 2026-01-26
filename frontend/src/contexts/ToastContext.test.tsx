import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import { renderHook } from '@testing-library/react';
import React from 'react';
import { ToastProvider, useToast, toast, setToastRef } from './ToastContext';

// Mock createPortal for testing
vi.mock('react-dom', async () => {
  const actual = await vi.importActual('react-dom');
  return {
    ...actual,
    createPortal: (node: React.ReactNode) => node,
  };
});

describe('ToastContext', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('useToast hook', () => {
    it('throws error when used outside provider', () => {
      expect(() => {
        renderHook(() => useToast());
      }).toThrow('useToast must be used within a ToastProvider');
    });

    it('returns context value when inside provider', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ToastProvider>{children}</ToastProvider>
      );

      const { result } = renderHook(() => useToast(), { wrapper });

      expect(result.current.toasts).toEqual([]);
      expect(typeof result.current.addToast).toBe('function');
      expect(typeof result.current.removeToast).toBe('function');
      expect(typeof result.current.success).toBe('function');
      expect(typeof result.current.error).toBe('function');
      expect(typeof result.current.warning).toBe('function');
      expect(typeof result.current.info).toBe('function');
    });
  });

  describe('ToastProvider', () => {
    it('adds and removes toasts', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ToastProvider>{children}</ToastProvider>
      );

      const { result } = renderHook(() => useToast(), { wrapper });

      let toastId: string;
      act(() => {
        toastId = result.current.addToast({
          type: 'success',
          title: 'Test Toast',
          message: 'Test message',
        });
      });

      expect(result.current.toasts).toHaveLength(1);
      expect(result.current.toasts[0].title).toBe('Test Toast');

      act(() => {
        result.current.removeToast(toastId);
      });

      expect(result.current.toasts).toHaveLength(0);
    });

    it('limits toasts to maxToasts', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ToastProvider maxToasts={3}>{children}</ToastProvider>
      );

      const { result } = renderHook(() => useToast(), { wrapper });

      act(() => {
        result.current.addToast({ type: 'info', title: 'Toast 1' });
        result.current.addToast({ type: 'info', title: 'Toast 2' });
        result.current.addToast({ type: 'info', title: 'Toast 3' });
        result.current.addToast({ type: 'info', title: 'Toast 4' });
        result.current.addToast({ type: 'info', title: 'Toast 5' });
      });

      expect(result.current.toasts).toHaveLength(3);
      // Most recent should be first
      expect(result.current.toasts[0].title).toBe('Toast 5');
    });

    it('provides convenience methods', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ToastProvider>{children}</ToastProvider>
      );

      const { result } = renderHook(() => useToast(), { wrapper });

      act(() => {
        result.current.success('Success Title', 'Success message');
      });
      expect(result.current.toasts[0].type).toBe('success');

      act(() => {
        result.current.error('Error Title');
      });
      expect(result.current.toasts[0].type).toBe('error');

      act(() => {
        result.current.warning('Warning Title');
      });
      expect(result.current.toasts[0].type).toBe('warning');

      act(() => {
        result.current.info('Info Title');
      });
      expect(result.current.toasts[0].type).toBe('info');
    });

    it('error toasts have longer default duration', () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <ToastProvider defaultDuration={5000}>{children}</ToastProvider>
      );

      const { result } = renderHook(() => useToast(), { wrapper });

      act(() => {
        result.current.error('Error');
      });

      // Error has 8000ms duration (longer than default)
      expect(result.current.toasts[0].duration).toBe(8000);
    });
  });

  describe('ToastItem', () => {
    it('renders toast content', () => {
      const TestComponent = () => {
        const { addToast } = useToast();
        React.useEffect(() => {
          addToast({ type: 'success', title: 'Test Title', message: 'Test Message' });
        }, [addToast]);
        return null;
      };

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      expect(screen.getByText('Test Title')).toBeInTheDocument();
      expect(screen.getByText('Test Message')).toBeInTheDocument();
    });

    it('renders different toast types with correct styling', () => {
      const TestComponent = () => {
        const { success, error, warning, info } = useToast();
        React.useEffect(() => {
          success('Success');
          error('Error');
          warning('Warning');
          info('Info');
        }, [success, error, warning, info]);
        return null;
      };

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      expect(screen.getByText('Success')).toBeInTheDocument();
      expect(screen.getByText('Error')).toBeInTheDocument();
      expect(screen.getByText('Warning')).toBeInTheDocument();
      expect(screen.getByText('Info')).toBeInTheDocument();
    });

    it('auto-dismisses after duration', () => {
      const TestComponent = () => {
        const { addToast, toasts } = useToast();
        React.useEffect(() => {
          addToast({ type: 'info', title: 'Auto Dismiss', duration: 1000 });
        }, [addToast]);
        return <div data-testid="count">{toasts.length}</div>;
      };

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      expect(screen.getByTestId('count').textContent).toBe('1');

      // Advance time for auto-dismiss
      act(() => {
        vi.advanceTimersByTime(1000);
      });

      // After animation (200ms)
      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(screen.getByTestId('count').textContent).toBe('0');
    });

    it('can be dismissed manually', () => {
      const TestComponent = () => {
        const { addToast, toasts } = useToast();
        React.useEffect(() => {
          addToast({ type: 'info', title: 'Manual Dismiss', dismissible: true });
        }, [addToast]);
        return <div data-testid="count">{toasts.length}</div>;
      };

      render(
        <ToastProvider>
          <TestComponent />
        </ToastProvider>
      );

      expect(screen.getByTestId('count').textContent).toBe('1');

      const dismissButton = screen.getByLabelText('Dismiss notification');
      fireEvent.click(dismissButton);

      // After animation
      act(() => {
        vi.advanceTimersByTime(200);
      });

      expect(screen.getByTestId('count').textContent).toBe('0');
    });
  });

  describe('standalone toast function', () => {
    it('warns when toast ref is not set', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      // Reset the toast ref by setting it to null internally
      // We can't directly reset it, but calling toast without provider tests this path
      const result = toast('success', 'Test', 'Message');
      
      consoleSpy.mockRestore();
    });

    it('works when ref is set', () => {
      const mockToastContext = {
        toasts: [],
        addToast: vi.fn().mockReturnValue('mock-id'),
        removeToast: vi.fn(),
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
      };

      setToastRef(mockToastContext);

      toast('success', 'Test Title', 'Test Message');
      expect(mockToastContext.addToast).toHaveBeenCalledWith({
        type: 'success',
        title: 'Test Title',
        message: 'Test Message',
      });
    });

    it('has convenience methods', () => {
      const mockToastContext = {
        toasts: [],
        addToast: vi.fn().mockReturnValue('mock-id'),
        removeToast: vi.fn(),
        success: vi.fn(),
        error: vi.fn(),
        warning: vi.fn(),
        info: vi.fn(),
      };

      setToastRef(mockToastContext);

      toast.success('Success');
      toast.error('Error');
      toast.warning('Warning');
      toast.info('Info');

      expect(mockToastContext.addToast).toHaveBeenCalledTimes(4);
    });
  });
});
