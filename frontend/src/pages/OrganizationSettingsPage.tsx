/**
 * Organization Settings Page
 *
 * Manage organization profile, members, invitations, and settings.
 */

import {
  Building2,
  Users,
  Mail,
  Settings,
  Shield,
  Crown,
  UserPlus,
  Trash2,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { TeamsTab } from '@/components/teams/TeamsTab';
import { useAuth } from '@/contexts/AuthContext';
import {
  organizationsApi,
  Organization,
  OrganizationMember,
  OrganizationInvite,
  OrganizationRole,
} from '@/lib/api/organizations';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

type Tab = 'general' | 'members' | 'teams' | 'invites' | 'settings';

// =============================================================================
// Helper Components
// =============================================================================

function getRoleIcon(role: OrganizationRole) {
  switch (role) {
    case 'owner':
      return <Crown className="h-4 w-4 text-yellow-500" />;
    case 'admin':
      return <Shield className="h-4 w-4 text-blue-500" />;
    case 'member':
      return <Users className="h-4 w-4 text-green-500" />;
    case 'viewer':
      return <Users className="h-4 w-4 text-gray-500" />;
  }
}

function getRoleLabel(role: OrganizationRole) {
  return role.charAt(0).toUpperCase() + role.slice(1);
}

interface RoleSelectProps {
  value: OrganizationRole;
  onChange: (role: OrganizationRole) => void;
  disabled?: boolean;
  excludeOwner?: boolean;
}

function RoleSelect({ value, onChange, disabled, excludeOwner = true }: RoleSelectProps) {
  const roles: OrganizationRole[] = excludeOwner
    ? ['admin', 'member', 'viewer']
    : ['owner', 'admin', 'member', 'viewer'];

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as OrganizationRole)}
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
// Tab Components
// =============================================================================

interface GeneralTabProps {
  org: Organization;
  onUpdate: (updates: Partial<Organization>) => Promise<void>;
}

function GeneralTab({ org, onUpdate }: GeneralTabProps) {
  const [name, setName] = useState(org.name);
  const [description, setDescription] = useState(org.description || '');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdate({ name, description });
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = name !== org.name || description !== (org.description || '');

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-4 text-lg font-medium text-gray-900 dark:text-white">
          Organization Profile
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Organization Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Slug
            </label>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-gray-500">app.example.com/org/</span>
              <span className="font-mono text-gray-900 dark:text-white">{org.slug}</span>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Slug cannot be changed after creation
            </p>
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
              placeholder="What does your organization do?"
            />
          </div>

          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className={cn(
              'rounded-lg px-4 py-2 font-medium',
              hasChanges && !isSaving
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'cursor-not-allowed bg-gray-200 text-gray-400'
            )}
          >
            {isSaving ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Saving...
              </span>
            ) : (
              'Save Changes'
            )}
          </button>
        </div>
      </div>

      <div className="border-t pt-6 dark:border-gray-700">
        <h3 className="mb-4 text-lg font-medium text-gray-900 dark:text-white">
          Plan & Limits
        </h3>
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-lg border bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800">
            <p className="text-sm text-gray-500">Plan</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {org.subscription_tier.charAt(0).toUpperCase() + org.subscription_tier.slice(1)}
            </p>
          </div>
          <div className="rounded-lg border bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800">
            <p className="text-sm text-gray-500">Members</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              {org.member_count} / {org.max_members}
            </p>
          </div>
          <div className="rounded-lg border bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800">
            <p className="text-sm text-gray-500">Projects</p>
            <p className="text-lg font-semibold text-gray-900 dark:text-white">
              - / {org.max_projects}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

interface MembersTabProps {
  orgId: string;
  currentUserId: string;
  isAdmin: boolean;
}

