/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Marketplace API client.
 *
 * Handles browsing, saving, publishing, and managing marketplace designs.
 */

import type {
  BrowseFilters,
  CategoryResponse,
  DesignComment,
  DesignList,
  DesignRating,
  DesignSummary,
  ListCreate,
  MarketplaceDesign,
  PaginatedComments,
  PaginatedDesigns,
  PaginatedRatings,
  RatingSummary,
  RemixResponse,
  ReportResponse,
  ReportStatus,
} from '@/types/marketplace';

const API_BASE = '/api/v2/marketplace';

/**
 * Get available categories.
 */
export async function getCategories(token?: string): Promise<CategoryResponse[]> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/categories`, { headers });
  if (!resp.ok) throw new Error(`Failed to get categories: ${resp.status}`);
  return resp.json();
}

/**
 * Get featured designs.
 */
export async function getFeaturedDesigns(limit?: number, token?: string): Promise<DesignSummary[]> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const query = limit ? `?limit=${limit}` : '';
  const resp = await fetch(`${API_BASE}/featured${query}`, { headers });
  if (!resp.ok) throw new Error(`Failed to get featured designs: ${resp.status}`);
  return resp.json();
}

/**
 * Browse marketplace designs with filters.
 */
export async function browseDesigns(
  filters: BrowseFilters,
  token?: string
): Promise<PaginatedDesigns> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.tags?.length) filters.tags.forEach(t => params.append('tags', t));
  if (filters.search) params.set('search', filters.search);
  if (filters.sort) params.set('sort', filters.sort);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  const query = params.toString() ? `?${params.toString()}` : '';
  const resp = await fetch(`${API_BASE}/designs${query}`, { headers });
  if (!resp.ok) throw new Error(`Failed to browse designs: ${resp.status}`);
  return resp.json();
}

/**
 * Save a design to user's collection.
 */
export async function saveDesign(designId: string, listIds?: string[], token?: string | null): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/save`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ list_ids: listIds }),
  });
  if (!resp.ok) throw new Error(`Failed to save design: ${resp.status}`);
}

/**
 * Unsave a design from user's collection.
 */
export async function unsaveDesign(designId: string, token?: string | null): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/save`, {
    method: 'DELETE',
    headers,
  });
  if (!resp.ok) throw new Error(`Failed to unsave design: ${resp.status}`);
}

/**
 * Check if a design is saved by the current user.
 */
export async function checkSaveStatus(designId: string, token: string): Promise<any> {
  const resp = await fetch(`${API_BASE}/designs/${designId}/save-status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Failed to check save status: ${resp.status}`);
  return resp.json();
}

/**
 * Publish a design to the marketplace.
 */
export async function publishDesign(designId: string, data?: unknown, token?: string): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/publish`, {
    method: 'POST',
    headers,
    body: data ? JSON.stringify(data) : undefined,
  });
  if (!resp.ok) throw new Error(`Failed to publish design: ${resp.status}`);
}

/**
 * Unpublish a design from the marketplace.
 */
export async function unpublishDesign(designId: string, token?: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/unpublish`, {
    method: 'POST',
    headers,
  });
  if (!resp.ok) throw new Error(`Failed to unpublish design: ${resp.status}`);
}

/**
 * Get user's saved lists.
 */
export async function getMyLists(token: string): Promise<DesignList[]> {
  const resp = await fetch(`${API_BASE}/lists`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Failed to get lists: ${resp.status}`);
  return resp.json();
}

/**
 * Create a new saved list.
 */
export async function createList(data: ListCreate, token?: string | null): Promise<DesignList> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/lists`, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  });
  if (!resp.ok) throw new Error(`Failed to create list: ${resp.status}`);
  return resp.json();
}

/**
 * Delete a saved list.
 */
export async function deleteList(listId: string, token?: string | null): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/lists/${listId}`, {
    method: 'DELETE',
    headers,
  });
  if (!resp.ok) throw new Error(`Failed to delete list: ${resp.status}`);
}

/**
 * Get starter template categories.
 */
export async function getStarterCategories(): Promise<CategoryResponse[]> {
  const resp = await fetch(`${API_BASE}/starters/categories`);
  if (!resp.ok) throw new Error(`Failed to get starter categories: ${resp.status}`);
  return resp.json();
}

/**
 * Get starter templates.
 */
export async function getStarters(params?: Record<string, unknown>): Promise<any> {
  const query = params ? '?' + new URLSearchParams(
    Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)])
  ).toString() : '';
  const resp = await fetch(`${API_BASE}/starters${query}`);
  if (!resp.ok) throw new Error(`Failed to get starters: ${resp.status}`);
  return resp.json();
}

/**
 * Get starter template detail.
 */
export async function getStarterDetail(starterId: string): Promise<any> {
  const resp = await fetch(`${API_BASE}/starters/${starterId}`);
  if (!resp.ok) throw new Error(`Failed to get starter detail: ${resp.status}`);
  return resp.json();
}

/**
 * Remix a starter template.
 */
