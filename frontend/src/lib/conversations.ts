/**
 * Conversation API client for AI-powered CAD generation.
 * Handles chat-based iterative design conversations.
 */

const API_BASE = '/api/v1/conversations';

// Type definitions matching backend schemas
export interface Message {
  id: string;
  role: string;
  message_type: string;
  content: string;
  extra_data?: Record<string, unknown>;
  created_at: string;
}

export interface PartUnderstanding {
  [key: string]: any;
  user_messages?: string[];
  model_context?: ModelContextData;
  classification?: {
    category: string;
    subcategory?: string;
    confidence: number;
  };
  missing_critical?: string[];
  dimensions: Record<string, unknown>;
  features: Array<Record<string, unknown>>;
  state: string;
  completeness_score: number;
}

export interface ModelContextData {
  design_id: string;
  name: string;
  description?: string;
  dimensions: Record<string, number | string>;
  features: Array<Record<string, unknown>>;
  parameters: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  status: string;
  title?: string;
  messages: Message[];
  understanding?: PartUnderstanding;
  result?: any;
  created_at: string;
  updated_at: string;
}

export interface ConversationListItem {
  id: string;
  status: string;
  title?: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface SendMessageResult {
  user_message: Message;
  assistant_message: Message;
  additional_messages: Message[];
  conversation_status: string;
  understanding?: PartUnderstanding;
  ready_to_generate: boolean;
  result?: any;
}

/**
 * Initialize a new conversation session.
 * Optionally attach an existing design for Q&A context.
 */
export async function createConversation(
  authToken: string,
  designIdForContext?: string
): Promise<Conversation> {
  const requestBody = designIdForContext ? { design_id: designIdForContext } : {};
  
  const resp = await fetch(API_BASE, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(errorData.detail || `Failed to start conversation: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Retrieve all conversations for the authenticated user.
 */
export async function listConversations(authToken: string): Promise<ConversationListItem[]> {
  const resp = await fetch(API_BASE, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    throw new Error(`Failed to fetch conversations: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Fetch a specific conversation with full message history.
 */
export async function getConversation(
  conversationId: string,
  authToken: string
): Promise<Conversation> {
  const resp = await fetch(`${API_BASE}/${conversationId}`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({ detail: 'Not found' }));
    throw new Error(errorData.detail || `Conversation not found: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Send a message in a conversation and receive AI response.
 * The AI processes through iterative reasoning and may ask clarifications.
 */
export async function sendMessage(
  conversationId: string,
  messageContent: string,
  authToken: string
): Promise<SendMessageResult> {
  const resp = await fetch(`${API_BASE}/${conversationId}/messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ content: messageContent }),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({ detail: 'Failed to send' }));
    throw new Error(errorData.detail || `Failed to send message: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Trigger CAD generation when conversation is ready.
 * Used for explicit generation requests after clarifications.
 */
export async function triggerGeneration(
  conversationId: string,
  authToken: string
): Promise<SendMessageResult> {
  const resp = await fetch(`${API_BASE}/${conversationId}/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({}),
  });

  if (!resp.ok) {
    const errorData = await resp.json().catch(() => ({ detail: 'Generation failed' }));
    throw new Error(errorData.detail || `Generation failed: ${resp.status}`);
  }

  return resp.json();
}

/**
 * Remove a conversation and all its messages.
 */
export async function deleteConversation(
  conversationId: string,
  authToken: string
): Promise<void> {
  const resp = await fetch(`${API_BASE}/${conversationId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${authToken}`,
    },
  });

  if (!resp.ok) {
    throw new Error(`Failed to delete conversation: ${resp.status}`);
  }
}
