/**
 * MoveModal Component
 *
 * Modal dialog for moving a design to a different project.
 */

import { FolderInput, FolderOpen } from 'lucide-react';
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
import type { Design, Project } from '@/lib/designs';

// =============================================================================
// Types
// =============================================================================

export interface MoveModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** The design being moved */
  design: Design | null;
  /** Available projects to move to */
  projects: Project[];
  /** Callback when move is confirmed */
  onConfirm: (targetProjectId: string) => Promise<void>;
  /** Whether a move operation is in progress */
  isLoading?: boolean;
}

// =============================================================================
// Component
// =============================================================================

export function MoveModal({
  isOpen,
  onClose,
  design,
  projects,
  onConfirm,
  isLoading = false,
}: MoveModalProps) {
  const [targetProjectId, setTargetProjectId] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  // Filter out the current project
  const availableProjects = projects.filter(
    (p) => p.id !== design?.project_id
  );

  // Reset state when design changes
  React.useEffect(() => {
    if (design && availableProjects.length > 0) {
      setTargetProjectId(availableProjects[0].id);
      setError(null);
    }
  }, [design, availableProjects.length]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!targetProjectId) {
      setError('Please select a project');
      return;
    }

    if (targetProjectId === design?.project_id) {
      setError('Design is already in this project');
      return;
    }

    try {
      await onConfirm(targetProjectId);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to move design');
    }
  };

  const currentProject = projects.find((p) => p.id === design?.project_id);
  const targetProject = projects.find((p) => p.id === targetProjectId);

  // If no other projects available, show message
  if (availableProjects.length === 0) {
    return (
      <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderInput className="h-5 w-5" />
              Move design
            </DialogTitle>
            <DialogDescription>
              You need at least two projects to move designs between them.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Create another project first, then you can move designs between
              projects.
            </p>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FolderInput className="h-5 w-5" />
              Move design
            </DialogTitle>
            <DialogDescription>
              Move "{design?.name}" to a different project.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Current Project Display */}
            <div>
              <span className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Current project
              </span>
              <div className="mt-1 flex items-center gap-2 rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-600 dark:bg-gray-800 dark:text-gray-400">
                <FolderOpen className="h-4 w-4" />
                {currentProject?.name || 'Unknown'}
              </div>
            </div>

            {/* Target Project Selector */}
            <div>
              <label
                htmlFor="move-target-project"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Move to
              </label>
              <div className="relative mt-1">
                <FolderOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <select
                  id="move-target-project"
                  value={targetProjectId}
                  onChange={(e) => setTargetProjectId(e.target.value)}
                  className="block w-full appearance-none rounded-md border border-gray-300 bg-white py-2 pl-10 pr-8 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  disabled={isLoading}
                  data-testid="move-project-select"
                >
                  {availableProjects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name} ({project.design_count} designs)
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Preview */}
            {targetProject && (
              <div className="rounded-md bg-indigo-50 p-3 dark:bg-indigo-900/20">
                <p className="text-sm text-indigo-700 dark:text-indigo-300">
                  <strong>{design?.name}</strong> will be moved from{' '}
                  <strong>{currentProject?.name}</strong> to{' '}
                  <strong>{targetProject.name}</strong>
                </p>
              </div>
            )}

            {/* Error Message */}
            {error && (
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
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
            <Button type="submit" disabled={isLoading || !targetProjectId}>
              {isLoading ? 'Moving...' : 'Move'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default MoveModal;
