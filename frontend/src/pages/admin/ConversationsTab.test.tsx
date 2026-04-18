/**
 * ConversationsTab Tests.
 *
 * Unit tests for the ConversationsTab component.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { adminApi } from '@/lib/api/admin';
import type { ConversationDetail } from '@/types/admin';

// Mock the admin API
vi.mock('@/lib/api/admin', () => ({
  adminApi: {
    conversations: {
      getStats: vi.fn(),
      getFlagged: vi.fn(),
      get: vi.fn(),
      getQualityMetrics: vi.fn(),
      export: vi.fn(),
    },
  },
}));

const mockAdminApi = vi.mocked(adminApi, true);

// Import after mocks
import { ConversationsTab } from './ConversationsTab';

describe('ConversationsTab', () => {
  const mockStatsResponse = {
    total_conversations: 500,
    total_messages: 3500,
    avg_messages_per_conversation: 7.0,
    active_today: 25,
    active_this_week: 100,
    conversations_by_status: { completed: 400, active: 80, failed: 20 },
  };

  const mockFlaggedResponse = {
    items: [
      {
        id: 'conv-1',
        user_id: 'user-1',
        user_email: 'alice@example.com',
        title: 'Problematic request',
        status: 'completed' as const,
        message_count: 12,
        flag_reason: 'inappropriate_content',
        created_at: '2024-03-01T00:00:00Z',
      },
      {
        id: 'conv-2',
        user_id: 'user-2',
        user_email: 'bob@example.com',
        title: null,
        status: 'failed' as const,
        message_count: 3,
        flag_reason: 'prompt_injection',
        created_at: '2024-03-05T00:00:00Z',
      },
    ],
    total: 2,
    page: 1,
    page_size: 20,
  };

  const mockQualityResponse = {
    total_conversations: 500,
    completed_conversations: 400,
    failed_conversations: 20,
    completion_rate: 0.8,
    avg_messages_to_completion: 5.5,
    conversations_by_status: { completed: 400, active: 80, failed: 20 },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockAdminApi.conversations.getStats.mockResolvedValue(mockStatsResponse);
    mockAdminApi.conversations.getFlagged.mockResolvedValue(mockFlaggedResponse);
    mockAdminApi.conversations.getQualityMetrics.mockResolvedValue(mockQualityResponse);
  });

  it('renders the conversations heading', async () => {
    render(<ConversationsTab />);

    expect(screen.getByText('Conversations')).toBeInTheDocument();
  });

  it('fetches and displays flagged conversations on mount', async () => {
    render(<ConversationsTab />);

    await waitFor(() => {
      expect(mockAdminApi.conversations.getFlagged).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
      expect(screen.getByText('bob@example.com')).toBeInTheDocument();
    });
  });

  it('fetches stats on mount', async () => {
    render(<ConversationsTab />);

    await waitFor(() => {
      expect(mockAdminApi.conversations.getStats).toHaveBeenCalled();
    });
  });

  it('displays status badges for flagged conversations', async () => {
    render(<ConversationsTab />);

    await waitFor(() => {
      expect(screen.getByText('completed')).toBeInTheDocument();
      expect(screen.getByText('failed')).toBeInTheDocument();
    });
  });

  it('displays flag reasons', async () => {
    render(<ConversationsTab />);

    await waitFor(() => {
      expect(screen.getByText('inappropriate_content')).toBeInTheDocument();
      expect(screen.getByText('prompt_injection')).toBeInTheDocument();
    });
  });

  it('shows empty state when no flagged conversations', async () => {
    mockAdminApi.conversations.getFlagged.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    render(<ConversationsTab />);

    await waitFor(() => {
      expect(screen.getByText('No flagged conversations.')).toBeInTheDocument();
    });
  });

  it('opens conversation detail modal', async () => {
    mockAdminApi.conversations.get.mockResolvedValue({
      id: 'conv-1',
      user_id: 'user-1',
      user_email: 'alice@example.com',
      title: 'Problematic request',
      status: 'completed',
      design_id: null,
      intent_data: {},
      build_plan_data: null,
      result_data: null,
      messages: [
        { role: 'user', content: 'Hello' },
        { role: 'assistant', content: 'How can I help?' },
      ],
      created_at: '2024-03-01T00:00:00Z',
      updated_at: null,
    } satisfies ConversationDetail);

    render(<ConversationsTab />);

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });

    const viewButtons = screen.getAllByTitle('View Detail');
    fireEvent.click(viewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Conversation Detail')).toBeInTheDocument();
      expect(mockAdminApi.conversations.get).toHaveBeenCalledWith('conv-1');
    });
  });

  it('switches to stats view', async () => {
    render(<ConversationsTab />);

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Stats'));

    await waitFor(() => {
      expect(screen.getByText('Conversation Statistics')).toBeInTheDocument();
    });
  });

  it('switches to quality metrics view', async () => {
    render(<ConversationsTab />);

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Quality'));

    await waitFor(() => {
      expect(screen.getByText('Quality Metrics')).toBeInTheDocument();
      expect(mockAdminApi.conversations.getQualityMetrics).toHaveBeenCalled();
    });
  });

  it('triggers export', async () => {
    const mockBlob = new Blob(['test'], { type: 'text/csv' });
    mockAdminApi.conversations.export.mockResolvedValue(mockBlob);

    render(<ConversationsTab />);

    await waitFor(() => {
      expect(screen.getByText('alice@example.com')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Export'));

    await waitFor(() => {
      expect(mockAdminApi.conversations.export).toHaveBeenCalledWith({ format: 'csv' });
    });
  });

  it('refreshes flagged list', async () => {
    render(<ConversationsTab />);

    await waitFor(() => {
      expect(mockAdminApi.conversations.getFlagged).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByText('Refresh'));

    await waitFor(() => {
      expect(mockAdminApi.conversations.getFlagged).toHaveBeenCalledTimes(2);
    });
  });
});
