/**
 * Tooltip Component - Accessible contextual help.
 *
 * Features:
 * - Hover and focus triggers
 * - Multiple positions
 * - Keyboard accessible
 * - Customizable delay
 */

import { useState, useRef, useEffect, ReactNode } from 'react';
import { createPortal } from 'react-dom';

// =============================================================================
// Types
// =============================================================================

type TooltipPosition = 'top' | 'bottom' | 'left' | 'right';

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  position?: TooltipPosition;
  delay?: number;
  className?: string;
  disabled?: boolean;
}

// =============================================================================
// Tooltip Component
// =============================================================================

export function Tooltip({
  content,
  children,
  position = 'top',
  delay = 200,
  className = '',
  disabled = false,
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0 });
  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<number | null>(null);

  // Calculate position
  const updatePosition = () => {
    if (!triggerRef.current || !tooltipRef.current) return;

    const triggerRect = triggerRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();

    let x = 0;
    let y = 0;

    switch (position) {
      case 'top':
        x = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;
        y = triggerRect.top - tooltipRect.height - 8;
        break;
      case 'bottom':
        x = triggerRect.left + triggerRect.width / 2 - tooltipRect.width / 2;
        y = triggerRect.bottom + 8;
        break;
      case 'left':
        x = triggerRect.left - tooltipRect.width - 8;
        y = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2;
        break;
      case 'right':
        x = triggerRect.right + 8;
        y = triggerRect.top + triggerRect.height / 2 - tooltipRect.height / 2;
        break;
    }

    // Keep within viewport
    const padding = 8;
    x = Math.max(padding, Math.min(x, window.innerWidth - tooltipRect.width - padding));
    y = Math.max(padding, Math.min(y, window.innerHeight - tooltipRect.height - padding));

    setCoords({ x, y });
  };

  // Show tooltip
  const show = () => {
    if (disabled) return;
    timeoutRef.current = window.setTimeout(() => {
      setIsVisible(true);
    }, delay);
  };

  // Hide tooltip
  const hide = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsVisible(false);
  };

  // Update position when visible
  useEffect(() => {
    if (isVisible) {
      updatePosition();
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);

      return () => {
        window.removeEventListener('scroll', updatePosition, true);
        window.removeEventListener('resize', updatePosition);
      };
    }
  }, [isVisible]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Arrow direction
  const arrowClass = {
    top: 'bottom-[-4px] left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-b-transparent',
    bottom: 'top-[-4px] left-1/2 -translate-x-1/2 border-l-transparent border-r-transparent border-t-transparent',
    left: 'right-[-4px] top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-r-transparent',
    right: 'left-[-4px] top-1/2 -translate-y-1/2 border-t-transparent border-b-transparent border-l-transparent',
  };

  return (
    <>
      <div
        ref={triggerRef}
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        className="inline-flex"
      >
        {children}
      </div>

      {isVisible &&
        createPortal(
          <div
            ref={tooltipRef}
            role="tooltip"
            className={`
              fixed z-[10000] px-3 py-2 text-sm text-white bg-gray-900 rounded-lg shadow-lg
              max-w-xs pointer-events-none animate-in fade-in-0 zoom-in-95 duration-150
              ${className}
            `}
            style={{
              left: `${coords.x}px`,
              top: `${coords.y}px`,
            }}
          >
            {content}
            <div
              className={`absolute w-0 h-0 border-4 border-gray-900 ${arrowClass[position]}`}
            />
          </div>,
          document.body
        )}
    </>
  );
}

// =============================================================================
// Icon Button with Tooltip
// =============================================================================

interface IconButtonProps {
  icon: ReactNode;
  label: string;
  onClick?: () => void;
  disabled?: boolean;
  className?: string;
  tooltipPosition?: TooltipPosition;
}

export function IconButton({
  icon,
  label,
  onClick,
  disabled = false,
  className = '',
  tooltipPosition = 'top',
}: IconButtonProps) {
  return (
    <Tooltip content={label} position={tooltipPosition}>
      <button
        onClick={onClick}
        disabled={disabled}
        aria-label={label}
        className={`
          p-2 rounded-lg transition-colors
          ${disabled 
            ? 'text-gray-300 cursor-not-allowed' 
            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
          }
          ${className}
        `}
      >
        {icon}
      </button>
    </Tooltip>
  );
}
