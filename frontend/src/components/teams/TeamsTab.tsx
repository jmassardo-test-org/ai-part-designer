/**
 * TeamsTab Component
 *
 * Displays and manages teams within an organization.
 * Includes team list, create/edit modals, and member management.
 */

import {
  Users,
  Plus,
  MoreVertical,
  Pencil,
  Trash2,
  Crown,
  Shield,
  Loader2,
  AlertCircle,
  X,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { teamsApi, Team, TeamDetail, TeamRole } from '@/lib/api/teams';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface TeamsTabProps {
  orgId: string;
  isAdmin: boolean;
}

// =============================================================================
// Helper Components
// =============================================================================

function getRoleIcon(role: TeamRole) {
  switch (role) {
    case 'admin':
      return <Crown className="h-4 w-4 text-yellow-500" />;
    case 'lead':
      return <Shield className="h-4 w-4 text-blue-500" />;
    case 'member':
      return <Users className="h-4 w-4 text-green-500" />;
    default:
      return <Users className="h-4 w-4 text-gray-500" />;
  }
}

function getRoleLabel(role: TeamRole) {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

interface RoleSelectProps {
  value: TeamRole;
  onChange: (role: TeamRole) => void;
  disabled?: boolean;
}

function RoleSelect({ value, onChange, disabled }: RoleSelectProps) {
  const roles: TeamRole[] = ['member', 'lead', 'admin'];

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as TeamRole)}
      disabled={disabled}
      className="rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700"
    >
      {roles.map((role) => (
        <option key={role} value={role}>
          {getRoleLabel(role)}
        </option>
      ))}
    </select>
  );
}

// =============================================================================
// Create/Edit Team Modal
// =============================================================================

interface TeamModalProps {
  orgId: string;
  team?: Team | null;
  onClose: () => void;
  onSave: (team: Team) => void;
}

