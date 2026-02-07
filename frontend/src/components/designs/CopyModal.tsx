/**
 * CopyModal Component
 *
 * Modal dialog for copying a design to the same or different project.
 * Supports copying with or without version history.
 */

import { Copy, FolderOpen } from 'lucide-react';
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

export interface CopyModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** The design being copied */
  design: Design | null;
  /** Available projects to copy to */
  projects: Project[];
  /** Callback when copy is confirmed */
  onConfirm: (options: {
    name: string;
    targetProjectId?: string;
    includeVersions: boolean;
  }) => Promise<void>;
  /** Whether a copy operation is in progress */
  isLoading?: boolean;
}

// =============================================================================
// Component
// =============================================================================

export function CopyModal({
  isOpen,
  onClose,
  design,
  projects,
  onConfirm,
  isLoading = false,
}: CopyModalProps) {
  const [name, setName] = useState('');
  const [targetProjectId, setTargetProjectId] = useState<string>('');
  const [includeVersions, setIncludeVersions] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when design changes
  React.useEffect(() => {
    if (design) {
      setName(`${design.name} (Copy)`);
      setTargetProjectId(design.project_id);
      setIncludeVersions(false);
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
      await onConfirm({
        name: trimmedName,
        targetProjectId: targetProjectId || undefined,
        includeVersions,
      });
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to copy design');
    }
  };

  const currentProject = projects.find((p) => p.id === design?.project_id);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Copy className="h-5 w-5" />
              Copy design
            </DialogTitle>
            <DialogDescription>
              Create a copy of "{design?.name}" in your library.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Name Input */}
            <div>
              <label
                htmlFor="copy-name"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Name
              </label>
              <input
                id="copy-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder="Copy name"
                autoFocus
                disabled={isLoading}
                data-testid="copy-name-input"
              />
            </div>

            {/* Project Selector */}
            <div>
              <label
                htmlFor="target-project"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Copy to project
              </label>
              <div className="relative mt-1">
                <FolderOpen className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <select
                  id="target-project"
                  value={targetProjectId}
                  onChange={(e) => setTargetProjectId(e.target.value)}
                  className="block w-full appearance-none rounded-md border border-gray-300 bg-white py-2 pl-10 pr-8 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                  disabled={isLoading}
                  data-testid="copy-project-select"
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                      {project.id === design?.project_id ? ' (current)' : ''}
                    </option>
                  ))}
                </select>
              </div>
              {currentProject && targetProjectId !== currentProject.id && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Moving from "{currentProject.name}" to "
                  {projects.find((p) => p.id === targetProjectId)?.name}"
                </p>
              )}
            </div>

            {/* Include Versions Checkbox */}
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                id="include-versions"
                checked={includeVersions}
                onChange={(e) => setIncludeVersions(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                disabled={isLoading}
                data-testid="copy-include-versions"
              />
              <div>
                <label
                  htmlFor="include-versions"
                  className="text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Include version history
                </label>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Copy all previous versions, not just the current one
                </p>
              </div>
            </div>

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
            <Button type="submit" disabled={isLoading || !name.trim()}>
              {isLoading ? 'Copying...' : 'Copy'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default CopyModal;
