/**
 * Design management API client.
 * Handles design CRUD operations and project management.
 */

const DESIGN_API = '/api/v1/designs';
const PROJECT_API = '/api/v1/projects';

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface DesignSaveParams {
  name: string;
  description: string;
  projectId: string;
  jobId: string;
}

/**
 * Save a generated design from a job result.
 */
export async function saveDesignFromJob(
  params: DesignSaveParams,
  authToken: string
): Promise<{ design_id: string }> {
  const resp = await fetch(`${DESIGN_API}/from-job`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({
      name: params.name,
      description: params.description,
      project_id: params.projectId,
      job_id: params.jobId,
    }),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Save failed' }));
    throw new Error(err.detail || `Failed to save design: ${resp.status}`);
  }

  return resp.json();
}

/**
 * List all projects for the authenticated user.
 */
export async function listProjects(authToken: string): Promise<Project[]> {
  const resp = await fetch(PROJECT_API, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    throw new Error(`Failed to fetch projects: ${resp.status}`);
  }

  return resp.json();
}
