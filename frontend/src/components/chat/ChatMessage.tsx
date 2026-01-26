/**
 * Chat message component for conversation UI.
 */

import { useMemo } from 'react';
import { 
  User, 
  Bot, 
  AlertCircle, 
  CheckCircle2, 
  Download,
  Loader2,
  HelpCircle,
  Clipboard,
  Settings
} from 'lucide-react';
import type { Message } from '@/lib/conversations';
import { formatDistanceToNow } from 'date-fns';

interface ChatMessageProps {
  message: Message;
  onDownload?: (format: 'step' | 'stl') => void;
  onOptionSelect?: (option: string) => void;
}

export function ChatMessage({ message, onDownload, onOptionSelect }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const isSystem = message.role === 'system';
  
  const formattedTime = useMemo(() => {
    try {
      return formatDistanceToNow(new Date(message.created_at), { addSuffix: true });
    } catch {
      return '';
    }
  }, [message.created_at]);
  
  // Parse markdown-like formatting
  const formattedContent = useMemo(() => {
    let content = message.content;
    
    // Convert **bold** to <strong>
    content = content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    
    // Convert _italic_ to <em>
    content = content.replace(/_([^_]+)_/g, '<em class="text-gray-500">$1</em>');
    
    // Convert newlines to <br>
    content = content.replace(/\n/g, '<br>');
    
    return content;
  }, [message.content]);
  
  const Icon = useMemo(() => {
    if (isUser) return User;
    if (isSystem) return Settings;
    
    switch (message.message_type) {
      case 'error':
        return AlertCircle;
      case 'result':
        return CheckCircle2;
      case 'clarification':
        return HelpCircle;
      case 'confirmation':
        return Clipboard;
      case 'progress':
        return Loader2;
      default:
        return Bot;
    }
  }, [isUser, isSystem, message.message_type]);
  
  const iconColor = useMemo(() => {
    if (isUser) return 'text-blue-600';
    if (message.message_type === 'error') return 'text-red-500';
    if (message.message_type === 'result') return 'text-green-500';
    if (message.message_type === 'clarification') return 'text-amber-500';
    return 'text-purple-600';
  }, [isUser, message.message_type]);
  
  const bgColor = useMemo(() => {
    if (isUser) return 'bg-blue-50';
    if (message.message_type === 'error') return 'bg-red-50';
    if (message.message_type === 'result') return 'bg-green-50';
    if (message.message_type === 'clarification') return 'bg-amber-50';
    return 'bg-gray-50';
  }, [isUser, message.message_type]);
  
  // Extract options from clarification questions
  const options = useMemo(() => {
    if (message.message_type !== 'clarification') return [];
    const extraData = message.extra_data as { questions?: Array<{ options: string[] }> } | undefined;
    return extraData?.questions?.flatMap(q => q.options) || [];
  }, [message]);
  
  // Extract download info from result
  const downloads = useMemo(() => {
    if (message.message_type !== 'result') return null;
    const extraData = message.extra_data as { downloads?: { step?: string; stl?: string } } | undefined;
    return extraData?.downloads;
  }, [message]);

  return (
    <div className={`flex gap-2.5 p-3 ${bgColor} rounded-lg`}>
      <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${isUser ? 'bg-blue-100' : 'bg-gray-200'}`}>
        <Icon className={`w-4 h-4 ${iconColor} ${message.message_type === 'progress' ? 'animate-spin' : ''}`} />
      </div>
      
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-medium text-xs text-gray-900">
            {isUser ? 'You' : isSystem ? 'System' : 'AI Assistant'}
          </span>
          {formattedTime && (
            <span className="text-[10px] text-gray-400">{formattedTime}</span>
          )}
        </div>
        
        <div 
          className="text-gray-700 text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: formattedContent }}
        />
        
        {/* Quick option buttons for clarification */}
        {options.length > 0 && onOptionSelect && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {options.map((option, index) => (
              <button
                key={index}
                onClick={() => onOptionSelect(option)}
                className="px-2.5 py-1 text-xs bg-white border border-gray-300 rounded-full hover:bg-gray-50 hover:border-gray-400 transition-colors"
              >
                {option}
              </button>
            ))}
          </div>
        )}
        
        {/* Download buttons for result */}
        {downloads && onDownload && (
          <div className="flex gap-2 mt-2">
            {downloads.step && (
              <button
                onClick={() => onDownload('step')}
                className="flex items-center gap-1 px-2.5 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                STEP
              </button>
            )}
            {downloads.stl && (
              <button
                onClick={() => onDownload('stl')}
                className="flex items-center gap-1 px-2.5 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                STL
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
