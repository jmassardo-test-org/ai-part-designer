/**
 * Chat input component with send button.
 */

import { useState, useRef, useCallback, KeyboardEvent } from 'react';
import { Send, Loader2 } from 'lucide-react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  loading?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled = false,
  loading = false,
  placeholder = "Describe the part you want to create...",
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  const handleSend = useCallback(() => {
    const trimmed = message.trim();
    if (trimmed && !disabled && !loading) {
      onSend(trimmed);
      setMessage('');
      
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [message, disabled, loading, onSend]);
  
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
    <div className="flex-1 relative">
      <textarea
        ref={textareaRef}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        placeholder={placeholder}
        disabled={disabled || loading}
        rows={1}
        className="w-full px-4 py-2.5 pr-12 bg-gray-50 text-gray-900 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent focus:bg-white disabled:bg-gray-100 disabled:text-gray-500 text-sm"
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
  );
}
