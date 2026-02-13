/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Marketplace API client.
 *
 * Handles browsing, saving, publishing, and managing marketplace designs.
 */

import type { BrowseFilters, CategoryResponse, DesignList, DesignSummary, ListCreate } from '@/types/marketplace';

const API_BASE = '/api/v1/marketplace';

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
): Promise<any> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch(`${API_BASE}/browse`, {
    method: 'POST',
    headers,
    body: JSON.stringify(filters),
  });
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
