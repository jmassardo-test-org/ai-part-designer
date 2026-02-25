/**
 * Tests for marketplace API functions (Epic 20 additions).
 *
 * Tests the new rating, comment, remix, report, and view tracking
 * API functions for correct URL construction, method, and error handling.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  getDesignDetail,
  rateDesign,
  deleteRating,
  getRatingSummary,
  getDesignRatings,
  getMyRating,
  getDesignComments,
  createComment,
  updateComment,
  deleteComment,
  remixDesign,
  reportDesign,
  checkReportStatus,
  trackDesignView,
} from '@/lib/marketplace';

// =============================================================================
// Setup: Mock global fetch
// =============================================================================

const mockFetch = vi.fn();

beforeEach(() => {
  mockFetch.mockClear();
  vi.stubGlobal('fetch', mockFetch);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function jsonOk(data: unknown) {
  return {
    ok: true,
    status: 200,
    json: () => Promise.resolve(data),
  };
}

function jsonError(status: number) {
  return {
    ok: false,
    status,
    json: () => Promise.resolve({ detail: 'Error' }),
  };
}

// =============================================================================
// getDesignDetail
// =============================================================================

describe('getDesignDetail', () => {
  it('calls correct URL without auth', async () => {
    /** Fetches from /api/v2/marketplace/designs/:id without auth header. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'd1', name: 'Test' }));

    await getDesignDetail('d1');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/marketplace/designs/d1',
      expect.objectContaining({ headers: {} })
    );
  });

  it('includes auth header when token provided', async () => {
    /** Auth header is included when a token is passed. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'd1' }));

    await getDesignDetail('d1', 'tok-123');

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers['Authorization']).toBe('Bearer tok-123');
  });

  it('throws on error response', async () => {
    /** Rejects when the API returns a non-OK status. */
    mockFetch.mockResolvedValueOnce(jsonError(404));

    await expect(getDesignDetail('bad-id')).rejects.toThrow('Failed to get design detail');
  });
});

// =============================================================================
// rateDesign
// =============================================================================

describe('rateDesign', () => {
  it('sends PUT with correct body', async () => {
    /** PUT request to ratings endpoint with rating and review in body. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'r1', rating: 5 }));

    await rateDesign('d1', 5, 'Great!', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/ratings');
    expect(opts.method).toBe('PUT');
    expect(JSON.parse(opts.body)).toEqual({ rating: 5, review: 'Great!' });
  });

  it('sends null review when omitted', async () => {
    /** Review defaults to null when not provided. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'r1', rating: 3 }));

    await rateDesign('d1', 3, undefined, 'tok');

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.review).toBeNull();
  });

  it('throws on error', async () => {
    /** Rejects on non-OK status. */
    mockFetch.mockResolvedValueOnce(jsonError(400));
    await expect(rateDesign('d1', 5, undefined, 'tok')).rejects.toThrow('Failed to rate design');
  });
});

// =============================================================================
// deleteRating
// =============================================================================

describe('deleteRating', () => {
  it('sends DELETE to correct URL', async () => {
    /** DELETE request to the ratings endpoint. */
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

    await deleteRating('d1', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/ratings');
    expect(opts.method).toBe('DELETE');
  });

  it('throws on error', async () => {
    /** Rejects when the rating is not found. */
    mockFetch.mockResolvedValueOnce(jsonError(404));
    await expect(deleteRating('d1', 'tok')).rejects.toThrow('Failed to delete rating');
  });
});

// =============================================================================
// getRatingSummary
// =============================================================================

describe('getRatingSummary', () => {
  it('fetches from summary endpoint', async () => {
    /** GET request to ratings/summary. */
    const summary = { average_rating: 4.2, total_ratings: 10 };
    mockFetch.mockResolvedValueOnce(jsonOk(summary));

    const result = await getRatingSummary('d1');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/marketplace/designs/d1/ratings/summary'
    );
    expect(result).toEqual(summary);
  });

  it('throws on error', async () => {
    /** Rejects on non-OK status. */
    mockFetch.mockResolvedValueOnce(jsonError(500));
    await expect(getRatingSummary('d1')).rejects.toThrow('Failed to get rating summary');
  });
});

// =============================================================================
// getDesignRatings
// =============================================================================

describe('getDesignRatings', () => {
  it('includes page and page_size params', async () => {
    /** Query parameters are appended correctly. */
    mockFetch.mockResolvedValueOnce(jsonOk({ ratings: [], total: 0 }));

    await getDesignRatings('d1', 2, 10);

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/marketplace/designs/d1/ratings?page=2&page_size=10'
    );
  });

  it('uses defaults for page params', async () => {
    /** Default page=1 and pageSize=20. */
    mockFetch.mockResolvedValueOnce(jsonOk({ ratings: [], total: 0 }));

    await getDesignRatings('d1');

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/marketplace/designs/d1/ratings?page=1&page_size=20'
    );
  });
});

// =============================================================================
// getMyRating
// =============================================================================

