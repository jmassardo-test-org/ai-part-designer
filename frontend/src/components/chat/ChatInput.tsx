/**
 * Chat input component with send button and slash command support.
 */

import { Send, Loader2, Wand2 } from 'lucide-react';
import { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { CommandAutocomplete, useCommandAutocomplete } from './CommandAutocomplete';

interface CommandResult {
  success: boolean;
  message: string;
  action?: string;
}

interface ChatInputProps {
  onSend: (message: string) => void;
  onGenerate?: () => void;
  onCommand?: (command: string, args: string[]) => Promise<CommandResult> | CommandResult;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
  showGenerateButton?: boolean;
  generateDisabled?: boolean;
}

export function ChatInput({
  onSend,
  onGenerate,
  onCommand,
  disabled = false,
  loading = false,
  placeholder = "Describe the part you want to create...",
  showGenerateButton = false,
  generateDisabled = false,
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Command autocomplete hook
  const {
    showAutocomplete,
    handleInputChange,
    handleCommandSelect,
    handleClose,
    isCommand,
    parseCommand,
  } = useCommandAutocomplete();
  
  const handleSend = useCallback(async () => {
    const trimmed = message.trim();
    if (!trimmed || disabled || loading) return;
    
    // Check if this is a command
    if (isCommand && onCommand) {
      const parsed = parseCommand();
      if (parsed) {
        const result = await onCommand(parsed.command, parsed.args);
        if (result.success) {
          setMessage('');
          if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
          }
          return;
        }
      }
    }
    
    // Regular message
    onSend(trimmed);
    setMessage('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [message, disabled, loading, onSend, onCommand, isCommand, parseCommand]);
  
  const handleMessageChange = useCallback((value: string) => {
    setMessage(value);
    handleInputChange(value);
  }, [handleInputChange]);
  
  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Send on Enter (without shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);
  
  const handleInput = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      // Auto-resize textarea
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, []);

  return (
    <div className="p-3 border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
      <div className="flex items-end gap-2">
        <div className="flex-1 relative">
          {/* Command Autocomplete Dropdown */}
          <CommandAutocomplete
            input={message}
            onSelect={(cmd) => {
              handleCommandSelect(cmd);
              setMessage(cmd);
            }}
            onClose={handleClose}
            visible={showAutocomplete}
          />
          
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => handleMessageChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onInput={handleInput}
            placeholder={placeholder}
            disabled={disabled || loading}
            rows={1}
            className="w-full px-4 py-2.5 pr-12 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 border border-gray-200 dark:border-gray-600 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent focus:bg-white dark:focus:bg-gray-600 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:text-gray-500 dark:disabled:text-gray-400 text-sm placeholder:text-gray-400 dark:placeholder:text-gray-500"
            style={{ minHeight: '42px', maxHeight: '120px' }}
          />
          
          <button
            onClick={handleSend}
            disabled={!message.trim() || disabled || loading}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-md bg-primary-600 text-white disabled:bg-gray-300 disabled:cursor-not-allowed hover:bg-primary-700 transition-colors"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        
        {showGenerateButton && onGenerate && (
          <button
            onClick={onGenerate}
            disabled={generateDisabled || loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium text-sm"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Wand2 className="w-4 h-4" />
            )}
            Generate
          </button>
        )}
      </div>
    </div>
  );
}
