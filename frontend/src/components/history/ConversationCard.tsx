/**
 * ConversationCard Component
 * 
 * Displays a conversation preview with title, thumbnail, timestamp, and design count.
 * Implements US-56007: Conversation Redesign requirements.
 */

import { Layers, Clock, Image as ImageIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

export interface ConversationCardData {
  /** Unique identifier */
  id: string;
  /** Conversation title (first line of prompt) */
  title: string;
  /** Preview text (continuation of prompt) */
  preview?: string;
  /** Timestamp of last activity */
  timestamp: Date;
  /** Number of designs in conversation */
  designCount: number;
  /** URL to thumbnail image of generated design */
  thumbnailUrl?: string;
  /** Whether the conversation is currently active */
  isActive?: boolean;
}

interface ConversationCardProps {
  /** Conversation data */
  conversation: ConversationCardData;
  /** Click handler */
  onClick?: () => void;
  /** Additional class names */
  className?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show the preview text */
  showPreview?: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Format a date to relative time (e.g., "2h ago", "Yesterday")
 */
// eslint-disable-next-line react-refresh/only-export-components
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);
  const diffWeeks = Math.floor(diffDays / 7);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffWeeks === 1) return '1 week ago';
  if (diffWeeks < 4) return `${diffWeeks} weeks ago`;
  
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: now.getFullYear() !== date.getFullYear() ? 'numeric' : undefined,
  });
}

/**
 * Extract title from prompt text (first line)
 */
// eslint-disable-next-line react-refresh/only-export-components
export function extractTitleFromPrompt(prompt: string): string {
  if (!prompt) return 'Untitled Design';
  
  // Get first line or first 50 characters
  const firstLine = prompt.split('\n')[0].trim();
  if (firstLine.length > 50) {
    return firstLine.substring(0, 47) + '...';
  }
  return firstLine || 'Untitled Design';
}

/**
 * Extract preview from prompt text (after first line)
 */
// eslint-disable-next-line react-refresh/only-export-components
export function extractPreviewFromPrompt(prompt: string): string {
  if (!prompt) return '';
  
  const lines = prompt.split('\n');
  if (lines.length <= 1) return '';
  
  const preview = lines.slice(1).join(' ').trim();
  if (preview.length > 80) {
    return preview.substring(0, 77) + '...';
  }
  return preview;
}

// =============================================================================
// Subcomponents
// =============================================================================

interface ThumbnailProps {
  url?: string;
  size: 'sm' | 'md' | 'lg';
}

function Thumbnail({ url, size }: ThumbnailProps): JSX.Element {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16',
  };

  return (
    <div
      className={cn(
        'flex-shrink-0 rounded-md overflow-hidden bg-gray-100 dark:bg-gray-700',
        'flex items-center justify-center',
        sizeClasses[size]
      )}
    >
      {url ? (
        <img
          src={url}
          alt="Design preview"
          className="w-full h-full object-cover"
          loading="lazy"
        />
      ) : (
        <ImageIcon className="w-1/2 h-1/2 text-gray-400 dark:text-gray-500" />
      )}
    </div>
  );
}

interface MetadataProps {
  timestamp: Date;
  designCount: number;
  size: 'sm' | 'md' | 'lg';
}

function Metadata({ timestamp, designCount, size }: MetadataProps): JSX.Element {
  const textSize = size === 'sm' ? 'text-xs' : 'text-xs';

  return (
    <div className={cn('flex items-center gap-3', textSize, 'text-gray-400 dark:text-gray-500')}>
      <span className="flex items-center gap-1">
        <Clock className="h-3 w-3" />
        {formatRelativeTime(timestamp)}
      </span>
      {designCount > 0 && (
        <span className="flex items-center gap-1">
          <Layers className="h-3 w-3" />
          {designCount} {designCount === 1 ? 'design' : 'designs'}
        </span>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ConversationCard({
  conversation,
  onClick,
  className,
  size = 'md',
  showPreview = true,
}: ConversationCardProps): JSX.Element {
  const { title, preview, timestamp, designCount, thumbnailUrl, isActive } = conversation;

  const paddingClasses = {
    sm: 'p-2',
    md: 'p-3',
    lg: 'p-4',
  };

  const gapClasses = {
    sm: 'gap-2',
    md: 'gap-3',
    lg: 'gap-4',
  };

  return (
    <article
      className={cn(
        'flex items-start rounded-lg transition-all duration-200',
        paddingClasses[size],
        gapClasses[size],
        onClick && 'cursor-pointer',
        isActive
          ? 'bg-primary-50 dark:bg-primary-900/20 ring-1 ring-primary-200 dark:ring-primary-700'
          : 'bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-750',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
      aria-current={isActive ? 'true' : undefined}
    >
      {/* Thumbnail */}
      <Thumbnail url={thumbnailUrl} size={size} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Title */}
        <h3
          className={cn(
            'font-medium truncate',
            size === 'sm' ? 'text-sm' : 'text-base',
            isActive
              ? 'text-primary-700 dark:text-primary-300'
              : 'text-gray-900 dark:text-white'
          )}
        >
          {title}
        </h3>

        {/* Preview */}
        {showPreview && preview && (
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5">
            {preview}
          </p>
        )}

        {/* Metadata */}
        <div className="mt-1.5">
          <Metadata timestamp={timestamp} designCount={designCount} size={size} />
        </div>
      </div>
    </article>
  );
}

export default ConversationCard;
