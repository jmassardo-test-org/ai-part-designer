/**
 * Save Design Modal Component.
 * 
 * Modal for saving a completed generation job as a permanent design.
 * Allows user to name the design and select a project.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Save,
  X,
  FolderPlus,
  Folder,
  Loader2,
  Check,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import type { Job } from '@/types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface Project {
  id: string;
  name: string;
  description: string | null;
  design_count: number;
}

interface SaveDesignModalProps {
  job: Job;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (designId: string, projectId: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function SaveDesignModal({
  job,
  isOpen,
  onClose,
  onSaved,
}: SaveDesignModalProps) {
  const { token } = useAuth();

  // Form state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');

  // Projects state
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoadingProjects, setIsLoadingProjects] = useState(false);

  // Create project state
  const [showCreateProject, setShowCreateProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [isCreatingProject, setIsCreatingProject] = useState(false);

  // Save state
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Generate default name from job
  useEffect(() => {
    if (isOpen && job) {
      // Try to extract a name from the job input
      const prompt = job.input_params?.prompt || '';
      const style = job.input_params?.style || '';
      
      let defaultName = 'Untitled Design';
      if (prompt) {
        // Take first 50 chars of prompt as name
        defaultName = prompt.substring(0, 50).trim();
        if (prompt.length > 50) defaultName += '...';
      } else if (style) {
        defaultName = `${style} Part`;
      }
      
      setName(defaultName);
      setDescription('');
      setSelectedProjectId(null);
      setTags([]);
      setError(null);
      setSuccess(false);
    }
  }, [isOpen, job]);

  // Fetch projects
  const fetchProjects = useCallback(async () => {
    if (!token) return;

    setIsLoadingProjects(true);
    try {
      const response = await fetch(`${API_BASE}/projects`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setProjects(data.projects || data.items || data);
        
        // Pre-select default project if exists
        const defaultProject = (data.projects || data.items || data).find(
          (p: Project) => p.name === 'My Designs'
        );
        if (defaultProject) {
          setSelectedProjectId(defaultProject.id);
        }
      }
    } catch (err) {
      console.error('Failed to fetch projects:', err);
    } finally {
      setIsLoadingProjects(false);
    }
  }, [token]);

  // Load projects when modal opens
  useEffect(() => {
    if (isOpen) {
      fetchProjects();
    }
  }, [isOpen, fetchProjects]);

  // Create new project
  const handleCreateProject = async () => {
    if (!newProjectName.trim() || !token) return;

    setIsCreatingProject(true);
    try {
      const response = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newProjectName,
          description: null,
        }),
      });

      if (response.ok) {
        const project = await response.json();
        setProjects([project, ...projects]);
        setSelectedProjectId(project.id);
        setNewProjectName('');
        setShowCreateProject(false);
      } else {
        throw new Error('Failed to create project');
      }
    } catch (err) {
      setError('Failed to create project');
    } finally {
      setIsCreatingProject(false);
    }
  };

  // Add tag
  const handleAddTag = () => {
    const tag = tagInput.trim().toLowerCase();
    if (tag && !tags.includes(tag) && tags.length < 10) {
      setTags([...tags, tag]);
      setTagInput('');
    }
  };

  // Remove tag
  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter(t => t !== tagToRemove));
  };

  // Save design
  const handleSave = async () => {
    if (!name.trim() || !token) return;

    setIsSaving(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/jobs/${job.id}/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: name.trim(),
          description: description.trim() || null,
          project_id: selectedProjectId,
          tags,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to save design');
      }

      const result = await response.json();
      setSuccess(true);

      // Notify parent after a brief delay to show success state
      setTimeout(() => {
        onSaved(result.design_id, result.project_id);
        onClose();
      }, 1000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save design');
    } finally {
      setIsSaving(false);
    }
  };

  // Handle backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !isSaving) {
      onClose();
    }
  };

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isSaving) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, isSaving, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-design-title"
    >
      <div className="w-full max-w-lg bg-white rounded-xl shadow-xl max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary-100 rounded-lg">
              <Save className="w-5 h-5 text-primary-600" />
            </div>
            <h2 id="save-design-title" className="text-lg font-semibold text-gray-900">
              Save Design
            </h2>
          </div>
          <button
            onClick={onClose}
            disabled={isSaving}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-lg transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4 space-y-4 overflow-y-auto max-h-[60vh]">
          {/* Success state */}
          {success && (
            <div className="flex items-center gap-3 p-4 bg-green-50 rounded-lg">
              <Check className="w-5 h-5 text-green-600" />
              <span className="text-green-700 font-medium">Design saved successfully!</span>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-50 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <span className="text-red-700">{error}</span>
            </div>
          )}

          {/* Preview thumbnail */}
          {job.result?.thumbnail_url && (
            <div className="flex justify-center">
              <img
                src={job.result.thumbnail_url}
                alt="Design preview"
                className="w-48 h-48 object-contain bg-gray-100 rounded-lg"
              />
            </div>
          )}

          {/* Name */}
          <div>
            <label htmlFor="design-name" className="block text-sm font-medium text-gray-700 mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              id="design-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter design name"
              maxLength={255}
              disabled={isSaving || success}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-50"
            />
          </div>

          {/* Description */}
          <div>
            <label htmlFor="design-description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              id="design-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional description..."
              rows={3}
              maxLength={2000}
              disabled={isSaving || success}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-50 resize-none"
            />
          </div>

          {/* Project selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Save to Project
            </label>

            {isLoadingProjects ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
              </div>
            ) : (
              <div className="space-y-2">
                {/* Project list */}
                <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                  {projects.map((project) => (
                    <button
                      key={project.id}
                      onClick={() => setSelectedProjectId(project.id)}
                      disabled={isSaving || success}
                      className={`flex items-center gap-2 p-3 rounded-lg border text-left transition-colors ${
                        selectedProjectId === project.id
                          ? 'border-primary-500 bg-primary-50 text-primary-700'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      } disabled:opacity-50`}
                    >
                      <Folder className={`w-4 h-4 flex-shrink-0 ${
                        selectedProjectId === project.id ? 'text-primary-600' : 'text-gray-400'
                      }`} />
                      <div className="min-w-0">
                        <div className="font-medium text-sm truncate">{project.name}</div>
                        <div className="text-xs text-gray-500">
                          {project.design_count} design{project.design_count !== 1 ? 's' : ''}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>

                {/* Create new project */}
                {showCreateProject ? (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newProjectName}
                      onChange={(e) => setNewProjectName(e.target.value)}
                      placeholder="New project name"
                      disabled={isCreatingProject}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreateProject();
                        if (e.key === 'Escape') setShowCreateProject(false);
                      }}
                    />
                    <button
                      onClick={handleCreateProject}
                      disabled={!newProjectName.trim() || isCreatingProject}
                      className="px-3 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isCreatingProject ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        'Create'
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setShowCreateProject(false);
                        setNewProjectName('');
                      }}
                      className="px-3 py-2 text-gray-600 hover:text-gray-800"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowCreateProject(true)}
                    disabled={isSaving || success}
                    className="flex items-center gap-2 w-full p-3 border border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-gray-400 hover:text-gray-700 transition-colors disabled:opacity-50"
                  >
                    <FolderPlus className="w-4 h-4" />
                    <span className="text-sm">Create new project</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Tags
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 rounded-md text-sm"
                >
                  {tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    disabled={isSaving || success}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                placeholder="Add a tag..."
                disabled={isSaving || success || tags.length >= 10}
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-50"
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddTag();
                  }
                }}
              />
              <button
                onClick={handleAddTag}
                disabled={!tagInput.trim() || isSaving || success || tags.length >= 10}
                className="px-3 py-2 text-primary-600 hover:text-primary-700 font-medium text-sm disabled:opacity-50"
              >
                Add
              </button>
            </div>
            {tags.length >= 10 && (
              <p className="mt-1 text-xs text-gray-500">Maximum 10 tags</p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t bg-gray-50">
          <button
            onClick={onClose}
            disabled={isSaving}
            className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || isSaving || success}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : success ? (
              <>
                <Check className="w-4 h-4" />
                Saved!
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Design
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

export default SaveDesignModal;
