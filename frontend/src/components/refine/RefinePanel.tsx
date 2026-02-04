/**
 * RefinePanel - Chat-based design refinement UI
 * 
 * Provides a conversational interface for iterative design refinement
 * using natural language instructions.
 */

import { format } from 'date-fns';
import {
  Send,
  MessageCircle,
  Loader2,
  RotateCcw,
  ChevronRight,
  ChevronDown,
  Sparkles,
  History,
  Settings2,
} from 'lucide-react';
import React, { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  parameters?: Record<string, number | string>;
}

interface DesignContext {
  id: string;
  design_id: string;
  messages: Message[];
  parameters: Record<string, number | string>;
  iteration_count: number;
  last_instruction: string | null;
}

interface RefineResponse {
  success: boolean;
  message: string;
  ai_response?: string;
  old_parameters?: Record<string, number | string>;
  new_parameters?: Record<string, number | string>;
}

interface RefinePanelProps {
  designId: string;
  onParametersChange?: (parameters: Record<string, number | string>) => void;
  onRefineComplete?: (response: RefineResponse) => void;
  className?: string;
}

const SUGGESTED_PROMPTS = [
  'Make it 20% taller',
  'Add rounded corners',
  'Make the walls thicker',
  'Add ventilation holes',
  'Double the width',
  'Make it more compact',
];

export function RefinePanel({
  designId,
  onParametersChange,
  onRefineComplete,
  className = '',
}: RefinePanelProps) {
  const [context, setContext] = useState<DesignContext | null>(null);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [showParameters, setShowParameters] = useState(true);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load context on mount
  useEffect(() => {
    loadContext();
  }, [designId]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [context?.messages]);

  const loadContext = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`/api/v1/designs/${designId}/refine/context`, {
        credentials: 'include',
      });
      
      if (!response.ok) throw new Error('Failed to load context');
      
      const data = await response.json();
      setContext(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load context');
    } finally {
      setIsLoading(false);
    }
  };

  const sendInstruction = async (instruction: string) => {
    if (!instruction.trim() || isSending) return;
    
    setIsSending(true);
    setError(null);
    
    // Optimistically add user message
    const userMessage: Message = {
      role: 'user',
      content: instruction,
      timestamp: new Date().toISOString(),
    };
    
    setContext(prev => prev ? {
      ...prev,
      messages: [...prev.messages, userMessage],
    } : null);
    
    setInputValue('');
    
    try {
      const response = await fetch(`/api/v1/designs/${designId}/refine`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          instruction,
          apply_immediately: true,
        }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to refine design');
      }
      
      const result: RefineResponse = await response.json();
      
      // Add assistant message
      if (result.ai_response) {
        const assistantMessage: Message = {
          role: 'assistant',
          content: result.ai_response,
          timestamp: new Date().toISOString(),
          parameters: result.new_parameters,
        };
        
        setContext(prev => prev ? {
          ...prev,
          messages: [...prev.messages, assistantMessage],
          parameters: result.new_parameters || prev.parameters,
          iteration_count: prev.iteration_count + 1,
        } : null);
      }
      
      // Notify parent
      if (result.new_parameters && onParametersChange) {
        onParametersChange(result.new_parameters);
      }
      if (onRefineComplete) {
        onRefineComplete(result);
      }
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to refine design');
      
      // Remove optimistic message on error
      setContext(prev => prev ? {
        ...prev,
        messages: prev.messages.slice(0, -1),
      } : null);
    } finally {
      setIsSending(false);
    }
  };

  const resetContext = async () => {
    if (!confirm('Reset conversation history? Current parameters will be preserved.')) {
      return;
    }
    
    try {
      const response = await fetch(`/api/v1/designs/${designId}/refine/context`, {
        method: 'DELETE',
        credentials: 'include',
      });
      
      if (!response.ok) throw new Error('Failed to reset context');
      
      await loadContext();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reset');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendInstruction(inputValue);
    }
  };

  const renderMessage = (message: Message, index: number) => {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';
    
    if (isSystem) {
      return (
        <div
          key={index}
          className="text-xs text-gray-500 text-center py-2 italic"
        >
          {message.content}
        </div>
      );
    }
    
    return (
      <div
        key={index}
        className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
      >
        <div
          className={`max-w-[80%] rounded-lg px-4 py-2 ${
            isUser
              ? 'bg-blue-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white'
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          
          {message.parameters && (
            <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600">
              <p className="text-xs opacity-75 mb-1">Parameter changes:</p>
              <div className="flex flex-wrap gap-1">
                {Object.entries(message.parameters).map(([key, value]) => (
                  <span
                    key={key}
                    className="text-xs px-2 py-0.5 bg-white/20 rounded"
                  >
                    {key}: {value}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          <span className="text-xs opacity-50 mt-1 block">
            {format(new Date(message.timestamp), 'HH:mm')}
          </span>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center p-8 ${className}`}>
        <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full bg-white dark:bg-gray-800 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-600" />
          <span className="font-medium">Refine Design</span>
          {context && (
            <span className="text-xs text-gray-500 bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded-full">
              v{context.iteration_count}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            title="History"
          >
            <History className="w-4 h-4" />
          </button>
          <button
            onClick={resetContext}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            title="Reset conversation"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>
      
      {/* Parameters panel (collapsible) */}
      {context && Object.keys(context.parameters).length > 0 && (
        <div className="border-b dark:border-gray-700">
          <button
            onClick={() => setShowParameters(!showParameters)}
            className="flex items-center justify-between w-full px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            <div className="flex items-center gap-2">
              <Settings2 className="w-4 h-4" />
              <span>Current Parameters</span>
            </div>
            {showParameters ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
          
          {showParameters && (
            <div className="px-4 pb-3 grid grid-cols-2 gap-2">
              {Object.entries(context.parameters).map(([key, value]) => (
                <div
                  key={key}
                  className="text-xs bg-gray-100 dark:bg-gray-700 rounded px-2 py-1"
                >
                  <span className="text-gray-500">{key}:</span>{' '}
                  <span className="font-medium">{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {context?.messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-500">
            <MessageCircle className="w-12 h-12 mb-4 opacity-30" />
            <p className="text-sm mb-4">
              Describe how you want to modify the design
            </p>
            
            {/* Suggested prompts */}
            <div className="grid grid-cols-2 gap-2 max-w-sm">
              {SUGGESTED_PROMPTS.map((prompt, i) => (
                <button
                  key={i}
                  onClick={() => sendInstruction(prompt)}
                  className="text-xs text-left px-3 py-2 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {context?.messages.map(renderMessage)}
            <div ref={messagesEndRef} />
          </>
        )}
        
        {isSending && (
          <div className="flex justify-start mb-3">
            <div className="bg-gray-100 dark:bg-gray-700 rounded-lg px-4 py-2">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
          </div>
        )}
      </div>
      
      {/* Error */}
      {error && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm">
          {error}
        </div>
      )}
      
      {/* Input */}
      <div className="border-t dark:border-gray-700 p-4">
        <div className="flex items-end gap-2">
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the change (e.g., 'make it taller')"
            rows={1}
            className="flex-1 resize-none rounded-lg border dark:border-gray-600 bg-gray-50 dark:bg-gray-700 px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isSending}
          />
          
          <button
            onClick={() => sendInstruction(inputValue)}
            disabled={!inputValue.trim() || isSending}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}

export default RefinePanel;
