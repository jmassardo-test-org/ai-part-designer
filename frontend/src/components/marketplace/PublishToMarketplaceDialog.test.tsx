/**
 * Tests for the PublishToMarketplaceDialog component.
 */

import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom';
import { PublishToMarketplaceDialog } from './PublishToMarketplaceDialog';
import { server } from '@/test/mocks/server';

// Hoist mocks to ensure they're available before imports
const { mockGetCategories, mockPublishDesign, mockUnpublishDesign } = vi.hoisted(() => ({
  mockGetCategories: vi.fn(() => Promise.resolve([])),
  mockPublishDesign: vi.fn(() => Promise.resolve({ id: 'design-123', published_at: new Date().toISOString() })),
  mockUnpublishDesign: vi.fn(() => Promise.resolve(undefined)),
}));

// Close MSW server for this test file since we're using vi.mock
beforeAll(() => {
  server.close();
});

afterAll(() => {
  server.listen();
});

// Mock the ThemeContext
vi.mock('@/contexts/ThemeContext', () => ({
  useTheme: () => ({
    theme: 'dark',
    resolvedTheme: 'dark',
    setTheme: vi.fn(),
    toggleTheme: vi.fn(),
    isLoading: false,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock the WebSocketContext
vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    isConnected: false,
    connectionState: 'disconnected',
    subscribe: vi.fn(),
    unsubscribe: vi.fn(),
    sendMessage: vi.fn(),
  }),
}));

// Mock AuthContext
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'user-1', email: 'test@example.com', name: 'Test User' },
    token: 'test-token',
    isAuthenticated: true,
  }),
}));

// Mock the marketplace API
vi.mock('@/lib/marketplace', () => ({
  getCategories: mockGetCategories,
  publishDesign: mockPublishDesign,
  unpublishDesign: mockUnpublishDesign,
}));

const mockCategories = [
  { name: 'Raspberry Pi', slug: 'raspberry-pi', design_count: 10 },
  { name: 'Arduino', slug: 'arduino', design_count: 5 },
  { name: 'Electronics', slug: 'electronics', design_count: 15 },
];

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
  designId: 'design-123',
  designName: 'My Test Design',
};

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
);

