/**
 * Unified Create Page with animated transition from prompts to chat.
 * 
 * Shows example prompts initially, then transforms into chat interface
 * when the user submits their first message.
 * 
 * Persists conversation ID in URL for refresh support.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { 
  Sparkles, 
  Lightbulb, 
  ArrowRight,
  Loader2,
  Package,
  Wrench,
  Box,
  Cpu,
  Settings2,
  History,
  MessageSquare,
} from 'lucide-react';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { ChatInput } from '@/components/chat/ChatInput';
import { UnderstandingSidebar } from '@/components/chat/UnderstandingSidebar';
import { ModelViewer } from '@/components/viewer';
import { useAuth } from '@/contexts/AuthContext';
import {
  createConversation,
  getConversation,
  listConversations,
  sendMessage,
  type Conversation,
  type ConversationListItem,
  type Message,
  type PartUnderstanding,
} from '@/lib/conversations';
import { downloadGeneratedFile, getPreviewData } from '@/lib/generate';

// Example prompts organized by category
const EXAMPLE_CATEGORIES = [
  {
    id: 'basic',
    name: 'Basic Shapes',
    icon: Box,
    prompts: [
      "Create a box 100mm long, 50mm wide, and 30mm tall with 3mm fillets on all edges",
      "Make a cylinder 2 inches in diameter and 4 inches tall with a 10mm center hole",
      "Design a 60mm diameter sphere",
    ],
  },
  {
    id: 'mechanical',
    name: 'Mechanical Parts',
    icon: Wrench,
    prompts: [
      "Build a mounting bracket: 80x60x3mm plate with four 5mm holes near the corners",
      "Create an L-bracket with 100mm legs, 3mm thick and 25mm wide",
      "Design a shaft collar 20mm bore, 40mm outer diameter, 15mm wide with M4 set screw",
    ],
  },
  {
    id: 'enclosures',
    name: 'Enclosures',
    icon: Package,
    prompts: [
      "Create a 2-part enclosure 120x80x50mm with lid and M3 mounting screws",
      "Design a Raspberry Pi 4 case with ventilation slots and GPIO access",
      "Make a waterproof junction box 100x100x60mm with cable glands",
    ],
  },
  {
    id: 'electronics',
    name: 'Electronics',
    icon: Cpu,
    prompts: [
      "Create a DIN rail mount for an Arduino Uno",
      "Design a panel mount for a 16x2 LCD display",
      "Make a battery holder for 4x AA batteries in 2x2 configuration",
    ],
  },
];

export function CreatePage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // View state - 'prompts' or 'chat'
  const [view, setView] = useState<'prompts' | 'chat'>('prompts');
  
  // Initial prompt before conversation starts
  const [initialPrompt, setInitialPrompt] = useState('');
  
  // Conversation state
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationListItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Understanding from latest response
  const [understanding, setUnderstanding] = useState<PartUnderstanding | null>(null);
  
  // Preview
  const [previewData, setPreviewData] = useState<ArrayBuffer | null>(null);
  
  // Scroll ref
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Load conversation history on mount
  useEffect(() => {
    if (token) {
      listConversations(token)
        .then(setConversationHistory)
        .catch(() => {});
    }
  }, [token]);
  
  // Load conversation from URL on mount
  useEffect(() => {
    const conversationId = searchParams.get('id');
    if (conversationId && token && !conversation) {
      setLoading(true);
      getConversation(conversationId, token)
        .then((convo) => {
          setConversation(convo);
          setView('chat');
          if (convo.understanding) {
            setUnderstanding(convo.understanding);
          }
          // Load preview if completed
          if (convo.result?.downloads?.stl && convo.result?.job_id) {
            getPreviewData(convo.result.job_id, token)
              .then(setPreviewData)
              .catch(() => {});
          }
        })
        .catch((err) => {
          setError(err.message);
          // Clear invalid ID from URL
          setSearchParams({});
        })
        .finally(() => setLoading(false));
    }
  }, [searchParams, token, conversation, setSearchParams]);
  
  // Auto-scroll when messages change - only scroll within container
  useEffect(() => {
    if (view === 'chat' && messagesEndRef.current) {
      // Use scrollTo on parent to avoid page scroll
      const container = messagesEndRef.current.parentElement?.parentElement;
      if (container) {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, [conversation?.messages, view]);
  
  // Start conversation with initial message
  const startConversation = useCallback(async (prompt: string) => {
    if (!token) {
      setError('Please log in to create parts');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Create conversation
      const convo = await createConversation(token);
      
      // Save to URL for persistence
      setSearchParams({ id: convo.id });
      
      // Create optimistic user message to show immediately
      const tempUserMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        message_type: 'text',
        content: prompt,
        created_at: new Date().toISOString(),
      };
      
      // Show chat view immediately with welcome + user message
      setConversation({
        ...convo,
        messages: [
          ...convo.messages,  // Welcome message
          tempUserMsg,
        ],
      });
      setView('chat');
      
      // Send initial message
      const response = await sendMessage(convo.id, prompt, token);
      
      // Update with real messages from server
      setConversation({
        ...convo,
        status: response.conversation_status as Conversation['status'],
        messages: [
          ...convo.messages,  // Welcome message
          response.user_message,
          response.assistant_message,
        ],
      });
      
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
      
      // Refresh history
      listConversations(token).then(setConversationHistory).catch(() => {});
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start conversation');
    } finally {
      setLoading(false);
    }
  }, [token, setSearchParams]);
  
  // Load a conversation from history
  const loadFromHistory = useCallback(async (id: string) => {
    if (!token) return;
    
    setLoading(true);
    setShowHistory(false);
    
    try {
      const convo = await getConversation(id, token);
      setConversation(convo);
      setSearchParams({ id: convo.id });
      setView('chat');
      
      if (convo.understanding) {
        setUnderstanding(convo.understanding);
      }
      
      if (convo.result?.downloads?.stl && convo.result?.job_id) {
        getPreviewData(convo.result.job_id, token)
          .then(setPreviewData)
          .catch(() => {});
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation');
    } finally {
      setLoading(false);
    }
  }, [token, setSearchParams]);
  
  // Handle initial prompt submit
  const handleInitialSubmit = useCallback(() => {
    if (initialPrompt.trim()) {
      startConversation(initialPrompt.trim());
    }
  }, [initialPrompt, startConversation]);
  
  // Use example prompt
  const handleExampleClick = useCallback((prompt: string) => {
    startConversation(prompt);
  }, [startConversation]);
  
  // Handle sending message in chat
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
      
      setConversation(prev => prev ? {
        ...prev,
        status: response.conversation_status as Conversation['status'],
        messages: [
          ...prev.messages.filter(m => m.id !== tempUserMsg.id),
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
      setError(err instanceof Error ? err.message : 'Failed to send message');
      setConversation(prev => prev ? {
        ...prev,
        messages: prev.messages.filter(m => m.id !== tempUserMsg.id),
      } : null);
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
  
  const isCompleted = conversation?.status === 'completed';

  return (
    <div className="-mx-4 sm:-mx-6 lg:-mx-8 -mt-8 -mb-8 relative h-[calc(100vh-64px)] overflow-hidden bg-gray-50">
      {/* History Button - Fixed position */}
      {conversationHistory.length > 0 && (
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="absolute top-3 right-3 z-20 flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 shadow-sm"
        >
          <History className="h-4 w-4" />
          History
        </button>
      )}
      
      {/* History Panel */}
      {showHistory && (
        <div className="absolute top-12 right-3 z-20 w-80 max-h-96 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-100 bg-gray-50">
            <h3 className="text-sm font-medium text-gray-900">Recent Designs</h3>
          </div>
          <div className="overflow-y-auto max-h-80">
            {conversationHistory.map((convo) => (
              <button
                key={convo.id}
                onClick={() => loadFromHistory(convo.id)}
                className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-0"
              >
                <div className="flex items-start gap-2">
                  <MessageSquare className="h-4 w-4 text-gray-400 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-900 truncate">
                      {convo.title || 'Untitled Design'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(convo.created_at).toLocaleDateString()} · {convo.message_count} messages
                    </p>
                  </div>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    convo.status === 'completed' ? 'bg-green-100 text-green-700' :
                    convo.status === 'failed' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-600'
                  }`}>
                    {convo.status}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
      
      {/* Prompts View */}
      <div 
        className={`absolute inset-0 transition-all duration-500 ease-out overflow-y-auto bg-gray-50 ${
          view === 'prompts' 
            ? 'opacity-100 translate-y-0' 
            : 'opacity-0 translate-y-full pointer-events-none'
        }`}
      >
        <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center justify-center h-12 w-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl mb-3">
              <Sparkles className="h-6 w-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900 mb-1">
              What would you like to create?
            </h1>
            <p className="text-gray-600 text-sm max-w-xl mx-auto">
              Describe the part you want in natural language, or choose from an example below.
              Our AI will help you refine your design through conversation.
            </p>
          </div>
          
          {/* Main Input */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-4 mb-4">
            <div className="flex gap-3">
              <textarea
                value={initialPrompt}
                onChange={(e) => setInitialPrompt(e.target.value)}
                placeholder="Describe your part... e.g., 'Create a mounting bracket 80mm wide with 4 screw holes'"
                rows={2}
                className="flex-1 px-3 py-2 bg-gray-50 text-gray-900 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none placeholder:text-gray-400"
                disabled={loading}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleInitialSubmit();
                  }
                }}
              />
              <button
                onClick={handleInitialSubmit}
                disabled={loading || !initialPrompt.trim()}
                className="self-end flex items-center gap-2 px-4 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    Start
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
            
            {error && (
              <p className="mt-2 text-sm text-red-600">{error}</p>
            )}
          </div>
          
          {/* Example Categories */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              <h2 className="font-medium text-sm text-gray-900">Or try an example</h2>
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
              {EXAMPLE_CATEGORIES.map((category) => (
                <div 
                  key={category.id}
                  className="bg-white rounded-lg border border-gray-200 overflow-hidden"
                >
                  <div className="flex items-center gap-1.5 px-3 py-2 bg-gray-50 border-b border-gray-200">
                    <category.icon className="h-3.5 w-3.5 text-gray-500" />
                    <span className="font-medium text-gray-700 text-xs">{category.name}</span>
                  </div>
                  <div className="p-1.5 space-y-0.5">
                    {category.prompts.map((prompt, index) => (
                      <button
                        key={index}
                        onClick={() => handleExampleClick(prompt)}
                        disabled={loading}
                        className="w-full text-left p-2 text-xs text-gray-700 rounded hover:bg-gray-50 transition-colors disabled:opacity-50 group"
                      >
                        <div className="flex items-start gap-1.5">
                          <span className="flex-1 line-clamp-2">{prompt}</span>
                          <ArrowRight className="h-3 w-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-0.5" />
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Chat View */}
      <div 
        className={`absolute inset-0 transition-all duration-500 ease-out ${
          view === 'chat' 
            ? 'opacity-100 translate-y-0' 
            : 'opacity-0 -translate-y-full pointer-events-none'
        }`}
      >
        <div className="flex h-full bg-white">
          {/* Left Column: Chat */}
          <div className="w-1/2 flex flex-col min-w-0 border-r border-gray-200 bg-white">
            {/* Chat Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
              <h2 className="text-sm font-medium text-gray-700 truncate">
                {conversation?.title || 'New Design'}
              </h2>
              <button
                onClick={() => {
                  setSearchParams({});
                  setConversation(null);
                  setUnderstanding(null);
                  setPreviewData(null);
                  setView('prompts');
                  setInitialPrompt('');
                }}
                className="text-xs text-primary-600 hover:text-primary-700 font-medium"
              >
                + New Design
              </button>
            </div>
            
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4">
              <div className="space-y-3">
                {conversation?.messages.map((message) => (
                  <ChatMessage
                    key={message.id}
                    message={message}
                    onOptionSelect={handleOptionSelect}
                  />
                ))}
                
                {/* Loading indicator while processing */}
                {loading && (
                  <div className="flex gap-2.5 p-3 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-gray-200">
                      <Loader2 className="w-4 h-4 text-primary-600 animate-spin" />
                    </div>
                    <div className="flex-1">
                      <span className="text-xs font-medium text-gray-900">AI Assistant</span>
                      <p className="text-sm text-gray-500 mt-0.5">
                        {understanding?.state === 'ready_to_plan' ? 'Generating your part...' : 'Thinking...'}
                      </p>
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            </div>
            
            {/* Error */}
            {error && view === 'chat' && (
              <div className="px-4 py-2 bg-red-50 border-t border-red-200">
                <p className="text-sm text-red-600 text-center">{error}</p>
              </div>
            )}
            
            {/* Input */}
            <div className="border-t border-gray-100 bg-white px-4 py-3">
              <div>
                <ChatInput
                  onSend={handleSendMessage}
                  disabled={loading}
                  loading={loading}
                  placeholder={
                    loading
                      ? "Generating your part..."
                      : isCompleted 
                        ? "Describe changes you'd like to make..."
                        : "Continue describing your part..."
                  }
                />
              </div>
            </div>
          </div>
          
          {/* Right Column: Preview + Details */}
          <div className="w-1/2 flex flex-col bg-gray-50">
            {/* 3D Preview Area */}
            <div className="flex-1 min-h-0 bg-gray-100 relative">
              {previewData ? (
                <ModelViewer stlData={previewData} />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center text-gray-400">
                    <Box className="h-16 w-16 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">3D preview will appear here</p>
                    <p className="text-xs mt-1">once generation is complete</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Model Details */}
            <div className="border-t border-gray-200 overflow-y-auto bg-white max-h-48">
              {understanding ? (
                <UnderstandingSidebar understanding={understanding} />
              ) : (
                <div className="p-4 text-center text-gray-500">
                  <Settings2 className="h-6 w-6 mx-auto mb-1 text-gray-300" />
                  <p className="text-xs">Analyzing...</p>
                </div>
              )}
              
              {/* Download buttons when completed */}
              {isCompleted && conversation?.result?.downloads && (
                <div className="p-3 border-t border-gray-200 bg-gray-50">
                  <p className="text-xs font-medium text-gray-700 mb-2">Download</p>
                  <div className="flex gap-2">
                    {conversation.result.downloads.step && (
                      <button
                        onClick={() => handleDownload('step')}
                        className="flex-1 px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                      >
                        Download STEP
                      </button>
                    )}
                    {conversation.result.downloads.stl && (
                      <button
                        onClick={() => handleDownload('stl')}
                        className="flex-1 px-3 py-2 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                      >
                        Download STL
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
