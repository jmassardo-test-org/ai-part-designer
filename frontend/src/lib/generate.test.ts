import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  generateFromDescription,
  parseDescription,
  downloadGeneratedFile,
  getPreviewData,
} from './generate';

// Mock global fetch with vi.fn
const mockFetch = vi.fn();

describe('generate module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('generateFromDescription', () => {
    it('generates CAD from description', async () => {
      const mockResponse = {
        job_id: 'job-123',
        status: 'completed',
        shape: 'box',
        confidence: 0.95,
        dimensions: { width: 100, height: 50, depth: 30 },
        warnings: [],
        timing: { parse_ms: 10, generate_ms: 100, export_ms: 50, total_ms: 160 },
        downloads: { step: '/download/job-123.step', stl: '/download/job-123.stl' },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await generateFromDescription({
        description: 'Create a 100x50x30mm box',
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/generate/'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: expect.stringContaining('Create a 100x50x30mm box'),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('includes auth token when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await generateFromDescription(
        { description: 'test' },
        'auth-token-123'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer auth-token-123',
          },
        })
      );
    });

    it('uses default export options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await generateFromDescription({ description: 'test' });

      const call = mockFetch.mock.calls[0];
      const body = JSON.parse(call[1].body);

      expect(body.export_step).toBe(true);
      expect(body.export_stl).toBe(true);
      expect(body.stl_quality).toBe('standard');
    });

    it('allows custom export options', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await generateFromDescription({
        description: 'test',
        export_step: false,
        export_stl: true,
        stl_quality: 'ultra',
      });

      const call = mockFetch.mock.calls[0];
      const body = JSON.parse(call[1].body);

      expect(body.export_step).toBe(false);
      expect(body.export_stl).toBe(true);
      expect(body.stl_quality).toBe('ultra');
    });

    it('throws error on failed response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Invalid description' }),
      });

      await expect(
        generateFromDescription({ description: 'bad input' })
      ).rejects.toThrow('Invalid description');
    });

    it('throws generic error when no detail provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({}),
      });

      await expect(
        generateFromDescription({ description: 'test' })
      ).rejects.toThrow('Generation failed');
    });

    it('handles JSON parse error in error response', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => {
          throw new Error('JSON parse error');
        },
      });

      await expect(
        generateFromDescription({ description: 'test' })
      ).rejects.toThrow('Generation failed');
    });
  });

  describe('parseDescription', () => {
    it('parses description without generating', async () => {
      const mockResponse = {
        shape: 'cylinder',
        dimensions: { radius: 25, height: 100 },
        features: [],
        units: 'mm',
        confidence: 0.9,
        assumptions: [],
        parse_time_ms: 5,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await parseDescription('Create a cylinder with 25mm radius');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/generate/parse'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ description: 'Create a cylinder with 25mm radius' }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('includes auth token when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await parseDescription('test', 'token-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: {
            'Content-Type': 'application/json',
            Authorization: 'Bearer token-123',
          },
        })
      );
    });

    it('throws error on failed parse', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: 'Cannot parse description' }),
      });

      await expect(parseDescription('gibberish')).rejects.toThrow('Cannot parse description');
    });
  });

  describe('downloadGeneratedFile', () => {
    it('downloads STEP file', async () => {
      const mockBlob = new Blob(['STEP content'], { type: 'application/step' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      const result = await downloadGeneratedFile('job-123', 'step');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/generate/job-123/download/step'),
        expect.objectContaining({ method: 'GET' })
      );
      expect(result).toEqual(mockBlob);
    });

    it('downloads STL file', async () => {
      const mockBlob = new Blob(['STL content'], { type: 'application/stl' });
      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      const result = await downloadGeneratedFile('job-456', 'stl');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/generate/job-456/download/stl'),
        { method: 'GET', headers: {} }
      );
      expect(result).toEqual(mockBlob);
    });

    it('includes auth token when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => new Blob(),
      });

      await downloadGeneratedFile('job-123', 'step', 'token-abc');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: { Authorization: 'Bearer token-abc' },
        })
      );
    });

    it('throws error on failed download', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
      });

      await expect(
        downloadGeneratedFile('job-123', 'stl')
      ).rejects.toThrow('Failed to download STL file');
    });
  });

  describe('getPreviewData', () => {
    it('returns ArrayBuffer for 3D preview', async () => {
      const mockArrayBuffer = new ArrayBuffer(100);
      const mockBlob = new Blob(['STL data']);
      mockBlob.arrayBuffer = vi.fn().mockResolvedValue(mockArrayBuffer);

      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      const result = await getPreviewData('job-123');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/generate/job-123/download/stl'),
        expect.any(Object)
      );
      expect(result).toEqual(mockArrayBuffer);
    });

    it('passes token to downloadGeneratedFile', async () => {
      const mockBlob = new Blob();
      mockBlob.arrayBuffer = vi.fn().mockResolvedValue(new ArrayBuffer(0));

      mockFetch.mockResolvedValueOnce({
        ok: true,
        blob: async () => mockBlob,
      });

      await getPreviewData('job-123', 'token-xyz');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: { Authorization: 'Bearer token-xyz' },
        })
      );
    });
  });
});
