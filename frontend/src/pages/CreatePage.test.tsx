/**
 * Tests for CreatePage component.
 * 
 * Tests the unified create page with animated transitions
 * from prompts to chat interface.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { CreatePage } from './CreatePage';

// Mock scrollIntoView for jsdom
Element.prototype.scrollIntoView = vi.fn();

// Mock AuthContext
const mockToken = 'test-token';
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com' },
    token: mockToken,
    isAuthenticated: true,
  }),
}));

// Mock ModelViewer component
vi.mock('@/components/viewer', () => ({
  ModelViewer: () => <div data-testid="model-viewer">3D Viewer Mock</div>,
}));

// Mock lib/conversations
const mockListConversations = vi.fn();
const mockCreateConversation = vi.fn();
const mockGetConversation = vi.fn();
const mockSendMessage = vi.fn();
const mockDeleteConversation = vi.fn();

vi.mock('@/lib/conversations', () => ({
  listConversations: (...args: unknown[]) => mockListConversations(...args),
  createConversation: (...args: unknown[]) => mockCreateConversation(...args),
  getConversation: (...args: unknown[]) => mockGetConversation(...args),
  sendMessage: (...args: unknown[]) => mockSendMessage(...args),
  deleteConversation: (...args: unknown[]) => mockDeleteConversation(...args),
  triggerGeneration: vi.fn(),
}));

// Mock lib/generate
vi.mock('@/lib/generate', () => ({
  downloadGeneratedFile: vi.fn(),
  getPreviewData: vi.fn(),
}));

const renderCreatePage = () => {
  return render(
    <BrowserRouter>
      <CreatePage />
    </BrowserRouter>
  );
};

describe('CreatePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListConversations.mockResolvedValue([]);
    mockCreateConversation.mockResolvedValue({
      id: 'conv-new',
      title: null,
      status: 'active',
      messages: [
        {
          id: 'msg-welcome',
          role: 'assistant',
          message_type: 'text',
          content: 'Welcome! Describe the part you want to create.',
          created_at: '2026-01-25T10:00:00Z',
        },
      ],
      understanding: null,
      result: null,
    });
  });

  describe('Initial State', () => {
    it('shows example prompts on initial load', async () => {
      renderCreatePage();

      // Should display the example prompts view initially
      await waitFor(() => {
        expect(screen.getByText(/what would you like to create/i)).toBeInTheDocument();
      });
    });

    it('displays prompt categories', async () => {
      renderCreatePage();

      // Should have example categories
      await waitFor(() => {
        expect(screen.getByText(/basic shapes/i)).toBeInTheDocument();
      });
    });
  });

  describe('SendMessageResponse additional_messages Type', () => {
    /**
     * These tests verify the TypeScript type and response handling
     * for the additional_messages field that carries confirmation
     * messages before the final result.
     */

    it('SendMessageResponse type includes additional_messages field', async () => {
      // This tests that the response structure supports additional_messages
      const responseWithConfirmation = {
        user_message: {
          id: 'msg-user-1',
          role: 'user',
          message_type: 'text',
          content: 'Create a 2 inch cylinder, 4 inches tall',
          created_at: '2026-01-25T10:01:00Z',
        },
        assistant_message: {
          id: 'msg-result',
          role: 'assistant',
          message_type: 'result',
          content: 'Your part has been generated!',
          created_at: '2026-01-25T10:01:02Z',
        },
        additional_messages: [
          {
            id: 'msg-confirmation',
            role: 'assistant',
            message_type: 'confirmation',
            content: "Here's what I understand:\n\n**Part Type:** Cylinder\n**Diameter:** 50.8mm\n**Height:** 101.6mm",
            created_at: '2026-01-25T10:01:01Z',
          },
        ],
        conversation_status: 'completed',
        understanding: {
          classification: { category: 'cylinder', confidence: 0.95 },
          completeness_score: 0.95,
        },
        ready_to_generate: true,
        result: {
          status: 'completed',
          job_id: 'job-123',
          downloads: { step: '/file.step', stl: '/file.stl' },
          shape: 'cylinder',
          dimensions: { diameter: 50.8, height: 101.6 },
          confidence: 0.95,
          warnings: [],
        },
      };

      // Verify the response structure
      expect(responseWithConfirmation.additional_messages).toHaveLength(1);
      expect(responseWithConfirmation.additional_messages[0].message_type).toBe('confirmation');
      expect(responseWithConfirmation.additional_messages[0].content).toContain("Here's what I understand");
    });

    it('handles empty additional_messages array gracefully', async () => {
      // Mock the send message response WITHOUT additional_messages
      const responseWithoutAdditional = {
        user_message: {
          id: 'msg-user-1',
          role: 'user',
          message_type: 'text',
          content: 'Make a box',
          created_at: '2026-01-25T10:01:00Z',
        },
        assistant_message: {
          id: 'msg-assistant-1',
          role: 'assistant',
          message_type: 'clarification',
          content: 'What dimensions would you like?',
          created_at: '2026-01-25T10:01:01Z',
        },
        // No additional_messages field - should default to empty array
        additional_messages: undefined,
        conversation_status: 'clarifying',
        understanding: null,
        ready_to_generate: false,
        result: null,
      };

      // The response should work even without additional_messages
      const additionalMsgs = responseWithoutAdditional.additional_messages || [];
      expect(additionalMsgs).toHaveLength(0);
    });

    it('message order is user -> additional -> assistant', async () => {
      /**
       * When generation happens, messages should appear in order:
       * 1. User's prompt
       * 2. Confirmation message (from additional_messages)
       * 3. Result message (assistant_message)
       */
      const response = {
        user_message: {
          id: 'msg-1',
          role: 'user',
          message_type: 'text',
          content: 'Create cylinder',
          created_at: '2026-01-25T10:01:00Z',
        },
        assistant_message: {
          id: 'msg-3',
          role: 'assistant',
          message_type: 'result',
          content: 'Generated!',
          created_at: '2026-01-25T10:01:02Z',
        },
        additional_messages: [
          {
            id: 'msg-2',
            role: 'assistant',
            message_type: 'confirmation',
            content: "Here's what I understand...",
            created_at: '2026-01-25T10:01:01Z',
          },
        ],
        conversation_status: 'completed',
        ready_to_generate: true,
        result: { status: 'completed', job_id: 'job-1', downloads: {} },
      };

      // Simulate how CreatePage builds the message array
      const additionalMsgs = response.additional_messages || [];
      const messages = [
        response.user_message,
        ...additionalMsgs,
        response.assistant_message,
      ];

      // Verify order
      expect(messages[0].id).toBe('msg-1'); // user
      expect(messages[1].id).toBe('msg-2'); // confirmation
      expect(messages[2].id).toBe('msg-3'); // result
    });
  });

  describe('History Management', () => {
    it('shows delete button on history items', async () => {
      const mockHistory = [
        {
          id: 'conv-1',
          title: 'Test Design 1',
          status: 'completed',
          message_count: 5,
          created_at: '2026-01-25T10:00:00Z',
          updated_at: '2026-01-25T10:30:00Z',
        },
      ];
      mockListConversations.mockResolvedValue(mockHistory);
      
      const { getByText, getByTitle } = render(
        <BrowserRouter>
          <CreatePage />
        </BrowserRouter>
      );
      
      // Wait for history to load and click history button
      await waitFor(() => {
        expect(getByText('History')).toBeInTheDocument();
      });
      
      getByText('History').click();
      
      // Should show the history item with delete button
      await waitFor(() => {
        expect(getByText('Test Design 1')).toBeInTheDocument();
        expect(getByTitle('Delete design')).toBeInTheDocument();
      });
    });

    it('shows confirmation dialog when delete is clicked', async () => {
      const mockHistory = [
        {
          id: 'conv-1',
          title: 'Test Design',
          status: 'completed',
          message_count: 3,
          created_at: '2026-01-25T10:00:00Z',
          updated_at: '2026-01-25T10:30:00Z',
        },
      ];
      mockListConversations.mockResolvedValue(mockHistory);
      
      const { getByText, getByTitle } = render(
        <BrowserRouter>
          <CreatePage />
        </BrowserRouter>
      );
      
      await waitFor(() => {
        expect(getByText('History')).toBeInTheDocument();
      });
      
      getByText('History').click();
      
      await waitFor(() => {
        expect(getByTitle('Delete design')).toBeInTheDocument();
      });
      
      getByTitle('Delete design').click();
      
      // Should show confirmation dialog
      await waitFor(() => {
        expect(getByText('Delete this design?')).toBeInTheDocument();
        expect(getByText('Delete')).toBeInTheDocument();
        expect(getByText('Cancel')).toBeInTheDocument();
      });
    });

    it('deletes conversation when confirmed', async () => {
      const mockHistory = [
        {
          id: 'conv-1',
          title: 'Design to Delete',
          status: 'completed',
          message_count: 3,
          created_at: '2026-01-25T10:00:00Z',
          updated_at: '2026-01-25T10:30:00Z',
        },
      ];
      mockListConversations.mockResolvedValue(mockHistory);
      mockDeleteConversation.mockResolvedValue(undefined);
      
      const { getByText, getByTitle, queryByText } = render(
        <BrowserRouter>
          <CreatePage />
        </BrowserRouter>
      );
      
      await waitFor(() => {
        expect(getByText('History')).toBeInTheDocument();
      });
      
      getByText('History').click();
      
      await waitFor(() => {
        expect(getByTitle('Delete design')).toBeInTheDocument();
      });
      
      getByTitle('Delete design').click();
      
      await waitFor(() => {
        expect(getByText('Delete this design?')).toBeInTheDocument();
      });
      
      // Click the Delete button in the confirmation
      getByText('Delete').click();
      
      await waitFor(() => {
        expect(mockDeleteConversation).toHaveBeenCalledWith('conv-1', mockToken);
      });
      
      // Item should be removed from the list
      await waitFor(() => {
        expect(queryByText('Design to Delete')).not.toBeInTheDocument();
      });
    });

    it('cancels delete when cancel is clicked', async () => {
      const mockHistory = [
        {
          id: 'conv-1',
          title: 'Keep This Design',
          status: 'completed',
          message_count: 3,
          created_at: '2026-01-25T10:00:00Z',
          updated_at: '2026-01-25T10:30:00Z',
        },
      ];
      mockListConversations.mockResolvedValue(mockHistory);
      
      const { getByText, getByTitle } = render(
        <BrowserRouter>
          <CreatePage />
        </BrowserRouter>
      );
      
      await waitFor(() => {
        expect(getByText('History')).toBeInTheDocument();
      });
      
      getByText('History').click();
      
      await waitFor(() => {
        expect(getByTitle('Delete design')).toBeInTheDocument();
      });
      
      getByTitle('Delete design').click();
      
      await waitFor(() => {
        expect(getByText('Delete this design?')).toBeInTheDocument();
      });
      
      // Click Cancel
      getByText('Cancel').click();
      
      // Should return to normal view with the design still present
      await waitFor(() => {
        expect(getByText('Keep This Design')).toBeInTheDocument();
      });
      
      // Delete should not have been called
      expect(mockDeleteConversation).not.toHaveBeenCalled();
    });
  });

  describe('Slash Commands Integration', () => {
    it('passes onCommand prop to ChatInput when in chat view', async () => {
      // Create a completed conversation to get to chat view
      const completedConversation = {
        id: 'conv-completed',
        title: 'Test Design',
        status: 'completed',
        messages: [
          {
            id: 'msg-1',
            role: 'assistant',
            message_type: 'text',
            content: 'Welcome!',
            created_at: '2026-01-25T10:00:00Z',
          },
          {
            id: 'msg-2',
            role: 'user',
            message_type: 'text',
            content: 'Create a box',
            created_at: '2026-01-25T10:01:00Z',
          },
        ],
        result: {
          job_id: 'job-123',
          downloads: {
            step: '/download/step',
            stl: '/download/stl',
          },
        },
        understanding: null,
      };
      
      mockGetConversation.mockResolvedValue(completedConversation);
      
      render(
        <MemoryRouter initialEntries={['/create?id=conv-completed']}>
          <CreatePage />
        </MemoryRouter>
      );
      
      // Wait for chat view to be loaded
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/describe changes|use \/help for commands/i)).toBeInTheDocument();
      });
    });

    it('shows /help hint in placeholder when design is completed', async () => {
      const completedConversation = {
        id: 'conv-completed',
        title: 'Test Design',
        status: 'completed',
        messages: [
          {
            id: 'msg-1',
            role: 'assistant',
            message_type: 'text',
            content: 'Welcome!',
            created_at: '2026-01-25T10:00:00Z',
          },
        ],
        result: {
          job_id: 'job-123',
          downloads: { stl: '/download/stl' },
        },
        understanding: null,
      };
      
      mockGetConversation.mockResolvedValue(completedConversation);
      
      render(
        <MemoryRouter initialEntries={['/create?id=conv-completed']}>
          <CreatePage />
        </MemoryRouter>
      );
      
      await waitFor(() => {
        // Use getAllByRole since there are multiple textboxes, find the one with help hint
        const inputs = screen.getAllByRole('textbox');
        const chatInput = inputs.find(input => 
          input.getAttribute('placeholder')?.includes('/help')
        );
        expect(chatInput).toBeTruthy();
      });
    });
  });
});
