/**
 * Thumbs up/down feedback component.
 */

import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ThumbsFeedbackProps {
  /** Number of thumbs up */
  thumbsUp: number;
  /** Number of thumbs down */
  thumbsDown: number;
  /** User's current feedback */
  userFeedback?: 'thumbs_up' | 'thumbs_down' | null;
  /** Callback when feedback changes */
  onFeedback?: (type: 'thumbs_up' | 'thumbs_down' | null) => void;
  /** Whether feedback is disabled */
  disabled?: boolean;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Additional class names */
  className?: string;
}

/**
 * Thumbs up/down feedback buttons.
 * 
 * Allows users to give quick positive or negative feedback on content.
 */
export function ThumbsFeedback({
  thumbsUp,
  thumbsDown,
  userFeedback,
  onFeedback,
  disabled = false,
  size = 'md',
  className,
}: ThumbsFeedbackProps) {
  const handleClick = (type: 'thumbs_up' | 'thumbs_down') => {
    if (disabled || !onFeedback) return;
    
    // Toggle off if clicking the same feedback
    if (userFeedback === type) {
      onFeedback(null);
    } else {
      onFeedback(type);
    }
  };
  
  const iconSize = size === 'sm' ? 'h-4 w-4' : 'h-5 w-5';
  const buttonSize = size === 'sm' ? 'h-8 px-2' : 'h-9 px-3';
  
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <Button
        variant={userFeedback === 'thumbs_up' ? 'default' : 'outline'}
        size="sm"
        disabled={disabled}
        onClick={() => handleClick('thumbs_up')}
        className={cn(
          buttonSize,
          userFeedback === 'thumbs_up' && 'bg-green-600 hover:bg-green-700',
        )}
      >
        <ThumbsUp className={cn(iconSize, 'mr-1')} />
        <span className="text-sm">{thumbsUp}</span>
      </Button>
      
      <Button
        variant={userFeedback === 'thumbs_down' ? 'default' : 'outline'}
        size="sm"
        disabled={disabled}
        onClick={() => handleClick('thumbs_down')}
        className={cn(
          buttonSize,
          userFeedback === 'thumbs_down' && 'bg-red-600 hover:bg-red-700',
        )}
      >
        <ThumbsDown className={cn(iconSize, 'mr-1')} />
        <span className="text-sm">{thumbsDown}</span>
      </Button>
    </div>
  );
}

interface FeedbackSummaryProps {
  /** Number of thumbs up */
  thumbsUp: number;
  /** Number of thumbs down */
  thumbsDown: number;
  /** Size variant */
  size?: 'sm' | 'md';
  /** Additional class names */
  className?: string;
}

/**
 * Read-only display of feedback summary.
 */
export function FeedbackSummary({
  thumbsUp,
  thumbsDown,
  size = 'md',
  className,
}: FeedbackSummaryProps) {
  const iconSize = size === 'sm' ? 'h-3 w-3' : 'h-4 w-4';
  const total = thumbsUp + thumbsDown;
  const positivePercent = total > 0 ? Math.round((thumbsUp / total) * 100) : 0;
  
  return (
    <div className={cn('flex items-center gap-3 text-muted-foreground', className)}>
      <div className="flex items-center gap-1">
        <ThumbsUp className={cn(iconSize, 'text-green-500')} />
        <span className="text-sm">{thumbsUp}</span>
      </div>
      <div className="flex items-center gap-1">
        <ThumbsDown className={cn(iconSize, 'text-red-500')} />
        <span className="text-sm">{thumbsDown}</span>
      </div>
      {total > 0 && (
        <span className="text-xs">
          ({positivePercent}% positive)
        </span>
      )}
    </div>
  );
}
