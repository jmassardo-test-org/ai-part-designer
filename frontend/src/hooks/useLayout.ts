/**
 * Layout API Hooks
 * 
 * React Query hooks for spatial layout management.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import type { 
  LayoutResponse, 
  PlacementResponse,
  ValidationResult,
} from '@/components/layout/types';
import type { LayoutAlgorithm } from '@/components/layout/LayoutToolbar';

// Query keys
export const layoutKeys = {
  all: ['layouts'] as const,
  lists: () => [...layoutKeys.all, 'list'] as const,
  list: (projectId: string) => [...layoutKeys.lists(), projectId] as const,
  details: () => [...layoutKeys.all, 'detail'] as const,
  detail: (id: string) => [...layoutKeys.details(), id] as const,
};

// Types
interface CreateLayoutParams {
  projectId: string;
  name: string;
  internalWidth?: number;
  internalDepth?: number;
  internalHeight?: number;
  autoDimensions?: boolean;
  gridSize?: number;
  clearanceMargin?: number;
}

interface UpdateLayoutParams {
  layoutId: string;
  updates: {
    name?: string;
    internalWidth?: number;
    internalDepth?: number;
    internalHeight?: number;
    autoDimensions?: boolean;
    gridSize?: number;
    clearanceMargin?: number;
  };
}

interface AddPlacementParams {
  layoutId: string;
  componentId: string;
  xPosition: number;
  yPosition: number;
  zPosition?: number;
  rotationZ?: number;
  width: number;
  depth: number;
  height: number;
  faceDirection?: string;
  locked?: boolean;
}

interface UpdatePlacementParams {
  layoutId: string;
  placementId: string;
  updates: {
    xPosition?: number;
    yPosition?: number;
    zPosition?: number;
    rotationZ?: number;
    faceDirection?: string;
    locked?: boolean;
  };
}

interface RemovePlacementParams {
  layoutId: string;
  placementId: string;
}

interface AutoLayoutParams {
  layoutId: string;
  algorithm: LayoutAlgorithm;
}

// API functions
async function getLayout(layoutId: string): Promise<LayoutResponse> {
  const response = await api.get(`/layouts/${layoutId}`);
  return response.data;
}

async function getProjectLayouts(projectId: string): Promise<LayoutResponse[]> {
  const response = await api.get(`/projects/${projectId}/layouts`);
  return response.data;
}

async function createLayout(params: CreateLayoutParams): Promise<LayoutResponse> {
  const response = await api.post('/layouts', params);
  return response.data;
}

async function updateLayout(params: UpdateLayoutParams): Promise<LayoutResponse> {
  const response = await api.patch(`/layouts/${params.layoutId}`, params.updates);
  return response.data;
}

async function deleteLayout(layoutId: string): Promise<void> {
  await api.delete(`/layouts/${layoutId}`);
}

async function addPlacement(params: AddPlacementParams): Promise<PlacementResponse> {
  const { layoutId, ...data } = params;
  const response = await api.post(`/layouts/${layoutId}/placements`, data);
  return response.data;
}

async function updatePlacement(params: UpdatePlacementParams): Promise<PlacementResponse> {
  const { layoutId, placementId, updates } = params;
  const response = await api.patch(`/layouts/${layoutId}/placements/${placementId}`, updates);
  return response.data;
}

async function removePlacement(params: RemovePlacementParams): Promise<void> {
  const { layoutId, placementId } = params;
  await api.delete(`/layouts/${layoutId}/placements/${placementId}`);
}

async function validateLayout(layoutId: string): Promise<ValidationResult> {
  const response = await api.post(`/layouts/${layoutId}/validate`);
  return response.data;
}

async function autoLayout(params: AutoLayoutParams): Promise<LayoutResponse> {
  const response = await api.post(`/layouts/${params.layoutId}/auto-layout`, {
    algorithm: params.algorithm,
  });
  return response.data;
}

// Hooks

/**
 * Fetch a single layout by ID
 */
export function useLayout(layoutId: string | undefined) {
  return useQuery({
    queryKey: layoutKeys.detail(layoutId!),
    queryFn: () => getLayout(layoutId!),
    enabled: !!layoutId,
  });
}

/**
 * Fetch all layouts for a project
 */
export function useProjectLayouts(projectId: string | undefined) {
  return useQuery({
    queryKey: layoutKeys.list(projectId!),
    queryFn: () => getProjectLayouts(projectId!),
    enabled: !!projectId,
  });
}

/**
 * Create a new layout
 */
export function useCreateLayout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createLayout,
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: layoutKeys.list(variables.projectId) });
      queryClient.setQueryData(layoutKeys.detail(data.id), data);
    },
  });
}

/**
 * Update layout properties
 */
export function useUpdateLayout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updateLayout,
    onSuccess: (data) => {
      queryClient.setQueryData(layoutKeys.detail(data.id), data);
    },
  });
}

/**
 * Delete a layout
 */
export function useDeleteLayout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: deleteLayout,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: layoutKeys.lists() });
    },
  });
}

/**
 * Add a component placement to a layout
 */
export function useAddPlacement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: addPlacement,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: layoutKeys.detail(variables.layoutId) });
    },
  });
}

/**
 * Update a component placement
 */
export function useUpdatePlacement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: updatePlacement,
    onMutate: async (variables) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: layoutKeys.detail(variables.layoutId) });

      // Snapshot current data
      const previous = queryClient.getQueryData<LayoutResponse>(
        layoutKeys.detail(variables.layoutId)
      );

      // Optimistically update
      if (previous) {
        queryClient.setQueryData<LayoutResponse>(
          layoutKeys.detail(variables.layoutId),
          {
            ...previous,
            placements: previous.placements.map((p) =>
              p.id === variables.placementId
                ? { ...p, ...variables.updates }
                : p
            ),
          }
        );
      }

      return { previous };
    },
    onError: (_, variables, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(
          layoutKeys.detail(variables.layoutId),
          context.previous
        );
      }
    },
    onSettled: (_, __, variables) => {
      queryClient.invalidateQueries({ queryKey: layoutKeys.detail(variables.layoutId) });
    },
  });
}

/**
 * Remove a component placement from a layout
 */
export function useRemovePlacement() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: removePlacement,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: layoutKeys.detail(variables.layoutId) });

      const previous = queryClient.getQueryData<LayoutResponse>(
        layoutKeys.detail(variables.layoutId)
      );

      if (previous) {
        queryClient.setQueryData<LayoutResponse>(
          layoutKeys.detail(variables.layoutId),
          {
            ...previous,
            placements: previous.placements.filter((p) => p.id !== variables.placementId),
          }
        );
      }

      return { previous };
    },
    onError: (_, variables, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          layoutKeys.detail(variables.layoutId),
          context.previous
        );
      }
    },
    onSettled: (_, __, variables) => {
      queryClient.invalidateQueries({ queryKey: layoutKeys.detail(variables.layoutId) });
    },
  });
}

/**
 * Validate layout for collisions and boundary issues
 */
export function useValidateLayout() {
  return useMutation({
    mutationFn: validateLayout,
  });
}

/**
 * Auto-arrange components in layout
 */
export function useAutoLayout() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: autoLayout,
    onSuccess: (data) => {
      queryClient.setQueryData(layoutKeys.detail(data.id), data);
    },
  });
}