function TeamModal({ orgId, team, onClose, onSave }: TeamModalProps) {
  const [name, setName] = useState(team?.name || '');
  const [description, setDescription] = useState(team?.description || '');
  const [color, setColor] = useState(team?.settings?.color || '#3B82F6');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEditing = !!team;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      let savedTeam: Team;
      if (isEditing) {
        savedTeam = await teamsApi.update(orgId, team.id, {
          name,
          description: description || undefined,
          settings: { color },
        });
      } else {
        savedTeam = await teamsApi.create(orgId, {
          name,
          description: description || undefined,
          settings: { color },
        });
      }
      onSave(savedTeam);
    } catch {
      setError(isEditing ? 'Failed to update team' : 'Failed to create team');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {isEditing ? 'Edit Team' : 'Create Team'}
          </h2>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-red-600 dark:bg-red-900/20 dark:text-red-400">
            <AlertCircle className="h-5 w-5" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Team Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
              placeholder="e.g., Engineering, Design, Marketing"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
              placeholder="What does this team do?"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Team Color
            </label>
            <div className="mt-1 flex items-center gap-3">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="h-10 w-10 cursor-pointer rounded border-0"
              />
              <span className="text-sm text-gray-500">{color}</span>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-lg px-4 py-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !name.trim()}
              className={cn(
                'flex items-center gap-2 rounded-lg px-4 py-2 font-medium text-white',
                isSubmitting || !name.trim()
                  ? 'cursor-not-allowed bg-blue-400'
                  : 'bg-blue-600 hover:bg-blue-700'
              )}
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {isEditing ? 'Save Changes' : 'Create Team'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Team Detail Modal (View Members)
// =============================================================================

interface TeamDetailModalProps {
  orgId: string;
  teamId: string;
  onClose: () => void;
  isAdmin: boolean;
}

function TeamDetailModal({ orgId, teamId, onClose, isAdmin }: TeamDetailModalProps) {
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTeam = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await teamsApi.get(orgId, teamId);
      setTeam(data);
    } catch {
      setError('Failed to load team details');
    } finally {
      setIsLoading(false);
    }
  }, [orgId, teamId]);

  useEffect(() => {
    loadTeam();
  }, [loadTeam]);

  const handleRemoveMember = async (userId: string) => {
    if (!confirm('Are you sure you want to remove this member?')) return;
    try {
      await teamsApi.removeMember(orgId, teamId, userId);
      loadTeam();
    } catch {
      alert('Failed to remove member');
    }
  };

  const handleUpdateRole = async (userId: string, role: TeamRole) => {
    try {
      await teamsApi.updateMember(orgId, teamId, userId, { role });
      loadTeam();
    } catch {
      alert('Failed to update role');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-lg bg-white shadow-xl dark:bg-gray-800">
        <div className="flex items-center justify-between border-b p-4 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {team?.name || 'Team Details'}
          </h2>
          <button
            onClick={onClose}
            className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="max-h-[calc(80vh-80px)] overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center gap-2 py-8 text-red-500">
              <AlertCircle className="h-5 w-5" />
              {error}
            </div>
          ) : team ? (
            <div className="space-y-6">
              {/* Team Info */}
              <div>
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-12 w-12 items-center justify-center rounded-lg text-white"
                    style={{ backgroundColor: team.settings?.color || '#3B82F6' }}
                  >
                    <Users className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      {team.name}
                    </h3>
                    <p className="text-sm text-gray-500">
                      {team.members?.length || 0} members
                    </p>
                  </div>
                </div>
                {team.description && (
                  <p className="mt-3 text-gray-600 dark:text-gray-400">
                    {team.description}
                  </p>
                )}
              </div>

              {/* Members List */}
              <div>
                <h4 className="mb-3 font-medium text-gray-900 dark:text-white">
                  Members
                </h4>
                {team.members && team.members.length > 0 ? (
                  <div className="space-y-2">
                    {team.members.map((member) => (
                      <div
                        key={member.id}
                        className="flex items-center justify-between rounded-lg border p-3 dark:border-gray-700"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200 dark:bg-gray-700">
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">
                              {member.email?.charAt(0).toUpperCase() || '?'}
                            </span>
                          </div>
                          <div>
                            <p className="font-medium text-gray-900 dark:text-white">
                              {member.full_name || member.email}
                            </p>
                            <p className="text-sm text-gray-500">{member.email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {isAdmin ? (
                            <>
                              <RoleSelect
                                value={member.role}
                                onChange={(role) => handleUpdateRole(member.user_id, role)}
                              />
                              <button
                                onClick={() => handleRemoveMember(member.user_id)}
                                className="rounded p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </>
                          ) : (
                            <span className="flex items-center gap-1 text-sm text-gray-500">
                              {getRoleIcon(member.role)}
                              {getRoleLabel(member.role)}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-gray-500 py-4">
                    No members yet
                  </p>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Team Card
// =============================================================================

interface TeamCardProps {
  team: Team;
  onEdit: () => void;
  onDelete: () => void;
  onViewMembers: () => void;
  isAdmin: boolean;
}

function TeamCard({ team, onEdit, onDelete, onViewMembers, isAdmin }: TeamCardProps) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      className="relative rounded-lg border bg-white p-4 transition-shadow hover:shadow-md dark:border-gray-700 dark:bg-gray-800"
      onClick={onViewMembers}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-lg text-white"
            style={{ backgroundColor: team.settings?.color || '#3B82F6' }}
          >
            <Users className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">
              {team.name}
            </h3>
            <p className="text-sm text-gray-500">
              {team.member_count || 0} members
            </p>
          </div>
        </div>

        {isAdmin && (
          <div className="relative" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700"
            >
              <MoreVertical className="h-5 w-5" />
            </button>

            {showMenu && (
              <div className="absolute right-0 z-10 mt-1 w-40 rounded-lg border bg-white py-1 shadow-lg dark:border-gray-600 dark:bg-gray-700">
                <button
                  onClick={() => {
                    setShowMenu(false);
                    onEdit();
                  }}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-600"
                >
                  <Pencil className="h-4 w-4" />
                  Edit Team
                </button>
                <button
                  onClick={() => {
                    setShowMenu(false);
                    onDelete();
                  }}
                  className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete Team
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {team.description && (
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
          {team.description}
        </p>
      )}

      {!team.is_active && (
        <span className="mt-2 inline-block rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">
          Inactive
        </span>
      )}
    </div>
  );
}

// =============================================================================
// Main TeamsTab Component
// =============================================================================

export function TeamsTab({ orgId, isAdmin }: TeamsTabProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [viewingTeamId, setViewingTeamId] = useState<string | null>(null);

  const loadTeams = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await teamsApi.list(orgId);
      setTeams(response.items);
    } catch {
      setError('Failed to load teams');
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadTeams();
  }, [loadTeams]);

  const handleSaveTeam = (team: Team) => {
    if (editingTeam) {
      setTeams((prev) => prev.map((t) => (t.id === team.id ? team : t)));
    } else {
      setTeams((prev) => [...prev, team]);
    }
    setShowCreateModal(false);
    setEditingTeam(null);
  };

  const handleDeleteTeam = async (team: Team) => {
    if (!confirm(`Are you sure you want to delete "${team.name}"?`)) return;
    try {
      await teamsApi.delete(orgId, team.id);
      setTeams((prev) => prev.filter((t) => t.id !== team.id));
    } catch {
      alert('Failed to delete team');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="mt-2 text-gray-600 dark:text-gray-400">{error}</p>
        <button
          onClick={loadTeams}
          className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">
            Teams
          </h3>
          <p className="text-sm text-gray-500">
            Organize members into teams for better collaboration
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            Create Team
          </button>
        )}
      </div>

      {/* Teams Grid */}
      {teams.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {teams.map((team) => (
            <TeamCard
              key={team.id}
              team={team}
              isAdmin={isAdmin}
              onEdit={() => setEditingTeam(team)}
              onDelete={() => handleDeleteTeam(team)}
              onViewMembers={() => setViewingTeamId(team.id)}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-lg border-2 border-dashed border-gray-300 p-12 text-center dark:border-gray-600">
          <Users className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
            No teams yet
          </h3>
          <p className="mt-2 text-gray-500">
            Create teams to organize your organization members
          </p>
          {isAdmin && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              <Plus className="h-4 w-4" />
              Create First Team
            </button>
          )}
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateModal || editingTeam) && (
        <TeamModal
          orgId={orgId}
          team={editingTeam}
          onClose={() => {
            setShowCreateModal(false);
            setEditingTeam(null);
          }}
          onSave={handleSaveTeam}
        />
      )}

      {/* Team Detail Modal */}
      {viewingTeamId && (
        <TeamDetailModal
          orgId={orgId}
          teamId={viewingTeamId}
          isAdmin={isAdmin}
          onClose={() => setViewingTeamId(null)}
        />
      )}
    </div>
  );
}

export default TeamsTab;
