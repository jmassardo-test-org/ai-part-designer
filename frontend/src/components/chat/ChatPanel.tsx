/**
 * Main chat panel component for conversational CAD generation.
 */

import { Plus, History, X, ChevronLeft, ChevronRight, Save, Check, FolderOpen } from 'lucide-react';
import { useState, useCallback, useEffect, useRef } from 'react';
import { ModelViewer } from '@/components/viewer';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { useSlashCommands, CommandHandlerContext, CommandResult } from '@/hooks/useSlashCommands';
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
import { saveDesignFromJob, listProjects, type Project } from '@/lib/designs';
import { downloadGeneratedFile, getPreviewData } from '@/lib/generate';
import { ChatInput } from './ChatInput';
import { ChatMessage } from './ChatMessage';
import { UnderstandingSidebar } from './UnderstandingSidebar';

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
  
  // Save design state
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [projects, setProjects] = useState<Project[]>([]);
  const [saveDesignName, setSaveDesignName] = useState('');
  const [saveDescription, setSaveDescription] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [designSaved, setDesignSaved] = useState(false);
  
  // Understanding from latest response
  const [understanding, setUnderstanding] = useState<PartUnderstanding | null>(null);
  
  // Toast for notifications
  const { toast } = useToast();
  
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      
      // Update conversation with new messages and result
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
      
      // Include additional_messages (e.g., confirmation before result)
      const additionalMsgs = response.additional_messages || [];
      setConversation(prev => prev ? {
        ...prev,
        status: response.conversation_status as Conversation['status'],
        result: response.result || prev.result,
        messages: [
          ...prev.messages,
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
    if (!token || !conversation?.result?.job_id || !saveDesignName.trim()) return;
    
    setIsSaving(true);
    setError(null);
    
    try {
      await saveDesignFromJob(
        conversation.result.job_id,
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
  
  // Slash command handler context
  const commandContext: CommandHandlerContext = {
    currentDesignId: conversation?.result?.job_id,
    onSaveDesign: async (name?: string) => {
      if (name) {
        setSaveDesignName(name);
      }
      await handleOpenSaveModal();
    },
    onExportDesign: async (format: string) => {
      if (format === 'stl' || format === 'step') {
        await handleDownload(format);
      }
    },
    onClearChat: () => {
      setConversation(null);
      setUnderstanding(null);
      setPreviewData(null);
      setDesignSaved(false);
    },
  };
  
  const { executeCommand, getCommands } = useSlashCommands(commandContext);
  
  // Handle slash command execution
  const handleCommand = useCallback(async (command: string, args: string[]): Promise<CommandResult> => {
    const result = await executeCommand(command, args);
    
    // Show toast notification based on result
    if (result.success) {
      // For help command, show a special message
      if (result.action === 'help') {
        const commands = getCommands();
        const helpMessage = commands.map(c => `**${c.command}** - ${c.description}`).join('\n');
        toast({
          title: 'Available Commands',
          description: helpMessage.slice(0, 200) + (helpMessage.length > 200 ? '...' : ''),
        });
      } else {
        toast({
          title: 'Success',
          description: result.message,
        });
      }
    } else {
      toast({
        title: 'Error',
        description: result.message,
        variant: 'destructive',
      });
    }
    
    return result;
  }, [executeCommand, getCommands, toast]);
  
  const canGenerate = understanding && understanding.completeness_score >= 0.3;
  const isCompleted = conversation?.status === 'completed';

  return (
    <div className={`flex h-full ${className}`}>
      {/* History Sidebar */}
      {showHistory && (
        <div className="w-64 border-r border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex flex-col">
          <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <h3 className="font-medium text-gray-900 dark:text-gray-100">Conversations</h3>
            <button
              onClick={() => setShowHistory(false)}
              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            {conversations.length === 0 ? (
              <p className="p-4 text-sm text-gray-500 dark:text-gray-400">No conversations yet</p>
            ) : (
              <ul className="divide-y divide-gray-200 dark:divide-gray-700">
                {conversations.map((convo) => (
                  <li key={convo.id}>
                    <button
                      onClick={() => handleLoadConversation(convo.id)}
                      className={`w-full p-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 ${
                        conversation?.id === convo.id ? 'bg-blue-50 dark:bg-blue-900/30' : ''
                      }`}
                    >
                      <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                        {convo.title || 'Untitled'}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
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
        <div className="p-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between bg-white dark:bg-gray-800">
          <div className="flex items-center gap-2">
            {!showHistory && (
              <button
                onClick={() => setShowHistory(true)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
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
              <span className="text-sm text-gray-500 dark:text-gray-400">
                {conversation.status}
              </span>
            )}
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
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
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
                Start a New Design
              </h2>
              <p className="text-gray-500 dark:text-gray-400 max-w-md mb-4">
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
                <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm">
                  {error}
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
        
        {/* 3D Preview and Actions (if completed) */}
        {isCompleted && previewData && (
          <div className="border-t border-gray-200 dark:border-gray-700">
            <div className="h-64">
              <ModelViewer stlData={previewData} />
            </div>
            <div className="p-3 border-t border-gray-200 dark:border-gray-700 flex items-center justify-center gap-3 bg-white dark:bg-gray-800">
              {designSaved ? (
                <div className="flex items-center gap-2 text-green-600">
                  <Check className="w-5 h-5" />
                  <span className="text-sm font-medium">Saved to Library</span>
                </div>
              ) : (
                <button
                  onClick={handleOpenSaveModal}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Save className="w-4 h-4" />
                  Save to Library
                </button>
              )}
              <button
                onClick={() => handleDownload('step')}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Download STEP
              </button>
              <button
                onClick={() => handleDownload('stl')}
                className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                Download STL
              </button>
            </div>
          </div>
        )}
        
        {/* Input */}
        {conversation && conversation.status !== 'completed' && (
          <ChatInput
            onSend={handleSendMessage}
            onGenerate={handleGenerate}
            onCommand={handleCommand}
            disabled={loading}
            loading={loading}
            showGenerateButton={!!canGenerate}
            generateDisabled={!canGenerate}
          />
        )}
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
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
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
      
      {/* Understanding Sidebar */}
      {showSidebar && (
        <div className="w-72 border-l border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 overflow-y-auto">
          <div className="p-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="font-medium text-gray-900 dark:text-gray-100">Understanding</h3>
          </div>
          <UnderstandingSidebar understanding={understanding} />
        </div>
      )}
    </div>
  );
}
