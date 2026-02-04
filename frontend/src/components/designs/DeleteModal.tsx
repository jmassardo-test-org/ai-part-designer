/**
 * DeleteModal Component
 *
 * Confirmation modal for deleting a design.
 * Shows undo toast after deletion.
 */

import { AlertTriangle, Trash2 } from 'lucide-react';
import React, { useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Design } from '@/lib/designs';

// =============================================================================
// Types
// =============================================================================

export interface DeleteModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** The design being deleted */
  design: Design | null;
  /** Callback when delete is confirmed, returns undo token */
  onConfirm: () => Promise<{ undoToken: string; expiresAt: string }>;
  /** Whether a delete operation is in progress */
  isLoading?: boolean;
}

export interface DeleteResult {
  success: boolean;
  undoToken?: string;
  expiresAt?: string;
}

// =============================================================================
// Component
// =============================================================================

export function DeleteModal({
  isOpen,
  onClose,
  design,
  onConfirm,
  isLoading = false,
}: DeleteModalProps) {
  const [error, setError] = useState<string | null>(null);

  // Reset error when modal opens/closes
  React.useEffect(() => {
    if (isOpen) {
      setError(null);
    }
  }, [isOpen]);

  const handleConfirm = async () => {
    setError(null);

    try {
      await onConfirm();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete design');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-red-600 dark:text-red-400">
            <Trash2 className="h-5 w-5" />
            Delete design
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete this design?
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {/* Design Info */}
          {design && (
            <div className="rounded-md bg-gray-50 p-4 dark:bg-gray-800">
              <div className="flex items-start gap-3">
                {design.thumbnail_url ? (
                  <img
                    src={design.thumbnail_url}
                    alt={design.name}
                    className="h-12 w-12 rounded object-cover"
                  />
                ) : (
                  <div className="flex h-12 w-12 items-center justify-center rounded bg-gray-200 dark:bg-gray-700">
                    <Trash2 className="h-6 w-6 text-gray-400" />
                  </div>
                )}
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {design.name}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    in {design.project_name}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Warning */}
          <div className="mt-4 flex items-start gap-3 rounded-md bg-amber-50 p-3 dark:bg-amber-900/20">
            <AlertTriangle className="h-5 w-5 flex-shrink-0 text-amber-600 dark:text-amber-400" />
            <div className="text-sm text-amber-700 dark:text-amber-300">
              <p className="font-medium">This action can be undone</p>
              <p className="mt-1">
                You'll have 30 seconds to restore this design after deletion.
              </p>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <p className="mt-4 text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="destructive"
            onClick={handleConfirm}
            disabled={isLoading}
            data-testid="confirm-delete"
          >
            {isLoading ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default DeleteModal;
