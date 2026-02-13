/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Teams API client.
 *
 * Handles team management within organizations.
 */

/** Team role type. */
export type TeamRole = 'lead' | 'member' | 'viewer' | 'admin';

/** Team summary. */
export interface Team {
  [key: string]: any;
  id: string;
  name: string;
  description?: string;
  member_count: number;
  created_at: string;
}

/** Team with full member details. */
export interface TeamDetail extends Team {
  [key: string]: any;
  members: TeamMember[];
}

/** Team member. */
export interface TeamMember {
  [key: string]: any;
  id: string;
  user_id: string;
  email: string;
  name: string;
  role: TeamRole;
  joined_at: string;
}

/** Teams API methods. */
export const teamsApi: any = {
  async list(orgId: string, token?: string): Promise<Team[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/teams`, { headers });
    if (!resp.ok) throw new Error(`Failed to list teams: ${resp.status}`);
    return resp.json();
  },
  async get(orgId: string, teamId: string, token?: string): Promise<TeamDetail> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/teams/${teamId}`, { headers });
    if (!resp.ok) throw new Error(`Failed to get team: ${resp.status}`);
    return resp.json();
  },
  async create(orgId: string, data: { name: string; description?: string }, token?: string): Promise<Team> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/teams`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Failed to create team: ${resp.status}`);
    return resp.json();
  },
  async addMember(orgId: string, teamId: string, userId: string, role: TeamRole, token?: string): Promise<TeamMember> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/teams/${teamId}/members`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ user_id: userId, role }),
    });
    if (!resp.ok) throw new Error(`Failed to add team member: ${resp.status}`);
    return resp.json();
  },
  async removeMember(orgId: string, teamId: string, memberId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/teams/${teamId}/members/${memberId}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`Failed to remove team member: ${resp.status}`);
  },
  async deleteTeam(orgId: string, teamId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/organizations/${orgId}/teams/${teamId}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`Failed to delete team: ${resp.status}`);
  },
};