describe('getMyRating', () => {
  it('fetches from ratings/me with auth', async () => {
    /** GET request with auth header. */
    const myRating = { id: 'r1', rating: 4 };
    mockFetch.mockResolvedValueOnce(jsonOk(myRating));

    const result = await getMyRating('d1', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/ratings/me');
    expect(opts.headers['Authorization']).toBe('Bearer tok');
    expect(result).toEqual(myRating);
  });

  it('returns null on 404', async () => {
    /** Returns null instead of throwing when rating is not found. */
    mockFetch.mockResolvedValueOnce(jsonError(404));

    const result = await getMyRating('d1', 'tok');
    expect(result).toBeNull();
  });

  it('throws on other errors', async () => {
    /** Non-404 errors are thrown. */
    mockFetch.mockResolvedValueOnce(jsonError(500));
    await expect(getMyRating('d1', 'tok')).rejects.toThrow('Failed to get my rating');
  });
});

// =============================================================================
// getDesignComments
// =============================================================================

describe('getDesignComments', () => {
  it('fetches with pagination params', async () => {
    /** GET request with page query params. */
    mockFetch.mockResolvedValueOnce(jsonOk({ comments: [], total: 0 }));

    await getDesignComments('d1', 3, 25);

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/v2/marketplace/designs/d1/comments?page=3&page_size=25'
    );
  });
});

// =============================================================================
// createComment
// =============================================================================

describe('createComment', () => {
  it('sends POST with content and parent_id', async () => {
    /** POST request with correct body for threaded replies. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'c1', content: 'Hello!' }));

    await createComment('d1', 'Hello!', 'parent-id', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/comments');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ content: 'Hello!', parent_id: 'parent-id' });
  });

  it('sends null parent_id for top-level comments', async () => {
    /** Top-level comments have parent_id=null. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'c2' }));

    await createComment('d1', 'Top comment', undefined, 'tok');

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.parent_id).toBeNull();
  });

  it('throws on error', async () => {
    /** Rejects on non-OK status. */
    mockFetch.mockResolvedValueOnce(jsonError(400));
    await expect(createComment('d1', 'oops')).rejects.toThrow('Failed to create comment');
  });
});

// =============================================================================
// updateComment
// =============================================================================

describe('updateComment', () => {
  it('sends PUT to comments/:id', async () => {
    /** PUT request to update comment content. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'c1', content: 'Updated' }));

    await updateComment('c1', 'Updated', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/comments/c1');
    expect(opts.method).toBe('PUT');
    expect(JSON.parse(opts.body)).toEqual({ content: 'Updated' });
  });

  it('throws on error', async () => {
    /** Rejects on unauthorized update. */
    mockFetch.mockResolvedValueOnce(jsonError(403));
    await expect(updateComment('c1', 'x', 'tok')).rejects.toThrow('Failed to update comment');
  });
});

// =============================================================================
// deleteComment
// =============================================================================

describe('deleteComment', () => {
  it('sends DELETE to comments/:id', async () => {
    /** DELETE request to remove a comment. */
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

    await deleteComment('c1', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/comments/c1');
    expect(opts.method).toBe('DELETE');
  });
});

// =============================================================================
// remixDesign
// =============================================================================

describe('remixDesign', () => {
  it('sends POST to remix endpoint', async () => {
    /** POST request to create a remix. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'remix-1', name: 'My Remix' }));

    await remixDesign('d1', 'My Remix', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/remix');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ name: 'My Remix' });
  });

  it('sends no body when name not provided', async () => {
    /** Body is undefined when no custom name. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'remix-2' }));

    await remixDesign('d1', undefined, 'tok');

    const body = mockFetch.mock.calls[0][1].body;
    expect(body).toBeUndefined();
  });

  it('throws on error', async () => {
    /** Rejects on non-OK status. */
    mockFetch.mockResolvedValueOnce(jsonError(400));
    await expect(remixDesign('d1', undefined, 'tok')).rejects.toThrow('Failed to remix design');
  });
});

// =============================================================================
// reportDesign
// =============================================================================

describe('reportDesign', () => {
  it('sends POST with reason and description', async () => {
    /** POST request with report details. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'rep-1', status: 'pending' }));

    await reportDesign('d1', 'spam', 'Clearly spam', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/report');
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ reason: 'spam', description: 'Clearly spam' });
  });

  it('sends null description when omitted', async () => {
    /** Description defaults to null when not provided. */
    mockFetch.mockResolvedValueOnce(jsonOk({ id: 'rep-2' }));

    await reportDesign('d1', 'copyright', undefined, 'tok');

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.description).toBeNull();
  });

  it('throws on error', async () => {
    /** Rejects on duplicate report or other error. */
    mockFetch.mockResolvedValueOnce(jsonError(409));
    await expect(reportDesign('d1', 'spam', undefined, 'tok')).rejects.toThrow(
      'Failed to report design'
    );
  });
});

// =============================================================================
// checkReportStatus
// =============================================================================

describe('checkReportStatus', () => {
  it('fetches with auth header', async () => {
    /** GET request with auth to check report status. */
    mockFetch.mockResolvedValueOnce(jsonOk({ already_reported: false }));

    const result = await checkReportStatus('d1', 'tok');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/report/status');
    expect(opts.headers['Authorization']).toBe('Bearer tok');
    expect(result).toEqual({ already_reported: false });
  });

  it('throws on error', async () => {
    /** Rejects on non-OK status. */
    mockFetch.mockResolvedValueOnce(jsonError(500));
    await expect(checkReportStatus('d1', 'tok')).rejects.toThrow(
      'Failed to check report status'
    );
  });
});

// =============================================================================
// trackDesignView
// =============================================================================

describe('trackDesignView', () => {
  it('sends POST to view endpoint', async () => {
    /** Fire-and-forget POST to track a view. */
    mockFetch.mockResolvedValueOnce({ ok: true, status: 204 });

    await trackDesignView('d1');

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v2/marketplace/designs/d1/view');
    expect(opts.method).toBe('POST');
  });

  it('does not throw on error (fire-and-forget)', async () => {
    /** View tracking silently ignores errors. */
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    // Should not throw
    await expect(trackDesignView('d1')).resolves.toBeUndefined();
  });
});
