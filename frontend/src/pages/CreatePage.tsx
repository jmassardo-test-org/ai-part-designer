/**
 * Unified Create Page with animated transition from prompts to chat.
 * 
 * Shows example prompts initially, then transforms into chat interface
 * when the user submits their first message.
 * 
 * Persists conversation ID in URL for refresh support.
 */

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
  GitFork,
  Save,
  Check,
  FolderOpen,
  X,
} from 'lucide-react';
import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useSearchParams, useLocation } from 'react-router-dom';
import { ChatInput } from '@/components/chat/ChatInput';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { UnderstandingSidebar } from '@/components/chat/UnderstandingSidebar';
import { HistoryPanel } from '@/components/history';
import { ModelViewer } from '@/components/viewer';
import { useAuth } from '@/contexts/AuthContext';
import { useHistoryPanel } from '@/hooks/useHistoryPanel';
import { useSlashCommands, type CommandHandlerContext } from '@/hooks/useSlashCommands';
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
import { saveDesignFromConversation, listProjects, type Project } from '@/lib/designs';
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

// Location state for incoming navigation
interface CreatePageLocationState {
  initialPrompt?: string;
  remixMode?: boolean;
  remixedFrom?: {
    id: string;
    name: string;
  };
  enclosureSpec?: Record<string, unknown>;
}