export async function remixStarter(
  starterId: string,
  customizations?: unknown,
  token?: string
): Promise<any> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/starters/${starterId}/remix`, {
    method: 'POST',
    headers,
    body: customizations ? JSON.stringify(customizations) : undefined,
  });
  if (!resp.ok) throw new Error(`Failed to remix starter: ${resp.status}`);
  return resp.json();
}

// =============================================================================
// Design Detail
// =============================================================================

/**
 * Get full details of a marketplace design.
 */
export async function getDesignDetail(designId: string, token?: string): Promise<MarketplaceDesign> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}`, { headers });
  if (!resp.ok) throw new Error(`Failed to get design detail: ${resp.status}`);
  return resp.json();
}

// =============================================================================
// Ratings API
// =============================================================================

/**
 * Create or update a rating for a design.
 */
export async function rateDesign(
  designId: string,
  rating: number,
  review?: string,
  token?: string
): Promise<DesignRating> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/ratings`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ rating, review: review || null }),
  });
  if (!resp.ok) throw new Error(`Failed to rate design: ${resp.status}`);
  return resp.json();
}

/**
 * Delete the current user's rating for a design.
 */
export async function deleteRating(designId: string, token?: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/ratings`, {
    method: 'DELETE',
    headers,
  });
  if (!resp.ok) throw new Error(`Failed to delete rating: ${resp.status}`);
}

/**
 * Get rating summary for a design.
 */
export async function getRatingSummary(designId: string): Promise<RatingSummary> {
  const resp = await fetch(`${API_BASE}/designs/${designId}/ratings/summary`);
  if (!resp.ok) throw new Error(`Failed to get rating summary: ${resp.status}`);
  return resp.json();
}

/**
 * Get paginated ratings for a design.
 */
export async function getDesignRatings(
  designId: string,
  page = 1,
  pageSize = 20
): Promise<PaginatedRatings> {
  const resp = await fetch(
    `${API_BASE}/designs/${designId}/ratings?page=${page}&page_size=${pageSize}`
  );
  if (!resp.ok) throw new Error(`Failed to get ratings: ${resp.status}`);
  return resp.json();
}

/**
 * Get current user's rating for a design.
 */
export async function getMyRating(designId: string, token: string): Promise<DesignRating | null> {
  const resp = await fetch(`${API_BASE}/designs/${designId}/ratings/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) {
    if (resp.status === 404) return null;
    throw new Error(`Failed to get my rating: ${resp.status}`);
  }
  return resp.json();
}

// =============================================================================
// Comments API
// =============================================================================

/**
 * Get threaded comments for a design.
 */
export async function getDesignComments(
  designId: string,
  page = 1,
  pageSize = 50
): Promise<PaginatedComments> {
  const resp = await fetch(
    `${API_BASE}/designs/${designId}/comments?page=${page}&page_size=${pageSize}`
  );
  if (!resp.ok) throw new Error(`Failed to get comments: ${resp.status}`);
  return resp.json();
}

/**
 * Create a comment on a design.
 */
export async function createComment(
  designId: string,
  content: string,
  parentId?: string,
  token?: string
): Promise<DesignComment> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/comments`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ content, parent_id: parentId || null }),
  });
  if (!resp.ok) throw new Error(`Failed to create comment: ${resp.status}`);
  return resp.json();
}

/**
 * Update a comment.
 */
export async function updateComment(
  commentId: string,
  content: string,
  token?: string
): Promise<DesignComment> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/comments/${commentId}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify({ content }),
  });
  if (!resp.ok) throw new Error(`Failed to update comment: ${resp.status}`);
  return resp.json();
}

/**
 * Delete a comment.
 */
export async function deleteComment(commentId: string, token?: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/comments/${commentId}`, {
    method: 'DELETE',
    headers,
  });
  if (!resp.ok) throw new Error(`Failed to delete comment: ${resp.status}`);
}

// =============================================================================
// Remix API
// =============================================================================

/**
 * Remix a marketplace design.
 */
export async function remixDesign(
  designId: string,
  name?: string,
  token?: string
): Promise<RemixResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/remix`, {
    method: 'POST',
    headers,
    body: name ? JSON.stringify({ name }) : undefined,
  });
  if (!resp.ok) throw new Error(`Failed to remix design: ${resp.status}`);
  return resp.json();
}

// =============================================================================
// Report API
// =============================================================================

/**
 * Report a design for content moderation.
 */
export async function reportDesign(
  designId: string,
  reason: string,
  description?: string,
  token?: string
): Promise<ReportResponse> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/designs/${designId}/report`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ reason, description: description || null }),
  });
  if (!resp.ok) throw new Error(`Failed to report design: ${resp.status}`);
  return resp.json();
}

/**
 * Check if the current user has already reported a design.
 */
export async function checkReportStatus(designId: string, token: string): Promise<ReportStatus> {
  const resp = await fetch(`${API_BASE}/designs/${designId}/report/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!resp.ok) throw new Error(`Failed to check report status: ${resp.status}`);
  return resp.json();
}

// =============================================================================
// View Tracking
// =============================================================================

/**
 * Track a view for a marketplace design (fire-and-forget).
 */
export async function trackDesignView(designId: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/designs/${designId}/view`, { method: 'POST' });
  } catch {
    // Silently ignore view tracking errors
  }
}
