/**
 * ThemeToggle Component
 * 
 * A button that toggles between light and dark themes.
 * Shows sun icon for dark mode, moon icon for light mode.
 */

import { Sun, Moon, Monitor } from 'lucide-react';
import React from 'react';
import { useTheme, Theme } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';

// =============================================================================
// Types
// =============================================================================

interface ThemeToggleProps {
  /** Additional CSS classes */
  className?: string;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Whether to show a dropdown with all options */
  showDropdown?: boolean;
}

// =============================================================================
// Size Mappings
// =============================================================================

const sizeClasses = {
  sm: 'h-8 w-8',
  md: 'h-10 w-10',
  lg: 'h-12 w-12',
};

const iconSizes = {
  sm: 16,
  md: 20,
  lg: 24,
};

// =============================================================================
// Component
// =============================================================================

export function ThemeToggle({
  className,
  size = 'md',
  showDropdown = false,
}: ThemeToggleProps): JSX.Element {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  const [isOpen, setIsOpen] = React.useState(false);
  const dropdownRef = React.useRef<HTMLDivElement>(null);

  // Close dropdown on click outside
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const iconSize = iconSizes[size];

  // Simple toggle button
  if (!showDropdown) {
    return (
      <button
        type="button"
        onClick={toggleTheme}
        className={cn(
          'inline-flex items-center justify-center rounded-md',
          'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
          'hover:bg-gray-100 dark:hover:bg-gray-800',
          'transition-colors focus-visible:outline-none focus-visible:ring-2',
          'focus-visible:ring-primary-500 focus-visible:ring-offset-2',
          sizeClasses[size],
          className
        )}
        aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
      >
        {resolvedTheme === 'dark' ? (
          <Sun size={iconSize} aria-hidden="true" />
        ) : (
          <Moon size={iconSize} aria-hidden="true" />
        )}
      </button>
    );
  }

  // Dropdown with all options
  const options: { value: Theme; icon: typeof Sun; label: string }[] = [
    { value: 'light', icon: Sun, label: 'Light' },
    { value: 'dark', icon: Moon, label: 'Dark' },
    { value: 'system', icon: Monitor, label: 'System' },
  ];

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'inline-flex items-center justify-center rounded-md',
          'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
          'hover:bg-gray-100 dark:hover:bg-gray-800',
          'transition-colors focus-visible:outline-none focus-visible:ring-2',
          'focus-visible:ring-primary-500 focus-visible:ring-offset-2',
          sizeClasses[size],
          className
        )}
        aria-label="Select theme"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {resolvedTheme === 'dark' ? (
          <Moon size={iconSize} aria-hidden="true" />
        ) : (
          <Sun size={iconSize} aria-hidden="true" />
        )}
      </button>

      {isOpen && (
        <div
          className={cn(
            'absolute right-0 z-50 mt-2 w-36 origin-top-right',
            'rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5',
            'dark:bg-gray-800 dark:ring-gray-700',
            'focus:outline-none'
          )}
          role="menu"
          aria-orientation="vertical"
        >
          <div className="py-1" role="none">
            {options.map(({ value, icon: Icon, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => {
                  setTheme(value);
                  setIsOpen(false);
                }}
                className={cn(
                  'flex w-full items-center gap-2 px-4 py-2 text-sm',
                  'text-gray-700 dark:text-gray-300',
                  'hover:bg-gray-100 dark:hover:bg-gray-700',
                  theme === value && 'bg-gray-100 dark:bg-gray-700'
                )}
                role="menuitem"
              >
                <Icon size={16} aria-hidden="true" />
                <span>{label}</span>
                {theme === value && (
                  <span className="ml-auto text-primary-500">✓</span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default ThemeToggle;