describe('PublishToMarketplaceDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetCategories.mockResolvedValue(mockCategories);
    mockPublishDesign.mockResolvedValue({
      id: 'design-123',
      published_at: new Date().toISOString(),
    });
    mockUnpublishDesign.mockResolvedValue({
      id: 'design-123',
      published_at: null,
    });
  });

  it('test setup works', () => {
    expect(true).toBe(true);
  });

  it('renders the dialog when open', async () => {
    render(<PublishToMarketplaceDialog {...defaultProps} />, { wrapper });

    // The title should be visible immediately
    expect(screen.getByText('Publish to Marketplace')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<PublishToMarketplaceDialog {...defaultProps} isOpen={false} />, { wrapper });
    expect(screen.queryByText('Publish to Marketplace')).not.toBeInTheDocument();
  });

  it('displays design name', async () => {
    render(<PublishToMarketplaceDialog {...defaultProps} />, { wrapper });

    await waitFor(
      () => expect(screen.getByText('My Test Design')).toBeInTheDocument(),
      { timeout: 5000 }
    );
  });

  it('loads and displays categories', async () => {
    render(<PublishToMarketplaceDialog {...defaultProps} />, { wrapper });

    await waitFor(
      () => expect(mockGetCategories).toHaveBeenCalled(),
      { timeout: 5000 }
    );

    const select = screen.getByTestId('category-select');
    expect(select).toBeInTheDocument();
    
    await waitFor(
      () => expect(screen.getByText(/Raspberry Pi/)).toBeInTheDocument(),
      { timeout: 5000 }
    );
  });

  it('allows adding tags', async () => {
    const user = userEvent.setup();
    render(<PublishToMarketplaceDialog {...defaultProps} />, { wrapper });

    await waitFor(
      () => expect(screen.getByTestId('tag-input')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    const tagInput = screen.getByTestId('tag-input');
    await user.type(tagInput, 'my-tag');
    await user.click(screen.getByText('Add'));

    expect(screen.getByText('my-tag')).toBeInTheDocument();
  });

  it('allows removing tags', async () => {
    const user = userEvent.setup();
    render(
      <PublishToMarketplaceDialog 
        {...defaultProps} 
        currentTags={['existing-tag']} 
      />, 
      { wrapper }
    );

    await waitFor(
      () => expect(screen.getByText('existing-tag')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    const tagElement = screen.getByText('existing-tag').closest('span');
    const removeButton = tagElement?.querySelector('button');
    if (removeButton) {
      await user.click(removeButton);
    }

    expect(screen.queryByText('existing-tag')).not.toBeInTheDocument();
  });

  it('disables publish button when no category selected', async () => {
    render(<PublishToMarketplaceDialog {...defaultProps} />, { wrapper });

    await waitFor(
      () => expect(screen.getByTestId('publish-submit')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    const publishButton = screen.getByTestId('publish-submit');
    // Button should be disabled when no category is selected
    expect(publishButton).toBeDisabled();
  });

  it('calls publishDesign with correct parameters', async () => {
    const user = userEvent.setup();
    render(<PublishToMarketplaceDialog {...defaultProps} />, { wrapper });

    await waitFor(
      () => expect(screen.getByTestId('category-select')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    const select = screen.getByTestId('category-select');
    await user.selectOptions(select, 'raspberry-pi');

    const tagInput = screen.getByTestId('tag-input');
    await user.type(tagInput, 'test-tag');
    await user.click(screen.getByText('Add'));

    await user.click(screen.getByTestId('publish-submit'));

    await waitFor(
      () => expect(mockPublishDesign).toHaveBeenCalledWith(
        'design-123',
        { category: 'raspberry-pi', tags: ['test-tag'] },
        'test-token'
      ),
      { timeout: 5000 }
    );
  });

  it('shows success message after publishing', async () => {
    const user = userEvent.setup();
    render(<PublishToMarketplaceDialog {...defaultProps} />, { wrapper });

    await waitFor(
      () => expect(screen.getByTestId('category-select')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    await user.selectOptions(screen.getByTestId('category-select'), 'arduino');
    await user.click(screen.getByTestId('publish-submit'));

    await waitFor(
      () => expect(screen.getByText('Design published successfully!')).toBeInTheDocument(),
      { timeout: 5000 }
    );
  });

  it('calls onClose when close button clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<PublishToMarketplaceDialog {...defaultProps} onClose={onClose} />, { wrapper });

    await waitFor(
      () => expect(screen.getByText('Cancel')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    await user.click(screen.getByText('Cancel'));
    expect(onClose).toHaveBeenCalled();
  });

  it('shows unpublish button when already published', async () => {
    render(
      <PublishToMarketplaceDialog 
        {...defaultProps} 
        isPublished={true}
        currentCategory="raspberry-pi"
      />, 
      { wrapper }
    );

    await waitFor(
      () => {
        expect(screen.getByText('Marketplace Settings')).toBeInTheDocument();
        expect(screen.getByText('Unpublish')).toBeInTheDocument();
      },
      { timeout: 5000 }
    );
  });

  it('calls unpublishDesign when unpublish clicked', async () => {
    const user = userEvent.setup();
    render(
      <PublishToMarketplaceDialog 
        {...defaultProps} 
        isPublished={true}
        currentCategory="raspberry-pi"
      />, 
      { wrapper }
    );

    await waitFor(
      () => expect(screen.getByText('Unpublish')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    await user.click(screen.getByText('Unpublish'));

    await waitFor(
      () => expect(mockUnpublishDesign).toHaveBeenCalledWith('design-123', 'test-token'),
      { timeout: 5000 }
    );
  });

  it('calls onPublished callback after successful publish', async () => {
    const onPublished = vi.fn();
    const user = userEvent.setup();
    render(
      <PublishToMarketplaceDialog 
        {...defaultProps} 
        onPublished={onPublished}
      />, 
      { wrapper }
    );

    await waitFor(
      () => expect(screen.getByTestId('category-select')).toBeInTheDocument(),
      { timeout: 5000 }
    );

    await user.selectOptions(screen.getByTestId('category-select'), 'electronics');
    await user.click(screen.getByTestId('publish-submit'));

    await waitFor(
      () => expect(onPublished).toHaveBeenCalled(),
      { timeout: 5000 }
    );
  });
});
