/**
 * useDesignManagement Hook
 *
 * Custom hook for design management operations (copy, move, delete, rename).
 * Integrates with the toast notification system for feedback.
 */

import React, { useCallback, useRef, useState } from 'react';
import { ToastAction } from '@/components/ui/toast';
import { useToast } from '@/hooks/use-toast';
import {
  copyDesign,
  deleteDesignWithUndo,
  undoDeleteDesign,
  updateDesign,
  type Design,
} from '@/lib/designs';

// =============================================================================
// Types
// =============================================================================

export interface UseDesignManagementOptions {
  /** Auth token for API calls */
  token: string;
  /** Callback when a design is modified */
  onDesignChange?: (design: Design) => void;
  /** Callback when a design is deleted */
  onDesignDelete?: (designId: string) => void;
  /** Callback when a design is restored */
  onDesignRestore?: (design: Design) => void;
}

export interface UseDesignManagementReturn {
  /** Rename a design */
  renameDesign: (designId: string, newName: string) => Promise<Design>;
  /** Copy a design */
  copyDesignTo: (
    designId: string,
    options: {
      name: string;
      targetProjectId?: string;
      includeVersions: boolean;
    }
  ) => Promise<Design>;
  /** Move a design to another project */
  moveDesign: (designId: string, targetProjectId: string) => Promise<Design>;
  /** Delete a design with undo capability */
  deleteDesignWithToast: (design: Design) => Promise<void>;
  /** Whether any operation is in progress */
  isLoading: boolean;
  /** Current operation being performed */
  currentOperation: string | null;
}

// =============================================================================
// Hook
// =============================================================================

export function useDesignManagement({
  token,
  onDesignChange,
  onDesignDelete,
  onDesignRestore,
}: UseDesignManagementOptions): UseDesignManagementReturn {
  const { toast, dismiss } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [currentOperation, setCurrentOperation] = useState<string | null>(null);

  // Keep track of pending undo timers
  const undoTimers = useRef<Map<string, NodeJS.Timeout>>(new Map());

  /**
   * Rename a design
   */
  const renameDesign = useCallback(
    async (designId: string, newName: string): Promise<Design> => {
      setIsLoading(true);
      setCurrentOperation('rename');

      try {
        const updated = await updateDesign(designId, { name: newName }, token);

        toast({
          title: 'Design renamed',
          description: `Renamed to "${newName}"`,
        });

        onDesignChange?.(updated);
        return updated;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to rename design';
        toast({
          title: 'Error',
          description: message,
          variant: 'destructive',
        });
        throw error;
      } finally {
        setIsLoading(false);
        setCurrentOperation(null);
      }
    },
    [token, toast, onDesignChange]
  );

  /**
   * Copy a design
   */
  const copyDesignTo = useCallback(
    async (
      designId: string,
      options: {
        name: string;
        targetProjectId?: string;
        includeVersions: boolean;
      }
    ): Promise<Design> => {
      setIsLoading(true);
      setCurrentOperation('copy');

      try {
        const copied = await copyDesign(designId, options.name, options, token);

        toast({
          title: 'Design copied',
          description: `Created "${options.name}"`,
        });

        onDesignChange?.(copied);
        return copied;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to copy design';
        toast({
          title: 'Error',
          description: message,
          variant: 'destructive',
        });
        throw error;
      } finally {
        setIsLoading(false);
        setCurrentOperation(null);
      }
    },
    [token, toast, onDesignChange]
  );

  /**
   * Move a design to another project
   */
  const moveDesign = useCallback(
    async (designId: string, targetProjectId: string): Promise<Design> => {
      setIsLoading(true);
      setCurrentOperation('move');

      try {
        const updated = await updateDesign(
          designId,
          { projectId: targetProjectId },
          token
        );

        toast({
          title: 'Design moved',
          description: `Moved to "${updated.project_name}"`,
        });

        onDesignChange?.(updated);
        return updated;
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to move design';
        toast({
          title: 'Error',
          description: message,
          variant: 'destructive',
        });
        throw error;
      } finally {
        setIsLoading(false);
        setCurrentOperation(null);
      }
    },
    [token, toast, onDesignChange]
  );

  /**
   * Delete a design with undo toast
   */
  const deleteDesignWithToast = useCallback(
    async (design: Design): Promise<void> => {
      setIsLoading(true);
      setCurrentOperation('delete');

      try {
        const result = await deleteDesignWithUndo(design.id, token);

        // Notify parent immediately
        onDesignDelete?.(design.id);

        // Calculate time remaining for undo
        const expiresAt = new Date(result.undo_expires_at).getTime();
        const timeRemaining = Math.max(0, expiresAt - Date.now());

        // Show undo toast
        const toastResult = toast({
          title: 'Design deleted',
          description: `"${design.name}" was deleted`,
          action: React.createElement(ToastAction, {
            altText: 'Undo delete',
            onClick: async () => {
              try {
                const restored = await undoDeleteDesign(
                  result.undo_token,
                  token
                );
                onDesignRestore?.(restored);

                // Clear the auto-dismiss timer
                const timer = undoTimers.current.get(result.undo_token);
                if (timer) {
                  clearTimeout(timer);
                  undoTimers.current.delete(result.undo_token);
                }

                toast({
                  title: 'Design restored',
                  description: `"${design.name}" has been restored`,
                });
              } catch {
                toast({
                  title: 'Could not restore',
                  description: 'The undo window has expired',
                  variant: 'destructive',
                });
              }
            },
          }, 'Undo') as React.ReactElement,
          duration: timeRemaining,
        });

        // Set timer to clear the undo token reference
        if (toastResult?.id) {
          const timer = setTimeout(() => {
            undoTimers.current.delete(result.undo_token);
            dismiss(toastResult.id);
          }, timeRemaining);
          undoTimers.current.set(result.undo_token, timer);
        }
      } catch (error) {
        const message =
          error instanceof Error ? error.message : 'Failed to delete design';
        toast({
          title: 'Error',
          description: message,
          variant: 'destructive',
        });
        throw error;
      } finally {
        setIsLoading(false);
        setCurrentOperation(null);
      }
    },
    [token, toast, dismiss, onDesignDelete, onDesignRestore]
  );

  return {
    renameDesign,
    copyDesignTo,
    moveDesign,
    deleteDesignWithToast,
    isLoading,
    currentOperation,
  };
}

export default useDesignManagement;
