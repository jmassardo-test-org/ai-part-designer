/**
 * Tests for the saveEditAsVersion function in the designs API client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { saveEditAsVersion } from './designs';

describe('saveEditAsVersion', () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('sends POST request to correct endpoint with auth header', async () => {
    const mockResponse = {
      version_id: 'v-123',
      version_number: 2,
      design_id: 'd-456',
      message: 'Version 2 created successfully',
    };

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await saveEditAsVersion(
      'd-456',
      {
        job_id: 'job-789',
        change_description: 'Increased width to 150mm',
      },
      'test-auth-token',
    );

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/designs/d-456/versions',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json',
          Authorization: 'Bearer test-auth-token',
        }),
      }),
    );

    expect(result).toEqual(mockResponse);
  });

  it('includes parameters when provided', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          version_id: 'v-1',
          version_number: 1,
          design_id: 'd-1',
          message: 'ok',
        }),
    });

    await saveEditAsVersion(
      'd-1',
      {
        job_id: 'job-1',
        change_description: 'Test',
        parameters: { width: 200, depth: 100 },
      },
      'token',
    );

    const callArgs = vi.mocked(global.fetch).mock.calls[0];
    const body = JSON.parse(callArgs[1]?.body as string);

    expect(body.parameters).toEqual({ width: 200, depth: 100 });
  });

  it('includes file_url when provided', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          version_id: 'v-1',
          version_number: 1,
          design_id: 'd-1',
          message: 'ok',
        }),
    });

    await saveEditAsVersion(
      'd-1',
      {
        job_id: 'job-1',
        change_description: 'Custom url',
        file_url: 'https://custom.example.com/file.stl',
      },
      'token',
    );

    const callArgs = vi.mocked(global.fetch).mock.calls[0];
    const body = JSON.parse(callArgs[1]?.body as string);

    expect(body.file_url).toBe('https://custom.example.com/file.stl');
  });

  it('throws error with detail message on failure', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Design not found' }),
    });

    await expect(
      saveEditAsVersion(
        'd-not-found',
        { job_id: 'j', change_description: 'x' },
        'token',
      ),
    ).rejects.toThrow('Design not found');
  });

  it('throws generic error when response has no detail', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('parse error')),
    });

    await expect(
      saveEditAsVersion(
        'd-err',
        { job_id: 'j', change_description: 'x' },
        'token',
      ),
    ).rejects.toThrow('Save version failed');
  });
});