function MembersTab({ orgId, currentUserId, isAdmin }: MembersTabProps) {
  const [members, setMembers] = useState<OrganizationMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMembers = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await organizationsApi.listMembers(orgId);
      setMembers(data);
    } catch {
      setError('Failed to load members');
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const handleRoleChange = async (memberId: string, newRole: OrganizationRole) => {
    try {
      await organizationsApi.changeMemberRole(orgId, memberId, newRole);
      await loadMembers();
    } catch {
      setError('Failed to change role');
    }
  };

  const handleRemove = async (memberId: string) => {
    if (!confirm('Are you sure you want to remove this member?')) return;
    try {
      await organizationsApi.removeMember(orgId, memberId);
      await loadMembers();
    } catch {
      setError('Failed to remove member');
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Members ({members.length})
        </h3>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <div className="divide-y rounded-lg border dark:divide-gray-700 dark:border-gray-700">
        {members.map((member) => (
          <div
            key={member.id}
            className="flex items-center justify-between p-4"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-200 font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                {member.display_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {member.display_name}
                  {member.user_id === currentUserId && (
                    <span className="ml-2 text-xs text-gray-500">(you)</span>
                  )}
                </p>
                <p className="text-sm text-gray-500">{member.email}</p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                {getRoleIcon(member.role)}
                {isAdmin && member.role !== 'owner' ? (
                  <RoleSelect
                    value={member.role}
                    onChange={(role) => handleRoleChange(member.id, role)}
                    disabled={member.user_id === currentUserId}
                  />
                ) : (
                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    {getRoleLabel(member.role)}
                  </span>
                )}
              </div>

              {isAdmin && member.role !== 'owner' && member.user_id !== currentUserId && (
                <button
                  onClick={() => handleRemove(member.id)}
                  className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-500 dark:hover:bg-gray-700"
                  title="Remove member"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface InvitesTabProps {
  orgId: string;
  isAdmin: boolean;
}

function InvitesTab({ orgId, isAdmin }: InvitesTabProps) {
  const [invites, setInvites] = useState<OrganizationInvite[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showInviteForm, setShowInviteForm] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<OrganizationRole>('member');
  const [isSending, setIsSending] = useState(false);

  const loadInvites = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await organizationsApi.listInvites(orgId);
      setInvites(data);
    } catch {
      setError('Failed to load invites');
    } finally {
      setIsLoading(false);
    }
  }, [orgId]);

  useEffect(() => {
    loadInvites();
  }, [loadInvites]);

  const handleInvite = async () => {
    if (!inviteEmail) return;
    setIsSending(true);
    setError(null);
    try {
      await organizationsApi.inviteMember(orgId, {
        email: inviteEmail,
        role: inviteRole,
      });
      setInviteEmail('');
      setShowInviteForm(false);
      await loadInvites();
    } catch (err: unknown) {
      setError((err as { response?: { data?: { detail?: string } } }).response?.data?.detail || 'Failed to send invite');
    } finally {
      setIsSending(false);
    }
  };

  const handleRevoke = async (inviteId: string) => {
    if (!confirm('Are you sure you want to revoke this invitation?')) return;
    try {
      await organizationsApi.revokeInvite(orgId, inviteId);
      await loadInvites();
    } catch {
      setError('Failed to revoke invite');
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900 dark:text-white">
          Pending Invitations
        </h3>
        {isAdmin && (
          <button
            onClick={() => setShowInviteForm(!showInviteForm)}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            <UserPlus className="h-4 w-4" />
            Invite Member
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 p-3 text-red-700 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {showInviteForm && (
        <div className="mb-6 rounded-lg border bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800">
          <h4 className="mb-3 font-medium text-gray-900 dark:text-white">
            Send Invitation
          </h4>
          <div className="flex gap-3">
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="email@example.com"
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 dark:border-gray-600 dark:bg-gray-700"
            />
            <RoleSelect value={inviteRole} onChange={setInviteRole} />
            <button
              onClick={handleInvite}
              disabled={!inviteEmail || isSending}
              className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                'Send'
              )}
            </button>
          </div>
        </div>
      )}

      {invites.length === 0 ? (
        <div className="rounded-lg border border-dashed py-8 text-center dark:border-gray-700">
          <Mail className="mx-auto mb-2 h-8 w-8 text-gray-400" />
          <p className="text-gray-500">No pending invitations</p>
        </div>
      ) : (
        <div className="divide-y rounded-lg border dark:divide-gray-700 dark:border-gray-700">
          {invites.map((invite) => (
            <div
              key={invite.id}
              className="flex items-center justify-between p-4"
            >
              <div>
                <p className="font-medium text-gray-900 dark:text-white">
                  {invite.email}
                </p>
                <p className="text-sm text-gray-500">
                  Invited by {invite.invited_by_name} · Expires{' '}
                  {new Date(invite.expires_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <span className="rounded bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                  {getRoleLabel(invite.role)}
                </span>
                {isAdmin && (
                  <button
                    onClick={() => handleRevoke(invite.id)}
                    className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-red-500 dark:hover:bg-gray-700"
                    title="Revoke invitation"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface SettingsTabProps {
  org: Organization;
  onUpdate: (updates: { settings: Record<string, unknown> }) => Promise<void>;
  onDelete: () => Promise<void>;
  isOwner: boolean;
}

function SettingsTab({ org, onUpdate, onDelete, isOwner }: SettingsTabProps) {
  const [settings, setSettings] = useState(org.settings);
  const [isSaving, setIsSaving] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');
  
  // Feature permissions state
  const [features, setFeatures] = useState<{
    enabled: string[];
    available: string[];
    tier: string;
  } | null>(null);
  const [loadingFeatures, setLoadingFeatures] = useState(true);
  const [savingFeatures, setSavingFeatures] = useState(false);

  // Load feature permissions
  useEffect(() => {
    const loadFeatures = async () => {
      try {
        const data = await organizationsApi.getFeatures(org.id);
        setFeatures({
          enabled: data.enabled_features,
          available: data.available_features,
          tier: data.subscription_tier,
        });
      } catch (err) {
        console.error('Failed to load features:', err);
      } finally {
        setLoadingFeatures(false);
      }
    };
    loadFeatures();
  }, [org.id]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onUpdate({ settings });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (deleteConfirmText !== org.name) return;
    await onDelete();
  };

  const handleToggleFeature = async (feature: string) => {
    if (!features) return;
    
    const newEnabled = features.enabled.includes(feature)
      ? features.enabled.filter(f => f !== feature)
      : [...features.enabled, feature];

    setSavingFeatures(true);
    try {
      const updated = await organizationsApi.updateFeatures(org.id, {
        enabled_features: newEnabled,
      });
      setFeatures({
        enabled: updated.enabled_features,
        available: updated.available_features,
        tier: updated.subscription_tier,
      });
    } catch (err) {
      console.error('Failed to update features:', err);
    } finally {
      setSavingFeatures(false);
    }
  };

  // Feature labels for display
  // TODO: Consider creating a backend endpoint to return feature metadata
  // to avoid duplication and maintain single source of truth
  const featureLabels: Record<string, { name: string; description: string }> = {
    ai_generation: {
      name: 'AI Generation',
      description: 'AI-powered part generation from natural language',
    },
    ai_chat: {
      name: 'AI Chat',
      description: 'Conversational AI interface for design',
    },
    direct_generation: {
      name: 'Direct Generation',
      description: 'Direct CAD generation without chat',
    },
    templates: {
      name: 'Templates',
      description: 'Access to design templates',
    },
    custom_templates: {
      name: 'Custom Templates',
      description: 'Create and manage custom templates',
    },
    assemblies: {
      name: 'Assemblies',
      description: 'Multi-part assemblies',
    },
    advanced_cad: {
      name: 'Advanced CAD',
      description: 'Advanced CAD operations',
    },
    design_sharing: {
      name: 'Design Sharing',
      description: 'Share designs with others',
    },
    teams: {
      name: 'Teams',
      description: 'Team collaboration features',
    },
    comments: {
      name: 'Comments',
      description: 'Design comments and annotations',
    },
    version_history: {
      name: 'Version History',
      description: 'Track design versions',
    },
    export_step: {
      name: 'STEP Export',
      description: 'Export designs to STEP format',
    },
    export_stl: {
      name: 'STL Export',
      description: 'Export designs to STL format',
    },
    export_dxf: {
      name: 'DXF Export',
      description: 'Export designs to DXF format',
    },
    export_drawings: {
      name: 'Technical Drawings',
      description: 'Generate technical drawings',
    },
    bom: {
      name: 'Bill of Materials',
      description: 'Generate BOMs for designs',
    },
    cost_estimation: {
      name: 'Cost Estimation',
      description: 'Estimate manufacturing costs',
    },
    file_uploads: {
      name: 'File Uploads',
      description: 'Upload reference files',
    },
    external_storage: {
      name: 'External Storage',
      description: 'Integration with cloud storage',
    },
  };

  return (
    <div className="space-y-8">
      {/* Organization Settings */}
      <div>
        <h3 className="mb-4 text-lg font-medium text-gray-900 dark:text-white">
          Organization Settings
        </h3>

        <div className="space-y-4">
          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={Boolean(settings.allow_member_invites)}
              onChange={(e) =>
                setSettings({ ...settings, allow_member_invites: e.target.checked })
              }
              className="rounded"
            />
            <span className="text-gray-700 dark:text-gray-300">
              Allow members to invite others
            </span>
          </label>

          <label className="flex items-center gap-3">
            <input
              type="checkbox"
              checked={Boolean(settings.require_2fa)}
              onChange={(e) =>
                setSettings({ ...settings, require_2fa: e.target.checked })
              }
              className="rounded"
            />
            <span className="text-gray-700 dark:text-gray-300">
              Require two-factor authentication
            </span>
          </label>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className="rounded-lg bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>

      {/* Feature Permissions */}
      {isOwner && (
        <div className="border-t pt-8 dark:border-gray-700">
          <div className="mb-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              Feature Permissions
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              Control which features are enabled for your organization.
              {features && (
                <span className="ml-1">
                  Available on <strong>{features.tier}</strong> tier.
                </span>
              )}
            </p>
          </div>

          {loadingFeatures ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
            </div>
          ) : features ? (
            <div className="space-y-3">
              {features.available.map((feature) => {
                const info = featureLabels[feature] || {
                  name: feature,
                  description: '',
                };
                const isEnabled = features.enabled.includes(feature);

                return (
                  <label
                    key={feature}
                    className="flex items-start gap-3 rounded-lg border p-4 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-700/50"
                  >
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={() => handleToggleFeature(feature)}
                      disabled={savingFeatures}
                      className="mt-1 rounded"
                    />
                    <div className="flex-1">
                      <div className="font-medium text-gray-900 dark:text-white">
                        {info.name}
                      </div>
                      {info.description && (
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {info.description}
                        </div>
                      )}
                    </div>
                  </label>
                );
              })}
              {features.available.length === 0 && (
                <p className="text-center text-gray-500">
                  No features available on your current tier.
                </p>
              )}
            </div>
          ) : (
            <div className="rounded-lg bg-red-50 p-4 text-red-700 dark:bg-red-900/20 dark:text-red-400">
              Failed to load features. Please try again.
            </div>
          )}
        </div>
      )}

      {/* Danger Zone */}
      {isOwner && (
        <div className="border-t pt-8 dark:border-gray-700">
          <h3 className="mb-4 text-lg font-medium text-red-600">Danger Zone</h3>

          <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-900/20">
            <h4 className="font-medium text-red-700 dark:text-red-400">
              Delete Organization
            </h4>
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              This action cannot be undone. All projects and data will be
              permanently deleted.
            </p>

            {!showDeleteConfirm ? (
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="mt-4 rounded-lg border border-red-500 px-4 py-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30"
              >
                Delete Organization
              </button>
            ) : (
              <div className="mt-4 space-y-3">
                <p className="text-sm text-red-600 dark:text-red-400">
                  Type <strong>{org.name}</strong> to confirm:
                </p>
                <input
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  className="w-full rounded-lg border border-red-300 px-3 py-2"
                />
                <div className="flex gap-2">
                  <button
                    onClick={handleDelete}
                    disabled={deleteConfirmText !== org.name}
                    className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Delete Forever
                  </button>
                  <button
                    onClick={() => {
                      setShowDeleteConfirm(false);
                      setDeleteConfirmText('');
                    }}
                    className="rounded-lg border px-4 py-2 text-gray-600 hover:bg-gray-50 dark:text-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export function OrganizationSettingsPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [org, setOrg] = useState<Organization | null>(null);
  const [membership, setMembership] = useState<OrganizationMember | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('general');

  const currentUserId = user?.id;
  const isAdmin = membership?.role === 'admin' || membership?.role === 'owner';
  const isOwner = org?.owner_id === currentUserId;

  const loadOrg = useCallback(async () => {
    if (!orgId || !currentUserId) return;
    setIsLoading(true);
    try {
      const [orgData, membershipData] = await Promise.all([
        organizationsApi.get(orgId),
        organizationsApi.getCurrentUserMembership(orgId),
      ]);
      setOrg(orgData);
      setMembership(membershipData);
    } catch {
      setError('Failed to load organization');
    } finally {
      setIsLoading(false);
    }
  }, [orgId, currentUserId]);

  useEffect(() => {
    loadOrg();
  }, [loadOrg]);

  const handleUpdate = async (updates: Partial<Organization>) => {
    if (!orgId) return;
    const updated = await organizationsApi.update(orgId, {
      name: updates.name,
      description: updates.description ?? undefined,
      logo_url: updates.logo_url ?? undefined,
      settings: updates.settings,
    });
    setOrg(updated);
  };

  const handleDelete = async () => {
    if (!orgId) return;
    await organizationsApi.delete(orgId);
    navigate('/organizations');
  };

  if (isLoading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  if (error || !org) {
    return (
      <div className="flex h-[50vh] flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-red-500" />
        <p className="text-gray-600">{error || 'Organization not found'}</p>
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'general', label: 'General', icon: <Building2 className="h-4 w-4" /> },
    { id: 'members', label: 'Members', icon: <Users className="h-4 w-4" /> },
    { id: 'teams', label: 'Teams', icon: <Users className="h-4 w-4" /> },
    { id: 'invites', label: 'Invites', icon: <Mail className="h-4 w-4" /> },
    { id: 'settings', label: 'Settings', icon: <Settings className="h-4 w-4" /> },
  ];

  return (
    <div className="container mx-auto max-w-4xl px-4 py-8">
      <div className="mb-8">
        <div className="flex items-center gap-3">
          {org.logo_url ? (
            <img
              src={org.logo_url}
              alt={org.name}
              className="h-12 w-12 rounded-lg"
            />
          ) : (
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400">
              <Building2 className="h-6 w-6" />
            </div>
          )}
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {org.name}
            </h1>
            <p className="text-gray-500">Organization Settings</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex border-b border-gray-200 dark:border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors',
              activeTab === tab.id
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="rounded-lg border bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        {activeTab === 'general' && (
          <GeneralTab org={org} onUpdate={handleUpdate} />
        )}
        {activeTab === 'members' && (
          <MembersTab
            orgId={org.id}
            currentUserId={currentUserId}
            isAdmin={isAdmin}
          />
        )}
        {activeTab === 'teams' && (
          <TeamsTab orgId={org.id} isAdmin={isAdmin} />
        )}
        {activeTab === 'invites' && (
          <InvitesTab orgId={org.id} isAdmin={isAdmin} />
        )}
        {activeTab === 'settings' && (
          <SettingsTab
            org={org}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
            isOwner={isOwner}
          />
        )}
      </div>
    </div>
  );
}

export default OrganizationSettingsPage;
