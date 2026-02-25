/**
 * Tests for MarketplaceDesignDetailPage component.
 *
 * Tests loading, error, detail rendering, and conditional UI
 * for the marketplace design detail view.
 */

import { screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderWithRouter } from '@/test/utils';
import { MarketplaceDesignDetailPage } from './MarketplaceDesignDetailPage';

// =============================================================================
// Mocks
// =============================================================================

const mockGetDesignDetail = vi.fn();
const mockGetRatingSummary = vi.fn();
const mockGetDesignRatings = vi.fn();
const mockGetDesignComments = vi.fn();
const mockGetMyRating = vi.fn();
const mockCheckReportStatus = vi.fn();
const mockTrackDesignView = vi.fn();

vi.mock('@/lib/marketplace', () => ({
  getDesignDetail: (...args: unknown[]) => mockGetDesignDetail(...args),
  getRatingSummary: (...args: unknown[]) => mockGetRatingSummary(...args),
  getDesignRatings: (...args: unknown[]) => mockGetDesignRatings(...args),
  getDesignComments: (...args: unknown[]) => mockGetDesignComments(...args),
  getMyRating: (...args: unknown[]) => mockGetMyRating(...args),
  checkReportStatus: (...args: unknown[]) => mockCheckReportStatus(...args),
  trackDesignView: (...args: unknown[]) => mockTrackDesignView(...args),
  rateDesign: vi.fn(),
  deleteRating: vi.fn(),
  createComment: vi.fn(),
  updateComment: vi.fn(),
  deleteComment: vi.fn(),
  remixDesign: vi.fn(),
  reportDesign: vi.fn(),
}));

// Authenticated non-owner mock
const mockAuthNonOwner = {
  token: 'mock-token',
  user: { id: 'user-999', email: 'viewer@example.com' },
  isLoading: false,
  isAuthenticated: true,
};

// Authenticated owner mock
const mockAuthOwner = {
  token: 'mock-token',
  user: { id: 'author-123', email: 'owner@example.com' },
  isLoading: false,
  isAuthenticated: true,
};

// Unauthenticated mock
const mockAuthAnonymous = {
  token: null,
  user: null,
  isLoading: false,
  isAuthenticated: false,
};

let currentAuthMock = mockAuthNonOwner;

vi.mock('@/contexts/AuthContext', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/contexts/AuthContext')>();
  return {
    ...actual,
    useAuth: () => currentAuthMock,
  };
});

// =============================================================================
// Test Data
// =============================================================================

const mockDesign = {
  id: 'design-123',
  name: 'Awesome Enclosure',
  description: 'A well-designed enclosure for electronics projects.',
  thumbnail_url: '/images/enc.png',
  category: 'electronics',
  tags: ['enclosure', '3d-print'],
  save_count: 15,
  remix_count: 7,
  is_starter: false,
  created_at: '2025-01-01T10:00:00Z',
  published_at: '2025-01-02T12:00:00Z',
  author_id: 'author-123',
  author_name: 'Design Master',
  avg_rating: 4.5,
  total_ratings: 12,
  is_saved: false,
  in_lists: [],
  remixed_from_id: null,
  remixed_from_name: null,
  featured_at: null,
  has_step: true,
  has_stl: true,
  view_count: 248,
};

const mockRatingSummary = {
  design_id: 'design-123',
  average_rating: 4.5,
  total_ratings: 12,
  rating_distribution: { 1: 0, 2: 1, 3: 1, 4: 3, 5: 7 },
};

const mockRatings = {
  ratings: [
    {
      id: 'rating-1',
      design_id: 'design-123',
      user_id: 'u1',
      rating: 5,
      review: 'Perfect!',
      created_at: '2025-01-10T10:00:00Z',
      updated_at: '2025-01-10T10:00:00Z',
      user_name: 'Reviewer 1',
    },
  ],
  total: 1,
  page: 1,
  page_size: 20,
};

const mockComments = {
  comments: [],
  total: 0,
  page: 1,
  page_size: 50,
};

// =============================================================================
// Tests
// =============================================================================

describe('MarketplaceDesignDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    currentAuthMock = mockAuthNonOwner;
    mockGetDesignDetail.mockResolvedValue(mockDesign);
    mockGetRatingSummary.mockResolvedValue(mockRatingSummary);
    mockGetDesignRatings.mockResolvedValue(mockRatings);
    mockGetDesignComments.mockResolvedValue(mockComments);
    mockGetMyRating.mockResolvedValue(null);
    mockCheckReportStatus.mockResolvedValue({ already_reported: false });
    mockTrackDesignView.mockResolvedValue(undefined);
  });

  it('renders loading state', () => {
    /** Loading spinner is shown before data loads. */
    mockGetDesignDetail.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeDefined();
  });

  it('renders error state when design not found', async () => {
    /** Error message is displayed when the API rejects. */
    mockGetDesignDetail.mockRejectedValue(new Error('Not found'));

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Design Not Found')).toBeInTheDocument();
    });
  });

  it('renders design details', async () => {
    /** Shows design name, description, author, and stats after loading. */
    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    expect(
      screen.getByText('A well-designed enclosure for electronics projects.')
    ).toBeInTheDocument();
    expect(screen.getByText('Design Master')).toBeInTheDocument();
    // File format badges
    expect(screen.getByText('STL')).toBeInTheDocument();
    expect(screen.getByText('STEP')).toBeInTheDocument();
  });

  it('shows remix button for non-owner', async () => {
    /** Non-owner users see the "Remix This Design" button. */
    currentAuthMock = mockAuthNonOwner;

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /remix this design/i })).toBeInTheDocument();
  });

  it('hides remix button for owner', async () => {
    /** Design owner should NOT see the remix button. */
    currentAuthMock = mockAuthOwner;

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /remix this design/i })).toBeNull();
  });

  it('shows report button for authenticated non-owner', async () => {
    /** Authenticated non-owners see "Report Design" button. */
    currentAuthMock = mockAuthNonOwner;

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: /report design/i })).toBeInTheDocument();
  });

  it('hides report button for unauthenticated user', async () => {
    /** Anonymous users should NOT see the "Report Design" button. */
    currentAuthMock = mockAuthAnonymous;

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /report design/i })).toBeNull();
  });

  it('hides report button for owner', async () => {
    /** Design owner should NOT see report button. */
    currentAuthMock = mockAuthOwner;

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /report design/i })).toBeNull();
  });

  it('tracks view on load', async () => {
    /** trackDesignView is called when the page loads. */
    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    expect(mockTrackDesignView).toHaveBeenCalledWith('design-123');
  });

  it('displays tags', async () => {
    /** Design tags are rendered as badges. */
    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('#enclosure')).toBeInTheDocument();
      expect(screen.getByText('#3d-print')).toBeInTheDocument();
    });
  });

  it('displays back to marketplace link', async () => {
    /** The "Back to Marketplace" link points to /marketplace. */
    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    const backLinks = screen.getAllByRole('link', { name: /back to marketplace/i });
    expect(backLinks[0]).toHaveAttribute('href', '/marketplace');
  });

  it('shows already reported state', async () => {
    /** When user already reported, button shows "Already Reported" and is disabled. */
    currentAuthMock = mockAuthNonOwner;
    mockCheckReportStatus.mockResolvedValue({ already_reported: true });

    renderWithRouter(<MarketplaceDesignDetailPage />, {
      initialEntries: ['/marketplace/design-123'],
      route: '/marketplace/:designId',
    });

    await waitFor(() => {
      expect(screen.getByText('Awesome Enclosure')).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /already reported/i })).toBeInTheDocument();
    });
  });
});
