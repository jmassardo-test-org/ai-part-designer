/**
 * HistoryPanel Component
 * 
 * Slide-out panel for conversation/design history.
 * Provides quick access to past designs and conversations.
 */

import { X, MessageSquare, Clock, Layers, ChevronRight } from 'lucide-react';
import { useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface ConversationPreview {
  id: string;
  title: string;
  preview: string;
  timestamp: Date;
  designCount: number;
  thumbnail?: string;
}

interface HistoryPanelProps {
  /** Whether the panel is open */
  isOpen: boolean;
  /** Callback to close the panel */
  onClose: () => void;
  /** List of conversations to display */
  conversations: ConversationPreview[];
  /** Currently selected conversation ID */
  activeConversationId?: string;
  /** Callback when a conversation is selected */
  onSelectConversation: (id: string) => void;
  /** Callback to start a new conversation */
  onNewConversation?: () => void;
  /** Whether conversations are loading */
  isLoading?: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

// =============================================================================
// Component
// =============================================================================

export function HistoryPanel({
  isOpen,
  onClose,
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  isLoading = false,
}: HistoryPanelProps): JSX.Element {
  // Handle keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
  );

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, handleKeyDown]);

  // Prevent body scroll when panel is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  const handleSelectConversation = (id: string) => {
    onSelectConversation(id);
    onClose();
  };

  return (
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/50 transition-opacity duration-300',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-50 h-full w-80 transform transition-transform duration-300 ease-in-out',
          'bg-white dark:bg-gray-800 shadow-xl',
          'border-r border-gray-200 dark:border-gray-700',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        role="dialog"
        aria-modal="true"
        aria-label="Conversation history"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-500 dark:text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              History
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-md text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            aria-label="Close history panel"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* New Conversation Button */}
        {onNewConversation && (
          <div className="p-4 border-b border-gray-200 dark:border-gray-700">
            <button
              onClick={() => {
                onNewConversation();
                onClose();
              }}
              className={cn(
                'w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg',
                'bg-primary-600 hover:bg-primary-700 text-white',
                'transition-colors font-medium'
              )}
            >
              <MessageSquare className="h-4 w-4" />
              New Design
            </button>
          </div>
        )}

        {/* Conversation List */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div
                  key={i}
                  className="animate-pulse"
                  role="status"
                  aria-label="Loading"
                >
                  <div className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
                </div>
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
              <MessageSquare className="h-12 w-12 text-gray-300 dark:text-gray-600 mb-4" />
              <p className="text-gray-500 dark:text-gray-400 font-medium">
                No conversations yet
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
                Start a new design to get started
              </p>
            </div>
          ) : (
            <nav className="p-2" aria-label="Conversation history">
              <ul className="space-y-1">
                {conversations.map((conversation) => (
                  <li key={conversation.id}>
                    <button
                      onClick={() => handleSelectConversation(conversation.id)}
                      className={cn(
                        'w-full flex items-start gap-3 p-3 rounded-lg text-left transition-colors',
                        activeConversationId === conversation.id
                          ? 'bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      )}
                    >
                      {/* Thumbnail or Icon */}
                      <div className="flex-shrink-0 w-10 h-10 rounded bg-gray-100 dark:bg-gray-700 flex items-center justify-center overflow-hidden">
                        {conversation.thumbnail ? (
                          <img
                            src={conversation.thumbnail}
                            alt=""
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <Layers className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                        )}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <p
                          className={cn(
                            'font-medium truncate',
                            activeConversationId === conversation.id
                              ? 'text-primary-700 dark:text-primary-300'
                              : 'text-gray-900 dark:text-white'
                          )}
                        >
                          {conversation.title}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5">
                          {conversation.preview}
                        </p>
                        <div className="flex items-center gap-3 mt-1">
                          <span className="text-xs text-gray-400 dark:text-gray-500">
                            {formatRelativeTime(conversation.timestamp)}
                          </span>
                          {conversation.designCount > 0 && (
                            <span className="text-xs text-gray-400 dark:text-gray-500 flex items-center gap-1">
                              <Layers className="h-3 w-3" />
                              {conversation.designCount}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Arrow */}
                      <ChevronRight className="flex-shrink-0 h-4 w-4 text-gray-400 dark:text-gray-500 mt-1" />
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          )}
        </div>
      </aside>
    </>
  );
}

export default HistoryPanel;
