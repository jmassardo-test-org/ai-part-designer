/**
 * Design management API client.
 * Handles design CRUD operations and project management.
 */

const DESIGN_API = '/api/v1/designs';
const PROJECT_API = '/api/v1/projects';

export interface Project {
  [key: string]: unknown;
  id: string;
  name: string;
  description?: string | null;
  thumbnail_url?: string | null;
  design_count?: number;
  created_at: string;
  updated_at?: string;
}

/** A design entity returned by the API. */
export interface Design {
  [key: string]: unknown;
  id: string;
  name: string;
  description: string;
  project_id: string;
  project_name: string;
  source_type: string;
  status: string;
  thumbnail_url: string | null;
  created_at: string;
  updated_at: string;
  extra_data?: {
    job_id?: string;
    downloads?: { stl?: string; step?: string };
    shape?: string;
    enclosure_schema?: unknown;
    [key: string]: unknown;
  };
}

/** Response from copying a design. */
export interface CopyResponse {
  [key: string]: unknown;
  design_id: string;
  name: string;
  id?: string;
  description?: string;
  project_id?: string;
  project_name?: string;
  source_type?: string;
  status?: string;
  thumbnail_url?: string | null;
  created_at?: string;
  updated_at?: string;
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
  paramsOrJobId: DesignSaveParams | string,
  authTokenOrName?: string,
  options?: Record<string, unknown>,
  authToken?: string
): Promise<{ design_id: string }> {
  const token = authToken || (typeof paramsOrJobId === 'string' ? '' : authTokenOrName) || '';
  const body = typeof paramsOrJobId === 'string'
    ? { job_id: paramsOrJobId, name: authTokenOrName, ...options }
    : {
        name: paramsOrJobId.name,
        description: paramsOrJobId.description,
        project_id: paramsOrJobId.projectId,
        job_id: paramsOrJobId.jobId,
      };
  const resp = await fetch(`${DESIGN_API}/from-job`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: 'Save failed' }));
    throw new Error(err.detail || `Failed to save design: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Get a single design by ID.
 */
export async function getDesign(designId: string, authToken: string): Promise<Design> {
  const resp = await fetch(`${DESIGN_API}/${designId}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    throw new Error(`Failed to fetch design: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Update a design's metadata.
 */
export async function updateDesign(
  designId: string,
  data: Record<string, unknown>,
  authToken: string
): Promise<Design> {
  const resp = await fetch(`${DESIGN_API}/${designId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(data),
  });

  if (!resp.ok) {
    throw new Error(`Failed to update design: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Copy a design to a project.
 */
export async function copyDesign(
  designId: string,
  nameOrTargetProjectId: string,
  optionsOrAuthToken?: string | Record<string, unknown>,
  authToken?: string
): Promise<Design> {
  const token = authToken || (typeof optionsOrAuthToken === 'string' ? optionsOrAuthToken : '');
  const resp = await fetch(`${DESIGN_API}/${designId}/copy`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(
      typeof optionsOrAuthToken === 'object'
        ? { name: nameOrTargetProjectId, ...optionsOrAuthToken }
        : { project_id: nameOrTargetProjectId }
    ),
  });

  if (!resp.ok) {
    throw new Error(`Failed to copy design: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Soft-delete a design with undo capability.
 */
export async function deleteDesignWithUndo(
  designId: string,
  authToken: string
): Promise<{ undo_token: string; undo_expires_at: string }> {
  const resp = await fetch(`${DESIGN_API}/${designId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    throw new Error(`Failed to delete design: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Undo a design deletion using the undo token.
 */
export async function undoDeleteDesign(
  undoToken: string,
  authToken: string
): Promise<Design> {
  const resp = await fetch(`${DESIGN_API}/undo-delete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ undo_token: undoToken }),
  });

  if (!resp.ok) {
    throw new Error(`Failed to undo delete: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Save a design from a conversation.
 */
export async function saveDesignFromConversation(
  conversationId: string,
  nameOrData: string | { name: string; description: string; project_id: string },
  dataOrAuthToken?: string | Record<string, unknown>,
  authToken?: string
): Promise<{ design_id: string }> {
  const token = authToken || (typeof dataOrAuthToken === 'string' ? dataOrAuthToken : '');
  const body = typeof nameOrData === 'string'
    ? { conversation_id: conversationId, name: nameOrData, ...(typeof dataOrAuthToken === 'object' ? dataOrAuthToken : {}) }
    : { conversation_id: conversationId, ...nameOrData };
  const resp = await fetch(`${DESIGN_API}/from-conversation`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok) {
    throw new Error(`Failed to save design from conversation: ${resp.status}`);
  }

  return resp.json();
}

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
