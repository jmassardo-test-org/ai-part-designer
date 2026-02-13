/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Organizations API client.
 *
 * Handles organization management, members, and invitations.
 */

/** Organization role type. */
export type OrganizationRole = 'owner' | 'admin' | 'member' | 'viewer';

/** Organization entity. */
export interface Organization {
  [key: string]: any;
  id: string;
  name: string;
  slug: string;
  description?: string;
  logo_url?: string;
  created_at: string;
  updated_at: string;
  member_count?: number;
  plan?: string;
}

/** Organization member. */
export interface OrganizationMember {
  [key: string]: any;
  id: string;
  user_id: string;
  email: string;
  name?: string;
  display_name?: string;
  role: OrganizationRole;
  joined_at: string;
  avatar_url?: string;
  invited_by_name?: string | null;
}

/** Organization invite. */
export interface OrganizationInvite {
  [key: string]: any;
  id: string;
  email: string;
  role: OrganizationRole;
  invited_by: string;
  created_at: string;
  expires_at: string;
  status: string;
}

/** Organizations API methods. */
export const organizationsApi: any = {
  async list(token?: string): Promise<Organization[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch('/api/v1/organizations', { headers });
    if (!resp.ok) throw new Error(`Failed to list organizations: ${resp.status}`);
    return resp.json();
  },
  async get(orgId: string, token?: string): Promise<Organization> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}`, { headers });
    if (!resp.ok) throw new Error(`Failed to get organization: ${resp.status}`);
    return resp.json();
  },
  async update(orgId: string, data: Partial<Organization>, token?: string): Promise<Organization> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Failed to update organization: ${resp.status}`);
    return resp.json();
  },
  async listMembers(orgId: string, token?: string): Promise<OrganizationMember[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/members`, { headers });
    if (!resp.ok) throw new Error(`Failed to list members: ${resp.status}`);
    return resp.json();
  },
  async inviteMember(orgId: string, email: string, role: OrganizationRole, token?: string): Promise<OrganizationInvite> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/invites`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ email, role }),
    });
    if (!resp.ok) throw new Error(`Failed to invite member: ${resp.status}`);
    return resp.json();
  },
  async removeMember(orgId: string, memberId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/members/${memberId}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`Failed to remove member: ${resp.status}`);
  },
  async updateMemberRole(orgId: string, memberId: string, role: OrganizationRole, token?: string): Promise<OrganizationMember> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/members/${memberId}/role`, {
      method: 'PUT',
      headers,
      body: JSON.stringify({ role }),
    });
    if (!resp.ok) throw new Error(`Failed to update member role: ${resp.status}`);
    return resp.json();
  },
};
