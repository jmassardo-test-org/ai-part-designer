/**
 * Main chat panel component for conversational CAD generation.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { Plus, History, X, ChevronLeft, ChevronRight } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { UnderstandingSidebar } from './UnderstandingSidebar';
import { ModelViewer } from '@/components/viewer';
import { useAuth } from '@/contexts/AuthContext';
import {
  createConversation,
  getConversation,
  sendMessage,
  triggerGeneration,
  listConversations,
  type Conversation,
  type Message,
  type PartUnderstanding,
  type ConversationListItem,
} from '@/lib/conversations';
import { downloadGeneratedFile, getPreviewData } from '@/lib/generate';

interface ChatPanelProps {
  className?: string;
}

export function ChatPanel({ className = '' }: ChatPanelProps) {
  const { token } = useAuth();
  
  // Conversation state
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // UI state
  const [showHistory, setShowHistory] = useState(false);
  const [showSidebar, setShowSidebar] = useState(true);
  const [previewData, setPreviewData] = useState<ArrayBuffer | null>(null);
  
  // Understanding from latest response
  const [understanding, setUnderstanding] = useState<PartUnderstanding | null>(null);
  
  // Scroll to bottom ref
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages]);
  
  // Load conversations on mount
  useEffect(() => {
    if (token) {
      loadConversations();
    }
  }, [token]);
  
  const loadConversations = useCallback(async () => {
    if (!token) return;
    
    try {
      const convos = await listConversations(token);
      setConversations(convos);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    }
  }, [token]);
  
  const handleNewConversation = useCallback(async () => {
    if (!token) {
      setError('Please log in to start a conversation');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const convo = await createConversation(token);
      setConversation(convo);
      setUnderstanding(null);
      setPreviewData(null);
      loadConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation');
    } finally {
      setLoading(false);
    }
  }, [token, loadConversations]);
  
  const handleLoadConversation = useCallback(async (id: string) => {
    if (!token) return;
    
    setLoading(true);
    setShowHistory(false);
    
    try {
      const convo = await getConversation(id, token);
      setConversation(convo);
      setUnderstanding(convo.understanding || null);
      
      // Load preview if there's a result
      if (convo.result?.downloads?.stl && convo.result?.job_id) {
        try {
          const preview = await getPreviewData(convo.result.job_id, token);
          setPreviewData(preview);
        } catch {
          // Non-fatal
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setLoading(false);
    }
  }, [token]);
  
  const handleSendMessage = useCallback(async (content: string) => {
    if (!token || !conversation) return;
    
    // Optimistically add user message
    const tempUserMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      message_type: 'text',
      content,
      created_at: new Date().toISOString(),
    };
    
    setConversation(prev => prev ? {
      ...prev,
      messages: [...prev.messages, tempUserMsg],
    } : null);
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await sendMessage(conversation.id, content, token);
      
      // Update conversation with new messages
      setConversation(prev => prev ? {
        ...prev,
        status: response.conversation_status as Conversation['status'],
        messages: [
          ...prev.messages.filter(m => m.id !== tempUserMsg.id),
          response.user_message,
          response.assistant_message,
        ],
      } : null);
      
      // Update understanding
      if (response.understanding) {
        setUnderstanding(response.understanding);
      }
      
      // Load preview if generation completed
      if (response.result?.downloads?.stl && response.result?.job_id) {
        try {
          const preview = await getPreviewData(response.result.job_id, token);
          setPreviewData(preview);
        } catch {
          // Non-fatal
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      // Remove optimistic message
      setConversation(prev => prev ? {
        ...prev,
        messages: prev.messages.filter(m => m.id !== tempUserMsg.id),
      } : null);
    } finally {
      setLoading(false);
    }
  }, [token, conversation]);
  
  const handleGenerate = useCallback(async () => {
    if (!token || !conversation) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await triggerGeneration(conversation.id, token);
      
      setConversation(prev => prev ? {
        ...prev,
        status: response.conversation_status as Conversation['status'],
        messages: [
          ...prev.messages,
          response.user_message,
          response.assistant_message,
        ],
      } : null);
      
      if (response.understanding) {
        setUnderstanding(response.understanding);
      }
      
      if (response.result?.downloads?.stl && response.result?.job_id) {
        try {
          const preview = await getPreviewData(response.result.job_id, token);
          setPreviewData(preview);
        } catch {
          // Non-fatal
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate');
    } finally {
      setLoading(false);
    }
  }, [token, conversation]);
  
  const handleOptionSelect = useCallback((option: string) => {
    handleSendMessage(option);
  }, [handleSendMessage]);
  
  const handleDownload = useCallback(async (format: 'step' | 'stl') => {
    if (!token || !conversation?.result?.job_id) return;
    
    try {
      const blob = await downloadGeneratedFile(conversation.result.job_id, format, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `generated-part.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(`Failed to download ${format.toUpperCase()} file`);
    }
  }, [token, conversation]);
  
  const canGenerate = understanding && understanding.completeness_score >= 0.3;
  const isCompleted = conversation?.status === 'completed';

  return (
    <div className={`flex h-full ${className}`}>
      {/* History Sidebar */}
      {showHistory && (
        <div className="w-64 border-r border-gray-200 bg-gray-50 flex flex-col">
          <div className="p-3 border-b border-gray-200 flex items-center justify-between">
            <h3 className="font-medium text-gray-900">Conversations</h3>
            <button
              onClick={() => setShowHistory(false)}
              className="p-1 hover:bg-gray-200 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            {conversations.length === 0 ? (
              <p className="p-4 text-sm text-gray-500">No conversations yet</p>
            ) : (
              <ul className="divide-y divide-gray-200">
                {conversations.map((convo) => (
                  <li key={convo.id}>
                    <button
                      onClick={() => handleLoadConversation(convo.id)}
                      className={`w-full p-3 text-left hover:bg-gray-100 ${
                        conversation?.id === convo.id ? 'bg-blue-50' : ''
                      }`}
                    >
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {convo.title || 'Untitled'}
                      </p>
                      <p className="text-xs text-gray-500">
                        {convo.message_count} messages • {convo.status}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
      
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="p-3 border-b border-gray-200 flex items-center justify-between bg-white">
          <div className="flex items-center gap-2">
            {!showHistory && (
              <button
                onClick={() => setShowHistory(true)}
                className="p-2 hover:bg-gray-100 rounded-lg"
                title="Show history"
              >
                <History className="w-5 h-5" />
              </button>
            )}
            <button
              onClick={handleNewConversation}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
            >
              <Plus className="w-4 h-4" />
              New Chat
            </button>
          </div>
          
          <div className="flex items-center gap-2">
            {conversation && (
              <span className="text-sm text-gray-500">
                {conversation.status}
              </span>
            )}
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 hover:bg-gray-100 rounded-lg"
              title={showSidebar ? 'Hide understanding' : 'Show understanding'}
            >
              {showSidebar ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
            </button>
          </div>
        </div>
        
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!conversation ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-4">
                <Plus className="w-8 h-8 text-blue-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Start a New Design
              </h2>
              <p className="text-gray-500 max-w-md mb-4">
                Click "New Chat" to start designing a CAD part. Describe what you want,
                and I'll ask clarifying questions to make sure I understand correctly.
              </p>
              <button
                onClick={handleNewConversation}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300"
              >
                New Chat
              </button>
            </div>
          ) : (
            <>
              {conversation.messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                  onDownload={handleDownload}
                  onOptionSelect={handleOptionSelect}
                />
              ))}
              
              {loading && (
                <div className="flex items-center gap-2 text-gray-500">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              )}
              
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
        
        {/* 3D Preview (if completed) */}
        {isCompleted && previewData && (
          <div className="h-64 border-t border-gray-200">
            <ModelViewer stlData={previewData} />
          </div>
        )}
        
        {/* Input */}
        {conversation && conversation.status !== 'completed' && (
          <ChatInput
            onSend={handleSendMessage}
            onGenerate={handleGenerate}
            disabled={loading}
            loading={loading}
            showGenerateButton={!!canGenerate}
            generateDisabled={!canGenerate}
          />
        )}
      </div>
      
      {/* Understanding Sidebar */}
      {showSidebar && (
        <div className="w-72 border-l border-gray-200 bg-gray-50 overflow-y-auto">
          <div className="p-3 border-b border-gray-200">
            <h3 className="font-medium text-gray-900">Understanding</h3>
          </div>
          <UnderstandingSidebar understanding={understanding} />
        </div>
      )}
    </div>
  );
}
