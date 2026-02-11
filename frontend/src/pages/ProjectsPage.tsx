/**
 * Projects Page - Manage user projects and organize designs.
 */

import {
  FolderPlus,
  Folder,
  FolderOpen,
  MoreVertical,
  Edit2,
  Trash2,
  FileBox,
  Clock,
  Search,
  Grid3X3,
  List,
  ChevronRight,
  X,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface Project {
  id: string;
  name: string;
  description: string | null;
  design_count: number;
  created_at: string;
  updated_at: string;
  team_id?: string | null;
  team_name?: string | null;
}

interface Design {
  id: string;
  name: string;
  thumbnail_url: string | null;
  created_at: string;
  updated_at: string;
}

interface Team {
  id: string;
  name: string;
  organization_id: string;
}

// =============================================================================
// Projects Page Component
// =============================================================================

export function ProjectsPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();

  // State
  const [projects, setProjects] = useState<Project[]>([]);
  const [designs, setDesigns] = useState<Design[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Teams state
  const [availableTeams, setAvailableTeams] = useState<Team[]>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');

  // Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [projectToEdit, setProjectToEdit] = useState<Project | null>(null);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);

  // Form state
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch projects
  const fetchProjects = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/projects`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch projects');

      const data = await response.json();
      // Backend returns { projects: [...], total, page, per_page }
      const projectsList = Array.isArray(data) ? data : (data.projects || data.items || []);
      setProjects(projectsList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  // Fetch available teams
  const fetchAvailableTeams = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/projects/available-teams`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        // If endpoint fails, just continue without teams
        console.warn('Failed to fetch teams, continuing without team selector');
        return;
      }

      const teams = await response.json();
      setAvailableTeams(teams || []);
    } catch (err) {
      console.warn('Error fetching teams:', err);
      // Continue without teams
    }
  }, [token]);

  // Fetch designs for selected project
  const fetchProjectDesigns = useCallback(async (projectId: string) => {
    try {
      const response = await fetch(`${API_BASE}/projects/${projectId}/designs`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch designs');

      const data = await response.json();
      setDesigns(data.items || data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load designs');
    }
  }, [token]);

  // Load projects on mount
  useEffect(() => {
    fetchProjects();
    fetchAvailableTeams();
  }, [fetchProjects, fetchAvailableTeams]);

  // Load project details if projectId in URL
  useEffect(() => {
    if (projectId && projects.length > 0) {
      const project = projects.find(p => p.id === projectId);
      if (project) {
        setSelectedProject(project);
        fetchProjectDesigns(projectId);
      }
    } else {
      setSelectedProject(null);
      setDesigns([]);
    }
  }, [projectId, projects, fetchProjectDesigns]);

  // Create project
  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      setIsSubmitting(true);
      const response = await fetch(`${API_BASE}/projects`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: newProjectName,
          description: newProjectDescription || null,
        }),
      });

      if (!response.ok) throw new Error('Failed to create project');

      const project = await response.json();
      setProjects([project, ...projects]);
      setShowCreateModal(false);
      setNewProjectName('');
      setNewProjectDescription('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Update project
  const handleUpdateProject = async () => {
    if (!projectToEdit || !newProjectName.trim()) return;

    try {
      setIsSubmitting(true);
      const body: any = {
        name: newProjectName,
        description: newProjectDescription || null,
      };

      // Include team_id if a team is selected
      if (selectedTeamId) {
        body.team_id = selectedTeamId;
      }

      const response = await fetch(`${API_BASE}/projects/${projectToEdit.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (!response.ok) throw new Error('Failed to update project');

      const updated = await response.json();
      setProjects(projects.map(p => p.id === updated.id ? updated : p));
      setShowEditModal(false);
      setProjectToEdit(null);
      setNewProjectName('');
      setNewProjectDescription('');
      setSelectedTeamId('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update project');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Delete project
  const handleDeleteProject = async () => {
    if (!projectToDelete) return;

    try {
      setIsSubmitting(true);
      const response = await fetch(`${API_BASE}/projects/${projectToDelete.id}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to delete project');

      setProjects(projects.filter(p => p.id !== projectToDelete.id));
      setShowDeleteModal(false);
      setProjectToDelete(null);

      // Navigate away if viewing deleted project
      if (selectedProject?.id === projectToDelete.id) {
        navigate('/projects');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Open edit modal
  const openEditModal = (project: Project) => {
    setProjectToEdit(project);
    setNewProjectName(project.name);
    setNewProjectDescription(project.description || '');
    setSelectedTeamId(project.team_id || '');
    setShowEditModal(true);
  };

  // Filter projects by search
  const filteredProjects = projects.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter designs by search
  const filteredDesigns = designs.filter(d =>
    d.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Format date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {selectedProject ? (
            <>
              <button
                onClick={() => navigate('/projects')}
                className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              >
                Projects
              </button>
              <ChevronRight className="w-4 h-4 text-gray-400" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                {selectedProject.name}
              </h1>
            </>
          ) : (
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Projects</h1>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder={selectedProject ? "Search designs..." : "Search projects..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
            />
          </div>

          {/* View Toggle */}
          <div className="flex bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-white dark:bg-gray-600 shadow' : ''}`}
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-white dark:bg-gray-600 shadow' : ''}`}
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* Create Button */}
          {!selectedProject && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <FolderPlus className="w-4 h-4" />
              New Project
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Loading */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
        </div>
      ) : selectedProject ? (
        /* Project Detail View */
        <div>
          {/* Project Info */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4 mb-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-gray-600 dark:text-gray-400">{selectedProject.description || 'No description'}</p>
                <div className="flex items-center gap-4 mt-2 text-sm text-gray-500 dark:text-gray-400">
                  <span className="flex items-center gap-1">
                    <FileBox className="w-4 h-4" />
                    {selectedProject.design_count} designs
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    Updated {formatDate(selectedProject.updated_at)}
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => openEditModal(selectedProject)}
                  className="p-2 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <Edit2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    setProjectToDelete(selectedProject);
                    setShowDeleteModal(true);
                  }}
                  className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>

          {/* Designs Grid/List */}
          {filteredDesigns.length === 0 ? (
            <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <FileBox className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-gray-400">No designs in this project</p>
              <button
                onClick={() => navigate('/create')}
                className="mt-4 text-primary-600 hover:underline"
              >
                Create a design
              </button>
            </div>
          ) : viewMode === 'grid' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredDesigns.map(design => (
                <div
                  key={design.id}
                  onClick={() => navigate(`/designs/${design.id}`)}
                  className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 hover:shadow-md transition-shadow cursor-pointer"
                >
                  <div className="aspect-square bg-gray-100 dark:bg-gray-700 rounded-t-lg flex items-center justify-center">
                    {design.thumbnail_url ? (
                      <img
                        src={design.thumbnail_url}
                        alt={design.name}
                        className="w-full h-full object-cover rounded-t-lg"
                      />
                    ) : (
                      <FileBox className="w-12 h-12 text-gray-300" />
                    )}
                  </div>
                  <div className="p-3">
                    <h3 className="font-medium truncate text-gray-900 dark:text-gray-100">{design.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{formatDate(design.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 divide-y dark:divide-gray-700">
              {filteredDesigns.map(design => (
                <div
                  key={design.id}
                  onClick={() => navigate(`/designs/${design.id}`)}
                  className="flex items-center gap-4 p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
                >
                  <div className="w-12 h-12 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center">
                    {design.thumbnail_url ? (
                      <img
                        src={design.thumbnail_url}
                        alt={design.name}
                        className="w-full h-full object-cover rounded"
                      />
                    ) : (
                      <FileBox className="w-6 h-6 text-gray-300" />
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900 dark:text-gray-100">{design.name}</h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{formatDate(design.created_at)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        /* Projects List */
        filteredProjects.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <Folder className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-gray-500 dark:text-gray-400">
              {searchQuery ? 'No projects match your search' : 'No projects yet'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="mt-4 text-primary-600 hover:underline"
              >
                Create your first project
              </button>
            )}
          </div>
        ) : viewMode === 'grid' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filteredProjects.map(project => (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4 hover:shadow-md transition-shadow cursor-pointer group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="p-2 bg-primary-50 dark:bg-primary-900/30 rounded-lg">
                    <FolderOpen className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      openEditModal(project);
                    }}
                    className="p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                  >
                    <MoreVertical className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                  </button>
                </div>
                <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">{project.name}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-1">
                  {project.description || 'No description'}
                </p>
                <div className="flex items-center gap-3 mt-3 text-xs text-gray-400 dark:text-gray-500">
                  <span>{project.design_count} designs</span>
                  <span>•</span>
                  <span>{formatDate(project.updated_at)}</span>
                  {project.team_name && (
                    <>
                      <span>•</span>
                      <span className="text-primary-600 dark:text-primary-400">{project.team_name}</span>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 divide-y dark:divide-gray-700">
            {filteredProjects.map(project => (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="flex items-center gap-4 p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer group"
              >
                <div className="p-2 bg-primary-50 dark:bg-primary-900/30 rounded-lg">
                  <FolderOpen className="w-6 h-6 text-primary-600 dark:text-primary-400" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-gray-900 dark:text-gray-100">{project.name}</h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {project.description || 'No description'}
                  </p>
                  {project.team_name && (
                    <p className="text-xs text-primary-600 dark:text-primary-400 mt-1">
                      Team: {project.team_name}
                    </p>
                  )}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {project.design_count} designs
                </div>
                <div className="text-sm text-gray-400 dark:text-gray-500">
                  {formatDate(project.updated_at)}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    openEditModal(project);
                  }}
                  className="p-1 opacity-0 group-hover:opacity-100 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <MoreVertical className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                </button>
              </div>
            ))}
          </div>
        )
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Create Project</h2>
              <button onClick={() => setShowCreateModal(false)}>
                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="My Project"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description (optional)
                </label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  placeholder="What's this project about?"
                  rows={3}
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateProject}
                disabled={!newProjectName.trim() || isSubmitting}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Creating...' : 'Create Project'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Project Modal */}
      {showEditModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Edit Project</h2>
              <button onClick={() => setShowEditModal(false)}>
                <X className="w-5 h-5 text-gray-500 dark:text-gray-400" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Project Name
                </label>
                <input
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description (optional)
                </label>
                <textarea
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  rows={3}
                />
              </div>
              {availableTeams.length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Team (optional)
                  </label>
                  <select
                    value={selectedTeamId}
                    onChange={(e) => setSelectedTeamId(e.target.value)}
                    className="w-full px-3 py-2 border dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">No team</option>
                    {availableTeams.map((team) => (
                      <option key={team.id} value={team.id}>
                        {team.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateProject}
                disabled={!newProjectName.trim() || isSubmitting}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteModal && projectToDelete && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-full">
                <Trash2 className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Delete Project</h2>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Are you sure you want to delete <strong>{projectToDelete.name}</strong>? 
              This will also delete all {projectToDelete.design_count} designs in this project.
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteProject}
                disabled={isSubmitting}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {isSubmitting ? 'Deleting...' : 'Delete Project'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ProjectsPage;
