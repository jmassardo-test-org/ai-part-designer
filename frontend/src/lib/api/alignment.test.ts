/**
 * Alignment API client tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { alignmentApi, ALIGNMENT_PRESETS } from './alignment';
// Mock the apiClient
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));
import { apiClient } from './client';

describe('alignmentApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('align', () => {
    it('aligns files with CENTER mode', async () => {
      const mockResponse = {
        success: true,
        output_path: '/uploads/aligned-result.step',
        mode: 'CENTER',
        file_count: 2,
        combined_bounds: {
          min_x: 0,
          min_y: 0,
          min_z: 0,
          max_x: 100,
          max_y: 100,
          max_z: 50,
          center_x: 50,
          center_y: 50,
          center_z: 25,
        },
        transformations: [],
        message: 'Alignment complete',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await alignmentApi.align({
        file_paths: ['/path/to/file1.step', '/path/to/file2.step'],
        mode: 'CENTER',
      });

      expect(apiClient.post).toHaveBeenCalledWith('/cad/align', {
        file_paths: ['/path/to/file1.step', '/path/to/file2.step'],
        mode: 'CENTER',
      });
      expect(result).toEqual(mockResponse);
    });

    it('aligns files with STACK_Z mode and gap', async () => {
      const mockResponse = {
        success: true,
        output_path: '/uploads/stacked.step',
        mode: 'STACK_Z',
        file_count: 3,
        combined_bounds: {
          min_x: 0,
          min_y: 0,
          min_z: 0,
          max_x: 50,
          max_y: 50,
          max_z: 150,
          center_x: 25,
          center_y: 25,
          center_z: 75,
        },
        transformations: [],
        message: 'Files stacked vertically',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await alignmentApi.align({
        file_paths: ['/a.step', '/b.step', '/c.step'],
        mode: 'STACK_Z',
        gap: 5,
      });

      expect(apiClient.post).toHaveBeenCalledWith('/cad/align', {
        file_paths: ['/a.step', '/b.step', '/c.step'],
        mode: 'STACK_Z',
        gap: 5,
      });
      expect(result.mode).toBe('STACK_Z');
      expect(result.file_count).toBe(3);
    });

    it('aligns files with reference index', async () => {
      const mockResponse = {
        success: true,
        output_path: '/uploads/aligned.step',
        mode: 'FACE',
        file_count: 2,
        combined_bounds: {
          min_x: 0, min_y: 0, min_z: 0,
          max_x: 100, max_y: 100, max_z: 50,
          center_x: 50, center_y: 50, center_z: 25,
        },
        transformations: [],
        message: 'Faces aligned',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      await alignmentApi.align({
        file_paths: ['/a.step', '/b.step'],
        mode: 'FACE',
        reference_index: 1,
      });

      expect(apiClient.post).toHaveBeenCalledWith('/cad/align', {
        file_paths: ['/a.step', '/b.step'],
        mode: 'FACE',
        reference_index: 1,
      });
    });

    it('handles alignment errors', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Alignment failed')
      );

      await expect(
        alignmentApi.align({
          file_paths: ['/invalid.step'],
          mode: 'CENTER',
        })
      ).rejects.toThrow('Alignment failed');
    });
  });

  describe('uploadAndAlign', () => {
    it('uploads files and aligns with specified mode', async () => {
      const mockFiles = [
        new File(['content1'], 'part1.step', { type: 'application/step' }),
        new File(['content2'], 'part2.step', { type: 'application/step' }),
      ];

      const mockResponse = {
        success: true,
        output_path: '/uploads/aligned-upload.step',
        mode: 'STACK_X',
        file_count: 2,
        combined_bounds: {
          min_x: 0, min_y: 0, min_z: 0,
          max_x: 200, max_y: 50, max_z: 50,
          center_x: 100, center_y: 25, center_z: 25,
        },
        transformations: [],
        message: 'Upload and alignment complete',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await alignmentApi.uploadAndAlign(mockFiles, 'STACK_X', 10);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/cad/align/upload',
        expect.any(FormData),
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      // Verify FormData contents
      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('mode')).toBe('STACK_X');
      expect(formData.get('gap')).toBe('10');
      expect(result).toEqual(mockResponse);
    });

    it('uploads with default gap of 0', async () => {
      const mockFiles = [new File(['content'], 'part.step')];
      
      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { success: true, output_path: '/output.step', mode: 'CENTER', file_count: 1 },
      });

      await alignmentApi.uploadAndAlign(mockFiles, 'CENTER');

      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('gap')).toBe('0');
    });
  });

  describe('preview', () => {
    it('gets alignment preview without creating output file', async () => {
      const mockPreview = {
        success: true,
        mode: 'EDGE',
        file_count: 2,
        combined_bounds: {
          min_x: 0, min_y: 0, min_z: 0,
          max_x: 100, max_y: 100, max_z: 50,
          center_x: 50, center_y: 50, center_z: 25,
        },
        transformations: [
          {
            file_path: '/a.step',
            original_bounds: {
              min_x: 0, min_y: 0, min_z: 0,
              max_x: 50, max_y: 50, max_z: 25,
              center_x: 25, center_y: 25, center_z: 12.5,
            },
            applied_translation: { x: 0, y: 0, z: 0 },
            final_bounds: {
              min_x: 0, min_y: 0, min_z: 0,
              max_x: 50, max_y: 50, max_z: 25,
              center_x: 25, center_y: 25, center_z: 12.5,
            },
          },
        ],
        message: 'Preview generated',
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockPreview,
      });

      const result = await alignmentApi.preview({
        file_paths: ['/a.step', '/b.step'],
        mode: 'EDGE',
      });

      expect(apiClient.post).toHaveBeenCalledWith('/cad/align/preview', {
        file_paths: ['/a.step', '/b.step'],
        mode: 'EDGE',
      });
      expect(result.transformations).toHaveLength(1);
    });
  });
});

describe('ALIGNMENT_PRESETS', () => {
  it('contains all alignment modes', () => {
    const modes = ALIGNMENT_PRESETS.map((p) => p.mode);
    expect(modes).toContain('CENTER');
    expect(modes).toContain('ORIGIN');
    expect(modes).toContain('STACK_Z');
    expect(modes).toContain('STACK_X');
    expect(modes).toContain('STACK_Y');
    expect(modes).toContain('FACE');
    expect(modes).toContain('EDGE');
  });

  it('has required properties for each preset', () => {
    ALIGNMENT_PRESETS.forEach((preset) => {
      expect(preset).toHaveProperty('mode');
      expect(preset).toHaveProperty('label');
      expect(preset).toHaveProperty('description');
      expect(preset).toHaveProperty('icon');
      expect(typeof preset.label).toBe('string');
      expect(typeof preset.description).toBe('string');
    });
  });

  it('has unique modes', () => {
    const modes = ALIGNMENT_PRESETS.map((p) => p.mode);
    const uniqueModes = new Set(modes);
    expect(uniqueModes.size).toBe(modes.length);
  });
});
