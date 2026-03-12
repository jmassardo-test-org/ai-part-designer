/**
 * ContentManagementTab Tests.
 *
 * Unit tests for the ContentManagementTab component.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from '@/lib/api/admin';
import type { ContentItemListResponse, ContentCategory, ContentAnalytics } from '@/types/admin';

// Mock the admin API
vi.mock('@/lib/api/admin', () => ({
  adminApi: {
    content: {
      listFaqs: vi.fn(),
      createFaq: vi.fn(),
      updateFaq: vi.fn(),
      deleteFaq: vi.fn(),
      listArticles: vi.fn(),
      createArticle: vi.fn(),
      updateArticle: vi.fn(),
      deleteArticle: vi.fn(),
      listCategories: vi.fn(),
      createCategory: vi.fn(),
      deleteCategory: vi.fn(),
      getAnalytics: vi.fn(),
    },
  },
}));

const mockAdminApi = vi.mocked(adminApi, true);

// Import after mocks
import { ContentManagementTab } from './ContentManagementTab';

describe('ContentManagementTab', () => {
  const mockFaqsResponse: ContentItemListResponse = {
    items: [
      {
        id: 'faq-1',
        content_type: 'faq',
        title: 'How to create a design?',
        slug: 'how-to-create-design',
        body: 'Go to the designer and...',
        category: 'Getting Started',
        tags: null,
        status: 'published',
        display_order: 1,
        is_featured: false,
        view_count: 50,
        helpful_count: 10,
        not_helpful_count: 2,
        published_at: '2024-01-01T00:00:00Z',
        created_by: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-15T00:00:00Z',
      },
      {
        id: 'faq-2',
        content_type: 'faq',
        title: 'Pricing information',
        slug: 'pricing-information',
        body: 'Our plans include...',
        category: 'Billing',
        tags: null,
        status: 'draft',
        display_order: 2,
        is_featured: false,
        view_count: 10,
        helpful_count: 3,
        not_helpful_count: 0,
        published_at: null,
        created_by: null,
        created_at: '2024-02-01T00:00:00Z',
        updated_at: '2024-02-01T00:00:00Z',
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
  };

  const mockArticlesResponse: ContentItemListResponse = {
    items: [
      {
        id: 'article-1',
        content_type: 'article',
        title: 'Introduction to 3D Printing',
        slug: 'intro-3d-printing',
        body: 'A guide for beginners...',
        category: 'Guides',
        tags: null,
        status: 'published',
        display_order: 1,
        is_featured: false,
        view_count: 200,
        helpful_count: 40,
        not_helpful_count: 5,
        published_at: '2024-03-01T00:00:00Z',
        created_by: null,
        created_at: '2024-03-01T00:00:00Z',
        updated_at: '2024-03-10T00:00:00Z',
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  };

  const mockCategoriesResponse: ContentCategory[] = [
    { id: 'cat-1', name: 'Getting Started', slug: 'getting-started', description: null, display_order: 1, parent_id: null, created_at: '2024-01-01T00:00:00Z', updated_at: null },
    { id: 'cat-2', name: 'Billing', slug: 'billing', description: null, display_order: 2, parent_id: null, created_at: '2024-01-01T00:00:00Z', updated_at: null },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminApi.content.listFaqs.mockResolvedValue(mockFaqsResponse);
    mockAdminApi.content.listArticles.mockResolvedValue(mockArticlesResponse);
    mockAdminApi.content.listCategories.mockResolvedValue(mockCategoriesResponse);
    mockAdminApi.content.getAnalytics.mockResolvedValue({
      total_faqs: 5,
      total_articles: 5,
      published_faqs: 4,
      published_articles: 3,
      total_views: 5000,
      total_helpful: 200,
      total_not_helpful: 30,
      popular_items: [],
      categories_breakdown: [],
    } satisfies ContentAnalytics);
  });

  it('renders the content management heading', async () => {
    render(<ContentManagementTab />);

    expect(screen.getByText('Content Management')).toBeInTheDocument();
  });

  it('defaults to FAQs sub-tab and loads FAQs', async () => {
    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(mockAdminApi.content.listFaqs).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('How to create a design?')).toBeInTheDocument();
    });
  });

  it('switches to Articles sub-tab', async () => {
    render(<ContentManagementTab />);

    fireEvent.click(screen.getByText('Articles'));

    await waitFor(() => {
      expect(mockAdminApi.content.listArticles).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('Introduction to 3D Printing')).toBeInTheDocument();
    });
  });

  it('displays published/draft status badges', async () => {
    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(screen.getByText('published')).toBeInTheDocument();
      expect(screen.getByText('draft')).toBeInTheDocument();
    });
  });

  it('shows empty state when no FAQs exist', async () => {
    mockAdminApi.content.listFaqs.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(screen.getByText('No items found.')).toBeInTheDocument();
    });
  });

  it('handles API error gracefully', async () => {
    mockAdminApi.content.listFaqs.mockRejectedValue(new Error('Network error'));

    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load content')).toBeInTheDocument();
    });
  });

  it('opens create modal when Add FAQ is clicked', async () => {
    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(screen.getByText('How to create a design?')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText(/New FAQ/i));

    await waitFor(() => {
      expect(screen.getByText('Title *')).toBeInTheDocument();
    });
  });

  it('opens categories view', async () => {
    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(screen.getByText('How to create a design?')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Categories'));

    await waitFor(() => {
      expect(mockAdminApi.content.listCategories).toHaveBeenCalled();
    });
  });

  it('opens analytics view', async () => {
    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(screen.getByText('How to create a design?')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Analytics'));

    await waitFor(() => {
      expect(mockAdminApi.content.getAnalytics).toHaveBeenCalled();
    });
  });

  it('deletes a FAQ with confirmation', async () => {
    mockAdminApi.content.deleteFaq.mockResolvedValue({ message: 'Deleted' });

    render(<ContentManagementTab />);

    await waitFor(() => {
      expect(screen.getByText('How to create a design?')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('Delete');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to delete/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Delete'));

    await waitFor(() => {
      expect(mockAdminApi.content.deleteFaq).toHaveBeenCalledWith('faq-1');
    });
  });
});
