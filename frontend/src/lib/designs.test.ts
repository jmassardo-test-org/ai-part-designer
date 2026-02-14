/**
 * Tests for the designs API service.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { saveDesignFromJob, saveDesignFromConversation, listDesigns, getDesign } from './designs';

// Mock fetch globally
const mockFetch = vi.fn();

describe('designs module', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe('saveDesignFromJob', () => {
    it('sends correct request to save design from job', async () => {
      const mockDesign = {
        id: 'design-123',
        name: 'My Design',
        description: 'A test design',
        project_id: 'project-123',
        project_name: 'My Project',
        source_type: 'ai_generated',
        status: 'ready',
        thumbnail_url: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDesign),
      });

      const result = await saveDesignFromJob(
        'job-123',
        'My Design',
        { description: 'A test design', projectId: 'project-123' },
        'test-token'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/designs/from-job'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            job_id: 'job-123',
            name: 'My Design',
            description: 'A test design',
            project_id: 'project-123',
          }),
        })
      );

      expect(result).toEqual(mockDesign);
    });

    it('throws error on failed request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Job not found' }),
      });

      await expect(
        saveDesignFromJob('bad-job', 'My Design', {}, 'test-token')
      ).rejects.toThrow('Job not found');
    });
  });

  describe('saveDesignFromConversation', () => {
    it('sends correct request to save design from conversation', async () => {
      const mockDesign = {
        id: 'design-456',
        name: 'Chat Design',
        description: 'Generated via chat',
        project_id: 'project-123',
        project_name: 'My Project',
        source_type: 'ai_generated',
        status: 'ready',
        thumbnail_url: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDesign),
      });

      const result = await saveDesignFromConversation(
        'conversation-123',
        'Chat Design',
        { description: 'Generated via chat', projectId: 'project-123' },
        'test-token'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/designs/from-conversation'),
        expect.objectContaining({
          method: 'POST',
          headers: {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            conversation_id: 'conversation-123',
            name: 'Chat Design',
            description: 'Generated via chat',
            project_id: 'project-123',
          }),
        })
      );

      expect(result).toEqual(mockDesign);
    });

    it('throws error when conversation not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Conversation not found' }),
      });

      await expect(
        saveDesignFromConversation('bad-id', 'My Design', {}, 'test-token')
      ).rejects.toThrow('Conversation not found');
    });

    it('throws error when conversation has no result', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Conversation has no result data' }),
      });

      await expect(
        saveDesignFromConversation('incomplete-id', 'My Design', {}, 'test-token')
      ).rejects.toThrow('Conversation has no result data');
    });

    it('handles missing optional parameters', async () => {
      const mockDesign = {
        id: 'design-789',
        name: 'Minimal Design',
        description: null,
        project_id: 'default-project',
        project_name: 'My Designs',
        source_type: 'ai_generated',
        status: 'ready',
        thumbnail_url: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDesign),
      });

      await saveDesignFromConversation(
        'conversation-123',
        'Minimal Design',
        {}, // No optional params
        'test-token'
      );

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: JSON.stringify({
            conversation_id: 'conversation-123',
            name: 'Minimal Design',
            description: null,
            project_id: null,
          }),
        })
      );
    });
  });

  describe('listDesigns', () => {
    it('fetches designs with default params', async () => {
      const mockResponse = {
        designs: [],
        total: 0,
        page: 1,
        per_page: 20,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      const result = await listDesigns('test-token');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/designs'),
        expect.objectContaining({
          headers: { 'Authorization': 'Bearer test-token' },
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('includes query parameters', async () => {
      const mockResponse = {
        designs: [],
        total: 0,
        page: 2,
        per_page: 10,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      });

      await listDesigns('test-token', { page: 2, perPage: 10, search: 'box' });

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('page=2');
      expect(calledUrl).toContain('per_page=10');
      expect(calledUrl).toContain('search=box');
    });
  });

  describe('getDesign', () => {
    it('fetches a specific design by ID', async () => {
      const mockDesign = {
        id: 'design-123',
        name: 'My Design',
        description: 'A test design',
        project_id: 'project-123',
        project_name: 'My Project',
        source_type: 'ai_generated',
        status: 'ready',
        thumbnail_url: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDesign),
      });

      const result = await getDesign('design-123', 'test-token');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/designs/design-123'),
        expect.objectContaining({
          headers: { 'Authorization': 'Bearer test-token' },
        })
      );

      expect(result).toEqual(mockDesign);
    });

    it('throws error when design not found', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: 'Design not found' }),
      });

      await expect(
        getDesign('bad-id', 'test-token')
      ).rejects.toThrow('Design not found');
    });
  });
});
