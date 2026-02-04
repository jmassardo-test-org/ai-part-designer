/**
 * DesignActionsMenu Component
 *
 * A dropdown menu providing quick actions for design management:
 * rename, copy, move, delete, and version management.
 */

import {
  Copy,
  FolderInput,
  History,
  MoreVertical,
  Pencil,
  Trash2,
} from 'lucide-react';
import React, { useCallback, useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Design, Project } from '@/lib/designs';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface DesignActionsMenuProps {
  /** The design to perform actions on */
  design: Design;
  /** User's projects for move/copy operations */
  projects: Project[];
  /** Callback when rename action is triggered */
  onRename: (design: Design) => void;
  /** Callback when copy action is triggered */
  onCopy: (design: Design) => void;
  /** Callback when move action is triggered */
  onMove: (design: Design) => void;
  /** Callback when delete action is triggered */
  onDelete: (design: Design) => void;
  /** Callback when versions action is triggered */
  onVersions?: (design: Design) => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show the versions option */
  showVersions?: boolean;
  /** Disable the entire menu */
  disabled?: boolean;
}

// =============================================================================
// Component
// =============================================================================

export function DesignActionsMenu({
  design,
  projects,
  onRename,
  onCopy,
  onMove,
  onDelete,
  onVersions,
  className,
  showVersions = true,
  disabled = false,
}: DesignActionsMenuProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleAction = useCallback(
    (action: (design: Design) => void) => (e: React.MouseEvent) => {
      e.stopPropagation();
      setIsOpen(false);
      action(design);
    },
    [design]
  );

  const toggleMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen((prev) => !prev);
  };

  const closeMenu = () => setIsOpen(false);

  return (
    <div className={cn('relative', className)}>
      {/* Trigger Button */}
      <Button
        variant="ghost"
        size="sm"
        onClick={toggleMenu}
        disabled={disabled}
        className="h-8 w-8 p-0 hover:bg-gray-100 dark:hover:bg-gray-700"
        aria-label="Design actions"
        data-testid="design-actions-trigger"
      >
        <MoreVertical className="h-4 w-4" />
      </Button>

      {/* Dropdown Menu */}
      {isOpen && (
        <>
          {/* Backdrop to close menu when clicking outside */}
          <div
            className="fixed inset-0 z-40"
            onClick={closeMenu}
            data-testid="menu-backdrop"
          />

          <div
            className="absolute right-0 top-full z-50 mt-1 min-w-[180px] rounded-md border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-700 dark:bg-gray-800"
            role="menu"
            data-testid="design-actions-menu"
          >
            {/* Rename */}
            <button
              onClick={handleAction(onRename)}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
              role="menuitem"
              data-testid="action-rename"
            >
              <Pencil className="h-4 w-4" />
              Rename
            </button>

            {/* Copy */}
            <button
              onClick={handleAction(onCopy)}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
              role="menuitem"
              data-testid="action-copy"
            >
              <Copy className="h-4 w-4" />
              Make a copy
            </button>

            {/* Move */}
            {projects.length > 1 && (
              <button
                onClick={handleAction(onMove)}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
                role="menuitem"
                data-testid="action-move"
              >
                <FolderInput className="h-4 w-4" />
                Move to project
              </button>
            )}

            {/* Versions */}
            {showVersions && onVersions && (
              <button
                onClick={handleAction(onVersions)}
                className="flex w-full items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-200 dark:hover:bg-gray-700"
                role="menuitem"
                data-testid="action-versions"
              >
                <History className="h-4 w-4" />
                Version history
              </button>
            )}

            {/* Separator */}
            <div className="my-1 border-t border-gray-200 dark:border-gray-700" />

            {/* Delete */}
            <button
              onClick={handleAction(onDelete)}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
              role="menuitem"
              data-testid="action-delete"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// =============================================================================
// Rename Modal
// =============================================================================

export interface RenameModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** The design being renamed */
  design: Design | null;
  /** Callback when rename is confirmed */
  onConfirm: (newName: string) => Promise<void>;
  /** Whether a rename operation is in progress */
  isLoading?: boolean;
}

export function RenameModal({
  isOpen,
  onClose,
  design,
  onConfirm,
  isLoading = false,
}: RenameModalProps) {
  const [name, setName] = useState(design?.name || '');
  const [error, setError] = useState<string | null>(null);

  // Reset state when design changes
  React.useEffect(() => {
    if (design) {
      setName(design.name);
      setError(null);
    }
  }, [design]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedName = name.trim();
    if (!trimmedName) {
      setError('Name is required');
      return;
    }

    if (trimmedName.length > 255) {
      setError('Name must be 255 characters or less');
      return;
    }

    try {
      await onConfirm(trimmedName);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename design');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Rename design</DialogTitle>
            <DialogDescription>
              Enter a new name for your design.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <label
              htmlFor="design-name"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              Name
            </label>
            <input
              id="design-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              placeholder="Design name"
              autoFocus
              disabled={isLoading}
              data-testid="rename-input"
            />
            {error && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">
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
            <Button type="submit" disabled={isLoading || !name.trim()}>
              {isLoading ? 'Renaming...' : 'Rename'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default DesignActionsMenu;
