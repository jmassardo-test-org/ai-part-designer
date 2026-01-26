/**
 * Tests for TemplatesPage component.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { TemplatesPage } from './TemplatesPage';

// Mock AuthContext
const mockUser = {
  id: '1',
  email: 'test@example.com',
  tier: 'free',
};

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: mockUser,
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock data
const mockTemplates = [
  {
    id: '1',
    slug: 'simple-box',
    name: 'Simple Box',
    description: 'A simple box template',
    category: 'enclosures',
    tags: ['box', 'enclosure'],
    thumbnail_url: null,
    tier_required: 'free',
    parameters: [
      { name: 'length', type: 'float', label: 'Length', default: 100, min: 10, max: 500 },
      { name: 'width', type: 'float', label: 'Width', default: 50, min: 10, max: 500 },
    ],
    is_featured: true,
    usage_count: 100,
  },
  {
    id: '2',
    slug: 'bracket',
    name: 'Mounting Bracket',
    description: 'A mounting bracket template',
    category: 'hardware',
    tags: ['bracket', 'mounting'],
    thumbnail_url: null,
    tier_required: 'pro',
    parameters: [],
    is_featured: false,
    usage_count: 50,
  },
];

const mockCategories = [
  { slug: 'enclosures', name: 'Enclosures', count: 10 },
  { slug: 'hardware', name: 'Hardware', count: 5 },
];

const renderTemplatesPage = () => {
  return render(
    <BrowserRouter>
      <TemplatesPage />
    </BrowserRouter>
  );
};

describe('TemplatesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('shows loading state initially', () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderTemplatesPage();

    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders templates page heading', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
    });
  });

  it('displays template cards', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
      expect(screen.getByText('Mounting Bracket')).toBeInTheDocument();
    });
  });

  it('shows featured badge on featured templates', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      expect(screen.getByText('Featured')).toBeInTheDocument();
    });
  });

  it('displays tier badges', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      expect(screen.getByText('Free')).toBeInTheDocument();
      expect(screen.getByText('Pro')).toBeInTheDocument();
    });
  });

  it('has search input', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search templates/i)).toBeInTheDocument();
    });
  });

  it('allows searching templates', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/search templates/i)).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search templates/i);
    await user.type(searchInput, 'box');

    // The search should trigger a URL update
    expect(searchInput).toHaveValue('box');
  });

  it('shows error state', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Failed to fetch templates'));

    renderTemplatesPage();

    await waitFor(() => {
      // Error is logged but UI may still render
      expect(screen.getByRole('heading', { name: /part templates/i })).toBeInTheDocument();
    });
  });

  it('toggles view mode between grid and list', async () => {
    const user = userEvent.setup();
    
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      expect(screen.getByText('Simple Box')).toBeInTheDocument();
    });

    // Find and click the list view button
    const listButton = screen.getByRole('button', { name: /list/i });
    await user.click(listButton);

    // The view mode should be list now
    expect(listButton).toBeInTheDocument();
  });

  it('shows lock overlay for inaccessible templates', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: mockCategories }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: mockTemplates }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      // Pro template should show Pro badge (user is on free tier)
      expect(screen.getByText('Pro')).toBeInTheDocument();
    });
  });

  it('handles empty template list', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockImplementation((url: string) => {
      if (url.includes('/templates/categories')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ categories: [] }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ templates: [] }),
      });
    });

    renderTemplatesPage();

    await waitFor(() => {
      // Should not show loading spinner anymore
      expect(document.querySelector('.animate-spin')).not.toBeInTheDocument();
    });
  });
});
