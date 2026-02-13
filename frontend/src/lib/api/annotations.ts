/* eslint-disable @typescript-eslint/no-explicit-any */
/**
 * Annotations API client.
 *
 * Handles 3D annotation management for design reviews.
 */

/** 3D position coordinates. */
export interface Position3D {
  [key: string]: any;
  x: number;
  y: number;
  z: number;
}

/** Annotation type. */
export type AnnotationType = 'comment' | 'dimension' | 'issue' | 'suggestion' | 'note' | 'question' | string;

/** Annotation status. */
export type AnnotationStatus = 'open' | 'resolved' | 'wontfix';

/** Annotation entity. */
export interface Annotation {
  [key: string]: any;
  id: string;
  design_id: string;
  type: AnnotationType;
  status: AnnotationStatus;
  position: Position3D;
  content: string;
  author_id: string;
  author_name: string;
  priority: 'low' | 'medium' | 'high' | 'critical' | number;
  created_at: string;
  updated_at: string;
  resolved_at?: string;
}

/** Data required to create an annotation. */
export interface CreateAnnotationData {
  [key: string]: any;
  design_id: string;
  type: AnnotationType;
  position: Position3D;
  content: string;
  priority?: 'low' | 'medium' | 'high' | 'critical';
}

/** Priority color mapping. */
export const PRIORITY_COLORS: Record<string, string> = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  critical: '#ef4444',
};

/** Annotations API methods. */
export const annotationsApi: any = {
  async list(designId: string, token?: string): Promise<Annotation[]> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/designs/${designId}/annotations`, { headers });
    if (!resp.ok) throw new Error(`Failed to list annotations: ${resp.status}`);
    return resp.json();
  },
  async create(data: CreateAnnotationData, token?: string): Promise<Annotation> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/designs/${data.design_id}/annotations`, {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Failed to create annotation: ${resp.status}`);
    return resp.json();
  },
  async update(designId: string, annotationId: string, data: Partial<Annotation>, token?: string): Promise<Annotation> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/designs/${designId}/annotations/${annotationId}`, {
      method: 'PUT',
      headers,
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`Failed to update annotation: ${resp.status}`);
    return resp.json();
  },
  async delete(designId: string, annotationId: string, token?: string): Promise<void> {
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(`/api/v1/designs/${designId}/annotations/${annotationId}`, {
      method: 'DELETE',
      headers,
    });
    if (!resp.ok) throw new Error(`Failed to delete annotation: ${resp.status}`);
  },
};

/** Labels for annotation types. */
export const ANNOTATION_TYPE_LABELS: Record<string, string> = {
  comment: 'Comment',
  dimension: 'Dimension',
  issue: 'Issue',
  suggestion: 'Suggestion',
  note: 'Note',
};

/** Colors for annotation types. */
export const ANNOTATION_TYPE_COLORS: Record<string, string> = {
  comment: '#3b82f6',
  dimension: '#8b5cf6',
  issue: '#ef4444',
  suggestion: '#22c55e',
  note: '#eab308',
};

/** Labels for annotation priorities. */
export const PRIORITY_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};
