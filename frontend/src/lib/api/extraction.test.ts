/**
 * Dimension Extraction API client tests.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { apiClient } from './client';
import { extractionApi } from './extraction';

// Mock the apiClient
vi.mock('./client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('extractionApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getStatus', () => {
    it('returns extraction service status', async () => {
      const mockStatus = {
        vision_available: true,
        pdf_available: true,
        supported_formats: ['png', 'jpg', 'jpeg', 'webp', 'pdf'],
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockStatus,
      });

      const result = await extractionApi.getStatus();

      expect(apiClient.get).toHaveBeenCalledWith('/extraction/status');
      expect(result).toEqual(mockStatus);
      expect(result.vision_available).toBe(true);
      expect(result.supported_formats).toContain('pdf');
    });

    it('returns unavailable status when services are down', async () => {
      const mockStatus = {
        vision_available: false,
        pdf_available: false,
        supported_formats: [],
      };

      (apiClient.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockStatus,
      });

      const result = await extractionApi.getStatus();

      expect(result.vision_available).toBe(false);
      expect(result.pdf_available).toBe(false);
    });
  });

  describe('extractFromFile', () => {
    it('extracts dimensions from an image file', async () => {
      const mockFile = new File(['image-content'], 'datasheet.png', {
        type: 'image/png',
      });

      const mockResponse = {
        overall_dimensions: {
          length: 100,
          width: 50,
          height: 25,
          unit: 'mm',
        },
        mounting_holes: [
          { x: 10, y: 10, diameter: 3, type: 'through' },
          { x: 90, y: 10, diameter: 3, type: 'through' },
        ],
        cutouts: null,
        connectors: [
          { name: 'USB-C', type: 'connector', position: { x: 50, y: 0 } },
        ],
        tolerances: { general: '±0.5mm' },
        notes: ['Dimensions in mm'],
        confidence: 0.95,
        pages_analyzed: 1,
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await extractionApi.extractFromFile(mockFile);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/extraction/dimensions',
        expect.any(FormData),
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('file')).toBe(mockFile);
      expect(result.overall_dimensions?.length).toBe(100);
      expect(result.mounting_holes).toHaveLength(2);
      expect(result.confidence).toBe(0.95);
    });

    it('extracts with context parameter', async () => {
      const mockFile = new File(['pdf-content'], 'component.pdf', {
        type: 'application/pdf',
      });

      const mockResponse = {
        overall_dimensions: { length: 85, width: 56, height: 17, unit: 'mm' },
        mounting_holes: [],
        cutouts: null,
        connectors: null,
        tolerances: null,
        notes: ['Raspberry Pi 4 Model B'],
        confidence: 0.92,
        pages_analyzed: 2,
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await extractionApi.extractFromFile(mockFile, {
        context: 'Raspberry Pi 4 Model B datasheet',
      });

      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('context')).toBe('Raspberry Pi 4 Model B datasheet');
      expect(result.notes).toContain('Raspberry Pi 4 Model B');
    });

    it('extracts with analyzeAllPages option', async () => {
      const mockFile = new File(['pdf-content'], 'multi-page.pdf', {
        type: 'application/pdf',
      });

      const mockResponse = {
        overall_dimensions: null,
        mounting_holes: null,
        cutouts: null,
        connectors: null,
        tolerances: null,
        notes: ['Multi-page analysis'],
        confidence: 0.8,
        pages_analyzed: 5,
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await extractionApi.extractFromFile(mockFile, {
        analyzeAllPages: true,
      });

      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('analyze_all_pages')).toBe('true');
      expect(result.pages_analyzed).toBe(5);
    });

    it('extracts with all options', async () => {
      const mockFile = new File(['content'], 'spec.pdf');

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { confidence: 0.9, pages_analyzed: 3 },
      });

      await extractionApi.extractFromFile(mockFile, {
        context: 'Arduino Uno specs',
        analyzeAllPages: true,
      });

      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('context')).toBe('Arduino Uno specs');
      expect(formData.get('analyze_all_pages')).toBe('true');
    });

    it('handles extraction errors', async () => {
      const mockFile = new File(['invalid'], 'bad-file.txt');

      (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Unsupported file format')
      );

      await expect(extractionApi.extractFromFile(mockFile)).rejects.toThrow(
        'Unsupported file format'
      );
    });
  });

  describe('extractFromUrl', () => {
    it('extracts dimensions from a URL', async () => {
      const testUrl = 'https://example.com/datasheet.pdf';

      const mockResponse = {
        overall_dimensions: {
          length: 150,
          width: 100,
          height: 30,
          unit: 'mm',
        },
        mounting_holes: [{ x: 5, y: 5, diameter: 4, type: 'M4' }],
        cutouts: [{ type: 'slot', x: 75, y: 50, width: 40, height: 10 }],
        connectors: null,
        tolerances: null,
        notes: null,
        confidence: 0.88,
        pages_analyzed: 1,
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await extractionApi.extractFromUrl(testUrl);

      expect(apiClient.post).toHaveBeenCalledWith(
        '/extraction/url',
        expect.any(FormData),
        { headers: { 'Content-Type': 'multipart/form-data' } }
      );

      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('url')).toBe(testUrl);
      expect(result.cutouts).toHaveLength(1);
      expect(result.cutouts?.[0].type).toBe('slot');
    });

    it('extracts from URL with context', async () => {
      const testUrl = 'https://manufacturer.com/product-spec.pdf';

      const mockResponse = {
        overall_dimensions: { length: 60, width: 40, height: 20, unit: 'mm' },
        mounting_holes: [],
        cutouts: null,
        connectors: null,
        tolerances: null,
        notes: ['ESP32 development board'],
        confidence: 0.91,
        pages_analyzed: 1,
      };

      (apiClient.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: mockResponse,
      });

      const result = await extractionApi.extractFromUrl(
        testUrl,
        'ESP32 DevKit C specifications'
      );

      const formData = (apiClient.post as ReturnType<typeof vi.fn>).mock.calls[0][1] as FormData;
      expect(formData.get('url')).toBe(testUrl);
      expect(formData.get('context')).toBe('ESP32 DevKit C specifications');
      expect(result.confidence).toBe(0.91);
    });

    it('handles URL extraction errors', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Failed to fetch URL')
      );

      await expect(
        extractionApi.extractFromUrl('https://invalid-url.com/404.pdf')
      ).rejects.toThrow('Failed to fetch URL');
    });

    it('handles network timeouts', async () => {
      (apiClient.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Request timeout')
      );

      await expect(
        extractionApi.extractFromUrl('https://slow-server.com/large.pdf')
      ).rejects.toThrow('Request timeout');
    });
  });
});
