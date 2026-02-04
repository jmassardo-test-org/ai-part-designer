/**
 * Star rating component for template ratings.
 */

import { useState } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StarRatingProps {
  /** Current rating value (1-5) */
  value: number;
  /** Callback when rating changes */
  onChange?: (value: number) => void;
  /** Whether the rating is readonly */
  readonly?: boolean;
  /** Size of the stars */
  size?: 'sm' | 'md' | 'lg';
  /** Show rating value text */
  showValue?: boolean;
  /** Number of total ratings */
  totalRatings?: number;
  /** Additional class names */
  className?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-5 w-5',
  lg: 'h-6 w-6',
};

/**
 * Interactive star rating component.
 * 
 * Displays 1-5 stars that can be clicked to set a rating.
 * Can also be used in readonly mode to display an existing rating.
 */
export function StarRating({
  value,
  onChange,
  readonly = false,
  size = 'md',
  showValue = false,
  totalRatings,
  className,
}: StarRatingProps) {
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  
  const displayValue = hoverValue ?? value;
  
  const handleClick = (star: number) => {
    if (readonly || !onChange) return;
    onChange(star);
  };
  
  const handleMouseEnter = (star: number) => {
    if (readonly) return;
    setHoverValue(star);
  };
  
  const handleMouseLeave = () => {
    setHoverValue(null);
  };
  
  return (
    <div className={cn('flex items-center gap-1', className)}>
      <div className="flex">
        {[1, 2, 3, 4, 5].map((star) => {
          const filled = star <= displayValue;
          const partial = !filled && star - 0.5 <= displayValue;
          
          return (
            <button
              key={star}
              type="button"
              disabled={readonly}
              onClick={() => handleClick(star)}
              onMouseEnter={() => handleMouseEnter(star)}
              onMouseLeave={handleMouseLeave}
              className={cn(
                'transition-colors focus:outline-none focus:ring-2 focus:ring-primary/50 rounded',
                readonly ? 'cursor-default' : 'cursor-pointer hover:scale-110',
              )}
              aria-label={`Rate ${star} stars`}
            >
              <Star
                className={cn(
                  sizeClasses[size],
                  'transition-colors',
                  filled
                    ? 'fill-yellow-400 text-yellow-400'
                    : partial
                    ? 'fill-yellow-400/50 text-yellow-400'
                    : 'fill-transparent text-gray-300 dark:text-gray-600',
                )}
              />
            </button>
          );
        })}
      </div>
      
      {showValue && (
        <span className="text-sm text-muted-foreground ml-1">
          {value.toFixed(1)}
          {totalRatings !== undefined && (
            <span className="text-xs ml-1">({totalRatings})</span>
          )}
        </span>
      )}
    </div>
  );
}

interface AverageRatingProps {
  /** Average rating value */
  average: number;
  /** Total number of ratings */
  total: number;
  /** Size of the display */
  size?: 'sm' | 'md' | 'lg';
  /** Additional class names */
  className?: string;
}

/**
 * Display component for average ratings.
 * 
 * Shows the average rating with a star icon and count.
 */
export function AverageRating({
  average,
  total,
  size = 'md',
  className,
}: AverageRatingProps) {
  return (
    <div className={cn('flex items-center gap-1', className)}>
      <Star
        className={cn(
          sizeClasses[size],
          'fill-yellow-400 text-yellow-400',
        )}
      />
      <span className={cn(
        'font-medium',
        size === 'sm' && 'text-sm',
        size === 'lg' && 'text-lg',
      )}>
        {average.toFixed(1)}
      </span>
      <span className="text-muted-foreground text-sm">
        ({total})
      </span>
    </div>
  );
}

interface RatingDistributionProps {
  /** Rating distribution: { 1: count, 2: count, ... } */
  distribution: Record<number, number>;
  /** Total ratings */
  total: number;
  /** Additional class names */
  className?: string;
}

/**
 * Displays rating distribution as horizontal bars.
 */
export function RatingDistribution({
  distribution,
  total,
  className,
}: RatingDistributionProps) {
  return (
    <div className={cn('space-y-1', className)}>
      {[5, 4, 3, 2, 1].map((star) => {
        const count = distribution[star] || 0;
        const percentage = total > 0 ? (count / total) * 100 : 0;
        
        return (
          <div key={star} className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground w-3">{star}</span>
            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
            <div className="flex-1 h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-yellow-400 rounded-full transition-all"
                style={{ width: `${percentage}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground w-8 text-right">
              {count}
            </span>
          </div>
        );
      })}
    </div>
  );
}
