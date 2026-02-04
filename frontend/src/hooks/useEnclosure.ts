/**
 * Enclosure API Hooks
 * 
 * React Query hooks for enclosure generation and management.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import type { EnclosureGenerationOptions } from '@/components/enclosure';
import api from '@/lib/api';
import { layoutKeys } from './useLayout';

// Types
interface GenerateEnclosureParams {
  layoutId: string;
  options: EnclosureGenerationOptions;
}

interface EnclosureResponse {
  id: string;
  projectId: string;
  layoutId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  modelUrl?: string;
  stlUrl?: string;
  stepUrl?: string;
  thumbnailUrl?: string;
  dimensions: {
    width: number;
    depth: number;
    height: number;
  };
  options: EnclosureGenerationOptions;
  createdAt: string;
  completedAt?: string;
  error?: string;
}

interface EnclosureJobStatus {
  jobId: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  currentStep?: string;
  result?: EnclosureResponse;
  error?: string;
}

// API functions
async function generateEnclosure(params: GenerateEnclosureParams): Promise<EnclosureJobStatus> {
  const response = await api.post('/enclosures/generate', {
    layout_id: params.layoutId,
    wall_thickness: params.options.wallThickness,
    bottom_thickness: params.options.bottomThickness,
    top_thickness: params.options.topThickness,
    style: params.options.style,
    corner_radius: params.options.cornerRadius,
    chamfer_size: params.options.chamferSize,
    lid_type: params.options.lidType,
    lid_clearance: params.options.lidClearance,
    screw_hole_diameter: params.options.screwHoleDiameter,
    screw_hole_count: params.options.screwHoleCount,
    ventilation_type: params.options.ventilationType,
    ventilation_size: params.options.ventilationSize,
    ventilation_spacing: params.options.ventilationSpacing,
    ventilation_faces: params.options.ventilationFaces,
    mounting_type: params.options.mountingType,
    standoff_height: params.options.standoffHeight,
    standoff_diameter: params.options.standoffDiameter,
    auto_cutouts: params.options.autoCutouts,
    cutout_clearance: params.options.cutoutClearance,
    cable_management: params.options.cableManagement,
    label_emboss: params.options.labelEmboss,
    label_text: params.options.labelText,
  });
  return response.data;
}

async function checkJobStatus(jobId: string): Promise<EnclosureJobStatus> {
  const response = await api.get(`/enclosures/jobs/${jobId}`);
  return response.data;
}

async function downloadEnclosure(enclosureId: string, format: 'stl' | 'step' | 'obj'): Promise<Blob> {
  const response = await api.get(`/enclosures/${enclosureId}/download`, {
    params: { format },
    responseType: 'blob',
  });
  return response.data;
}

// Hooks

/**
 * Generate an enclosure from a layout
 */
export function useGenerateEnclosure() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: generateEnclosure,
    onSuccess: (_, variables) => {
      // Invalidate layout to reflect new enclosure
      queryClient.invalidateQueries({ queryKey: layoutKeys.detail(variables.layoutId) });
    },
  });
}

/**
 * Poll for job status updates
 */
export function useCheckJobStatus() {
  return useMutation({
    mutationFn: checkJobStatus,
  });
}

/**
 * Download enclosure in specified format
 */
export function useDownloadEnclosure() {
  return useMutation({
    mutationFn: async ({ enclosureId, format }: { enclosureId: string; format: 'stl' | 'step' | 'obj' }) => {
      const blob = await downloadEnclosure(enclosureId, format);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `enclosure.${format}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      return blob;
    },
  });
}

/**
 * Hook to poll for enclosure generation progress
 */
export function useEnclosureProgress(
  jobId: string | null,
  onComplete: (result: EnclosureResponse) => void,
  onError: (error: string) => void,
) {
  const checkStatus = useCheckJobStatus();

  React.useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const status = await checkStatus.mutateAsync(jobId);
        
        if (status.status === 'completed' && status.result) {
          clearInterval(interval);
          onComplete(status.result);
        } else if (status.status === 'failed') {
          clearInterval(interval);
          onError(status.error || 'Generation failed');
        }
      } catch (error) {
        clearInterval(interval);
        onError((error as Error).message);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [jobId]);
}

// Need to import React for useEffect
import React from 'react';