export function CreatePage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const locationState = location.state as CreatePageLocationState | null;
  
  // View state - 'prompts' or 'chat'
  const [view, setView] = useState<'prompts' | 'chat'>('prompts');
  
  // Initial prompt before conversation starts
  const [initialPrompt, setInitialPrompt] = useState('');
  
  // Remix state
  const [isRemixMode, setIsRemixMode] = useState(false);
  const [remixedFrom, setRemixedFrom] = useState<{ id: string; name: string } | null>(null);
  
  // Conversation state
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationListItem[]>([]);
  const { isOpen: showHistory, toggle: toggleHistory, close: closeHistory } = useHistoryPanel({ enableShortcut: true });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Understanding from latest response
  const [understanding, setUnderstanding] = useState<PartUnderstanding | null>(null);
  
  // Preview
  const [previewData, setPreviewData] = useState<ArrayBuffer | null>(null);
  
  // Save design state
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [saveDesignName, setSaveDesignName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [designSaved, setDesignSaved] = useState(false);
  
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

  // Handle incoming prompt from navigation (e.g., from Generate page)
  // Using a ref to track if we've already handled the initial prompt
  const hasHandledInitialPrompt = useRef(false);
  
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
      // Include additional_messages (e.g., confirmation before result)
      const additionalMsgs = response.additional_messages || [];
      setConversation({
        ...convo,
        status: response.conversation_status as Conversation['status'],
        result: response.result || convo.result,
        messages: [
          ...convo.messages,  // Welcome message
          response.user_message,
          ...additionalMsgs,
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

  // Handle incoming prompt from navigation (e.g., from Generate page)
  useEffect(() => {
    if (locationState?.initialPrompt && !hasHandledInitialPrompt.current && token && !conversation) {
      hasHandledInitialPrompt.current = true;
      
      let promptToSend = locationState.initialPrompt;
      
      // If we're in remix mode, construct a detailed prompt with the original spec context
      if (locationState.remixMode && locationState.enclosureSpec && locationState.remixedFrom) {
        // Set remix state for UI
        setIsRemixMode(true);
        setRemixedFrom(locationState.remixedFrom);
        
        const spec = locationState.enclosureSpec;
        const originalName = locationState.remixedFrom.name;
        
        // Build a description of the original enclosure
        const exterior = spec.exterior as { width?: { value: number; unit?: string }; depth?: { value: number; unit?: string }; height?: { value: number; unit?: string } } | undefined;
        const walls = spec.walls as { thickness?: { value: number; unit?: string } } | undefined;
        const lid = spec.lid as { type?: string } | undefined;
        const ventilation = spec.ventilation as { enabled?: boolean; pattern?: string } | undefined;
        
        let originalDescription = `I'm remixing an existing enclosure called "${originalName}".\n\n`;
        originalDescription += `**Original enclosure specifications:**\n`;
        
        if (exterior) {
          const w = exterior.width?.value || 0;
          const d = exterior.depth?.value || 0;
          const h = exterior.height?.value || 0;
          const unit = exterior.width?.unit || 'mm';
          originalDescription += `- Exterior dimensions: ${w}×${d}×${h} ${unit}\n`;
        }
        
        if (walls?.thickness) {
          originalDescription += `- Wall thickness: ${walls.thickness.value}${walls.thickness.unit || 'mm'}\n`;
        }
        
        if (lid?.type) {
          originalDescription += `- Lid type: ${lid.type.replace('_', ' ')}\n`;
        }
        
        if (ventilation?.enabled) {
          originalDescription += `- Ventilation: ${ventilation.pattern || 'enabled'}\n`;
        }
        
        // Add features if present
        const features = spec.features as Array<{ type: string; port_type?: string }> | undefined;
        if (features && features.length > 0) {
          originalDescription += `- Features: ${features.map(f => f.port_type || f.type).join(', ')}\n`;
        }
        
        originalDescription += `\n**Requested modification:**\n${locationState.initialPrompt}\n\n`;
        originalDescription += `Please apply this modification to the existing enclosure design, keeping all other specifications the same unless they need to change to accommodate the new feature.`;
        
        promptToSend = originalDescription;
      }
      
      setInitialPrompt(locationState.initialPrompt);
      // Auto-submit the prompt to start the conversation
      startConversation(promptToSend);
    }
  }, [locationState, token, conversation, startConversation]);
  
  // Load a conversation from history
  const loadFromHistory = useCallback(async (id: string) => {
    if (!token) return;

    setLoading(true);
    closeHistory();
    
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
  }, [token, setSearchParams, closeHistory]);
  
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
      
      // Include additional_messages (e.g., confirmation before result)
      const additionalMsgs = response.additional_messages || [];
      setConversation(prev => prev ? {
        ...prev,
        status: response.conversation_status as Conversation['status'],
        result: response.result || prev.result,
        messages: [
          ...prev.messages.filter(m => m.id !== tempUserMsg.id),
          response.user_message,
          ...additionalMsgs,
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
    } catch {
      setError(`Failed to download ${format.toUpperCase()} file`);
    }
  }, [token, conversation]);

  // Open save modal and load projects
  const handleOpenSaveModal = useCallback(async () => {
    if (!token) return;
    
    try {
      const projectList = await listProjects(token);
      setProjects(projectList);
      
      // Default name from conversation title or description
      const defaultName = conversation?.title || 
        (understanding?.classification?.category ? 
          `${understanding.classification.category} Part` : 
          'Generated Part');
      setSaveDesignName(defaultName);
      setSaveDescription('');
      setSelectedProjectId(null);
      setShowSaveModal(true);
    } catch {
      setError('Failed to load projects');
    }
  }, [token, conversation, understanding]);

  // Save design to library
  const handleSaveDesign = useCallback(async () => {
    if (!token || !conversation?.id || !saveDesignName.trim()) return;
    
    setIsSaving(true);
    setError(null);
    
    try {
      await saveDesignFromConversation(
        conversation.id,
        saveDesignName,
        {
          description: saveDescription || undefined,
          projectId: selectedProjectId || undefined,
        },
        token
      );
      
      setDesignSaved(true);
      setShowSaveModal(false);
      setSaveDesignName('');
      setSaveDescription('');
      setSelectedProjectId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save design');
    } finally {
      setIsSaving(false);
    }
  }, [token, conversation, saveDesignName, saveDescription, selectedProjectId]);
  
  const isCompleted = conversation?.status === 'completed';

  // Slash command handlers
  const handleClearChat = useCallback(() => {
    setConversation(null);
    setPreviewData(null);
    setUnderstanding(null);
    setDesignSaved(false);
    setView('prompts');
    setSearchParams({});
  }, [setSearchParams]);

  const handleExportDesign = useCallback(async (format: string) => {
    if (!token || !conversation?.result?.job_id) {
      throw new Error('No design to export');
    }
    const validFormat = format as 'step' | 'stl';
    await handleDownload(validFormat);
  }, [token, conversation, handleDownload]);

  // Slash commands context
  const commandContext: CommandHandlerContext = useMemo(() => ({
    currentDesignId: conversation?.id,
    onSaveDesign: async () => {
      await handleOpenSaveModal();
    },
    onExportDesign: handleExportDesign,
    onClearChat: handleClearChat,
    onShowMessage: (message: string, type?: 'info' | 'success' | 'error') => {
      if (type === 'error') {
        setError(message);
      }
      // For info/success, could add a toast system in the future
    },
  }), [conversation?.id, handleOpenSaveModal, handleExportDesign, handleClearChat]);

  const { executeCommand } = useSlashCommands(commandContext);

  // Handle slash command execution
  const handleCommand = useCallback(async (command: string, args: string[]) => {
    const result = await executeCommand(command, args);
    
    // Show help message as a system message
    if (result.action === 'help' && result.success) {
      // Add help as a temporary message
      const helpMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        message_type: 'text',
        content: `**Available Commands:**\n\n${result.message}`,
        created_at: new Date().toISOString(),
      };
      setConversation(prev => prev ? {
        ...prev,
        messages: [...prev.messages, helpMessage],
      } : null);
    }
    
    return result;
  }, [executeCommand]);

  // Map conversation history to HistoryPanel format (US-16005)
  const historyPreviews = useMemo(
    () =>
      conversationHistory.map((c) => ({
        id: c.id,
        title: c.title || 'Untitled Design',
        preview: `${c.message_count} messages`,
        timestamp: new Date(c.created_at),
        designCount: c.status === 'completed' ? 1 : 0,
      })),
    [conversationHistory]
  );

  const handleNewConversation = useCallback(() => {
    setConversation(null);
    setSearchParams({});
    setView('prompts');
    setUnderstanding(null);
    setPreviewData(null);
    setInitialPrompt('');
    closeHistory();
  }, [setSearchParams, closeHistory]);

  return (
    <div className="-mx-4 sm:-mx-6 lg:-mx-8 -mt-8 -mb-8 relative h-[calc(100vh-64px)] overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* History Button - Left side (US-16005) */}
      <button
        onClick={toggleHistory}
        className="absolute top-3 left-3 z-20 flex items-center gap-1.5 px-3 py-1.5 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 shadow-sm"
        aria-label="Open history panel"
      >
        <History className="h-4 w-4" />
        History
      </button>

      {/* Slide-out History Panel (US-16005) */}
      <HistoryPanel
        isOpen={showHistory}
        onClose={closeHistory}
        conversations={historyPreviews}
        activeConversationId={conversation?.id}
        onSelectConversation={loadFromHistory}
        onNewConversation={handleNewConversation}
        isLoading={false}
      />
      
      {/* Prompts View */}
      <div 
        className={`absolute inset-0 transition-all duration-500 ease-out overflow-y-auto bg-gray-50 dark:bg-gray-900 ${
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
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-1">
              What would you like to create?
            </h1>
            <p className="text-gray-600 dark:text-gray-400 text-sm max-w-xl mx-auto">
              Describe the part you want in natural language, or choose from an example below.
              Our AI will help you refine your design through conversation.
            </p>
          </div>
          
          {/* Main Input */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm p-4 mb-4">
            <div className="flex gap-3">
              <textarea
                value={initialPrompt}
                onChange={(e) => setInitialPrompt(e.target.value)}
                placeholder="Describe your part... e.g., 'Create a mounting bracket 80mm wide with 4 screw holes'"
                rows={2}
                className="flex-1 px-3 py-2 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm border border-gray-200 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent resize-none placeholder:text-gray-400 dark:placeholder:text-gray-500"
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
              <h2 className="font-medium text-sm text-gray-900 dark:text-gray-100">Or try an example</h2>
            </div>
            
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-3">
              {EXAMPLE_CATEGORIES.map((category) => (
                <div 
                  key={category.id}
                  className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden"
                >
                  <div className="flex items-center gap-1.5 px-3 py-2 bg-gray-50 dark:bg-gray-700 border-b border-gray-200 dark:border-gray-600">
                    <category.icon className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                    <span className="font-medium text-gray-700 dark:text-gray-300 text-xs">{category.name}</span>
                  </div>
                  <div className="p-1.5 space-y-0.5">
                    {category.prompts.map((prompt, index) => (
                      <button
                        key={index}
                        onClick={() => handleExampleClick(prompt)}
                        disabled={loading}
                        className="w-full text-left p-2 text-xs text-gray-700 dark:text-gray-300 rounded hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 group"
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
        <div className="flex h-full bg-white dark:bg-gray-800">
          {/* Left Column: Chat */}
          <div className="w-1/2 flex flex-col min-w-0 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            {/* Chat Header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-700">
              <h2 className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
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
                  setIsRemixMode(false);
                  setRemixedFrom(null);
                }}
                className="text-xs text-primary-600 hover:text-primary-700 font-medium"
              >
                + New Design
              </button>
            </div>
            
            {/* Remix Banner */}
            {isRemixMode && remixedFrom && (
              <div className="mx-4 mt-3 p-3 bg-gradient-to-r from-primary-50 to-purple-50 dark:from-primary-900/30 dark:to-purple-900/30 border border-primary-200 dark:border-primary-700 rounded-lg">
                <div className="flex items-center gap-2">
                  <GitFork className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                  <span className="text-sm font-medium text-primary-900 dark:text-primary-100">
                    Remixing: {remixedFrom.name}
                  </span>
                </div>
                <p className="text-xs text-primary-700 dark:text-primary-300 mt-1">
                  Your requested changes will be applied to the original design.
                </p>
              </div>
            )}
            
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
                  <div className="flex gap-2.5 p-3 bg-gray-50 dark:bg-gray-700 rounded-lg">
                    <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center bg-gray-200 dark:bg-gray-600">
                      <Loader2 className="w-4 h-4 text-primary-600 animate-spin" />
                    </div>
                    <div className="flex-1">
                      <span className="text-xs font-medium text-gray-900 dark:text-gray-100">AI Assistant</span>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
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
              <div className="px-4 py-2 bg-red-50 dark:bg-red-900/30 border-t border-red-200 dark:border-red-800">
                <p className="text-sm text-red-600 dark:text-red-400 text-center">{error}</p>
              </div>
            )}
            
            {/* Input */}
            <div className="border-t border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800 px-4 py-3">
              <div>
                <ChatInput
                  onSend={handleSendMessage}
                  onCommand={handleCommand}
                  disabled={loading}
                  loading={loading}
                  placeholder={
                    loading
                      ? "Generating your part..."
                      : isCompleted 
                        ? "Describe changes you'd like to make or use /help for commands"
                        : "Continue describing your part..."
                  }
                />
              </div>
            </div>
          </div>
          
          {/* Right Column: Preview + Details */}
          <div className="w-1/2 flex flex-col bg-gray-50 dark:bg-gray-900 overflow-hidden">
            {/* 3D Preview Area - Takes remaining space after details section */}
            <div className="flex-1 min-h-[200px] bg-gray-100 dark:bg-gray-800 relative">
              {previewData ? (
                <ModelViewer stlData={previewData} />
              ) : (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center text-gray-400 dark:text-gray-500">
                    <Box className="h-16 w-16 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">3D preview will appear here</p>
                    <p className="text-xs mt-1">once generation is complete</p>
                  </div>
                </div>
              )}
            </div>
            
            {/* Model Details - Fixed height based on content, no scroll */}
            <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
              {understanding ? (
                <UnderstandingSidebar understanding={understanding} />
              ) : (
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  <Settings2 className="h-6 w-6 mx-auto mb-1 text-gray-300 dark:text-gray-600" />
                  <p className="text-xs">Analyzing...</p>
                </div>
              )}
              
              {/* Download buttons when completed */}
              {isCompleted && conversation?.result?.downloads && (
                <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-700">
                  {/* Save button */}
                  <div className="mb-3">
                    {designSaved ? (
                      <div className="flex items-center justify-center gap-2 px-3 py-2 text-sm bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300 rounded-lg">
                        <Check className="w-4 h-4" />
                        Design Saved
                      </div>
                    ) : (
                      <button
                        onClick={handleOpenSaveModal}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700"
                      >
                        <Save className="w-4 h-4" />
                        Save to Library
                      </button>
                    )}
                  </div>
                  
                  <p className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">Download</p>
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
      
      {/* Save Design Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Save to Library</h2>
              <button
                onClick={() => setShowSaveModal(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4 space-y-4">
              {/* Name input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Design Name *
                </label>
                <input
                  type="text"
                  value={saveDesignName}
                  onChange={(e) => setSaveDesignName(e.target.value)}
                  placeholder="My Awesome Part"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
              
              {/* Description input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={saveDescription}
                  onChange={(e) => setSaveDescription(e.target.value)}
                  placeholder="Optional description..."
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
              
              {/* Project selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Save to Project
                </label>
                <div className="relative">
                  <FolderOpen className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <select
                    value={selectedProjectId || ''}
                    onChange={(e) => setSelectedProjectId(e.target.value || null)}
                    className="w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 appearance-none bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                  >
                    <option value="">My Designs (default)</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowSaveModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveDesign}
                disabled={isSaving || !saveDesignName.trim()}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Save Design
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
