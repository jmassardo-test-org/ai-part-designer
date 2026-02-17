/**
 * Alignment API client tests.
 *
 * Tests for the alignment API module that handles part alignment operations.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { alignmentApi, ALIGNMENT_PRESETS, AlignmentMode } from './alignment';

// Store original fetch
const originalFetch = global.fetch;

// Mock fetch helper that returns proper Response-like object
function createMockResponse(data: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    json: () => Promise.resolve(data),
    clone: function() { return this; },
    headers: new Headers(),
    redirected: false,
    statusText: ok ? 'OK' : 'Error',
    type: 'basic',
    url: '',
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    text: () => Promise.resolve(JSON.stringify(data)),
  } as Response;
}

describe('alignmentApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe('align', () => {
    it('aligns parts with CENTER mode', async () => {
      const mockResponse = {
        success: true,
        output_path: '/uploads/aligned-result.step',
        mode: 'CENTER',
        file_count: 2,
        transformations: [],
        message: 'Alignment complete',
      };

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await alignmentApi.align(
        ['part1', 'part2'],
        'CENTER' as AlignmentMode
      );

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/alignment/align', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ part_ids: ['part1', 'part2'], mode: 'CENTER' }),
      });
      expect(result).toEqual(mockResponse);
    });

    it('aligns parts with stack mode and options', async () => {
      const mockResponse = {
        success: true,
        output_path: '/uploads/stacked.step',
        mode: 'stack',
        file_count: 3,
        transformations: [],
        message: 'Files stacked',
      };

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await alignmentApi.align(
        ['part1', 'part2', 'part3'],
        'stack' as AlignmentMode,
        { gap: 5, reference: 'first' }
      );

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/alignment/align', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          part_ids: ['part1', 'part2', 'part3'],
          mode: 'stack',
          gap: 5,
          reference: 'first',
        }),
      });
      expect(result.mode).toBe('stack');
    });

    it('includes authorization header when token provided', async () => {
      const mockResponse = { success: true, transformations: [] };

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockResponse));

      await alignmentApi.align(['part1'], 'center' as AlignmentMode, {}, 'test-token');

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/alignment/align', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-token',
        },
        body: expect.any(String),
      });
    });

    it('throws error on failed alignment', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({}, false, 500));

      await expect(
        alignmentApi.align(['part1'], 'CENTER' as AlignmentMode)
      ).rejects.toThrow('Alignment failed: 500');
    });
  });

  describe('alignParts', () => {
    it('aligns parts using alignParts method', async () => {
      const mockResponse = {
        success: true,
        transformations: [],
      };

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse(mockResponse));

      const result = await alignmentApi.alignParts(
        ['part1', 'part2'],
        'align-x' as AlignmentMode,
        { gap: 10 }
      );

      expect(global.fetch).toHaveBeenCalledWith('/api/v1/alignment/align', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          part_ids: ['part1', 'part2'],
          mode: 'align-x',
          gap: 10,
        }),
      });
      expect(result.success).toBe(true);
    });
  });
});

describe('ALIGNMENT_PRESETS', () => {
  it('contains expected alignment preset keys', () => {
    expect(ALIGNMENT_PRESETS).toHaveProperty('center');
    expect(ALIGNMENT_PRESETS).toHaveProperty('stack-z');
    expect(ALIGNMENT_PRESETS).toHaveProperty('align-x');
    expect(ALIGNMENT_PRESETS).toHaveProperty('align-y');
  });

  it('has required properties for each preset', () => {
    Object.values(ALIGNMENT_PRESETS).forEach((preset) => {
      expect(preset).toHaveProperty('mode');
      expect(preset).toHaveProperty('label');
      expect(preset).toHaveProperty('description');
      expect(typeof preset.label).toBe('string');
      expect(typeof preset.description).toBe('string');
    });
  });

  it('has unique modes across presets', () => {
    const modes = Object.values(ALIGNMENT_PRESETS).map((p) => p.mode);
    const uniqueModes = new Set(modes);
    expect(uniqueModes.size).toBe(modes.length);
  });

  it('center preset has correct configuration', () => {
    const centerPreset = ALIGNMENT_PRESETS['center'];
    expect(centerPreset.mode).toBe('center');
    expect(centerPreset.label).toBe('Center');
  });

  it('stack-z preset has correct configuration', () => {
    const stackPreset = ALIGNMENT_PRESETS['stack-z'];
    expect(stackPreset.mode).toBe('stack');
    expect(stackPreset.label).toBe('Stack (Z)');
  });
});
