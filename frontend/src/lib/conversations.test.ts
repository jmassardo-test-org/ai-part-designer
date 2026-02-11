/**
 * Tests for conversations API client.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  createConversation,
  listConversations,
  getConversation,
  sendMessage,
  triggerGeneration,
  deleteConversation,
  type Conversation,
  type ConversationListItem,
  type SendMessageResult,
} from './conversations';

// Mock fetch globally
global.fetch = vi.fn();

describe('Conversations API Client', () => {
  const mockToken = 'test-auth-token-123';
  const mockConvId = 'conv-uuid-456';
  const mockDesignId = 'design-uuid-789';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createConversation', () => {
    it('should create conversation without design context', async () => {
      const mockResponse: Conversation = {
        id: mockConvId,
        status: 'active',
        messages: [],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await createConversation(mockToken);

      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/conversations',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: `Bearer ${mockToken}`,
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should create conversation with design context', async () => {
      const mockResponse: Conversation = {
        id: mockConvId,
        status: 'active',
        messages: [],
        understanding: {
          user_messages: [],
          model_context: {
            design_id: mockDesignId,
            name: 'Test Model',
            dimensions: {},
            features: [],
            parameters: {},
            metadata: {},
          },
          dimensions: {},
          features: [],
          state: 'classifying',
          completeness_score: 0,
        },
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await createConversation(mockToken, mockDesignId);

      const calls = (global.fetch as ReturnType<typeof vi.fn>).mock.calls;
      const callBody = JSON.parse(calls[0][1].body);
      expect(callBody).toEqual({ design_id: mockDesignId });
      expect(result.understanding?.model_context?.design_id).toBe(mockDesignId);
    });

    it('should throw error on failed request', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: async () => ({ detail: 'Design not found' }),
      });

      await expect(createConversation(mockToken, mockDesignId)).rejects.toThrow(
        'Design not found'
      );
    });
  });

  describe('listConversations', () => {
    it('should fetch all conversations', async () => {
      const mockList: ConversationListItem[] = [
        {
          id: 'conv-1',
          status: 'active',
          title: 'Test 1',
          message_count: 5,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      ];

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockList,
      });

      const result = await listConversations(mockToken);

      expect(result).toEqual(mockList);
    });
  });

  describe('getConversation', () => {
    it('should fetch conversation by ID', async () => {
      const mockConv: Conversation = {
        id: mockConvId,
        status: 'completed',
        messages: [
          {
            id: 'msg-1',
            role: 'user',
            message_type: 'text',
            content: 'Create a box',
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockConv,
      });

      const result = await getConversation(mockConvId, mockToken);

      expect(result).toEqual(mockConv);
      expect(result.messages).toHaveLength(1);
    });
  });

  describe('sendMessage', () => {
    it('should send message and receive response', async () => {
      const mockResult: SendMessageResult = {
        user_message: {
          id: 'msg-user',
          role: 'user',
          message_type: 'text',
          content: 'Make it 100mm wide',
          created_at: '2024-01-01T00:00:00Z',
        },
        assistant_message: {
          id: 'msg-asst',
          role: 'assistant',
          message_type: 'clarification',
          content: 'What should the height be?',
          created_at: '2024-01-01T00:00:01Z',
        },
        additional_messages: [],
        conversation_status: 'clarifying',
        ready_to_generate: false,
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      });

      const result = await sendMessage(mockConvId, 'Make it 100mm wide', mockToken);

      expect(result.user_message.content).toBe('Make it 100mm wide');
      expect(result.conversation_status).toBe('clarifying');
    });
  });

  describe('triggerGeneration', () => {
    it('should trigger CAD generation', async () => {
      const mockResult: SendMessageResult = {
        user_message: {
          id: 'msg-1',
          role: 'system',
          message_type: 'text',
          content: 'Generating...',
          created_at: '2024-01-01T00:00:00Z',
        },
        assistant_message: {
          id: 'msg-2',
          role: 'assistant',
          message_type: 'result',
          content: 'Generation complete',
          created_at: '2024-01-01T00:00:01Z',
        },
        additional_messages: [],
        conversation_status: 'completed',
        ready_to_generate: true,
      };

      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      });

      const result = await triggerGeneration(mockConvId, mockToken);

      expect(result.conversation_status).toBe('completed');
    });
  });

  describe('deleteConversation', () => {
    it('should delete conversation', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: true,
      });

      await deleteConversation(mockConvId, mockToken);

      expect(global.fetch).toHaveBeenCalledWith(
        `/api/v1/conversations/${mockConvId}`,
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('should throw on delete failure', async () => {
      (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      await expect(deleteConversation(mockConvId, mockToken)).rejects.toThrow();
    });
  });
});
