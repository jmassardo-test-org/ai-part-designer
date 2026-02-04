/**
 * Command Autocomplete component.
 *
 * Shows suggestions when user types slash commands in chat input.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';

// =============================================================================
// Types
// =============================================================================

interface Command {
  command: string;
  description: string;
  args?: string[];
}

interface CommandAutocompleteProps {
  input: string;
  onSelect: (command: string) => void;
  onClose: () => void;
  visible: boolean;
}

interface UseCommandAutocompleteOptions {
  onCommandExecuted?: (command: string, args: string[]) => void;
}

// =============================================================================
// Command Definitions
// =============================================================================

const COMMANDS: Command[] = [
  // Design management
  { command: '/save', description: 'Save the current design' },
  { command: '/saveas', description: 'Save with a new name', args: ['name'] },
  { command: '/rename', description: 'Rename current design', args: ['new_name'] },
  { command: '/delete', description: 'Delete current design' },

  // Export
  { command: '/export', description: 'Export to format (stl, step)', args: ['format'] },
  { command: '/exportall', description: 'Export all project designs', args: ['format'] },

  // Templates
  { command: '/maketemplate', description: 'Save as a template' },

  // History
  { command: '/undo', description: 'Undo last change' },
  { command: '/redo', description: 'Redo last undone change' },
  { command: '/history', description: 'Show version history' },
  { command: '/restore', description: 'Restore to version', args: ['version'] },

  // View
  { command: '/view', description: 'Switch view (top, front, side, iso)', args: ['mode'] },
  { command: '/zoom', description: 'Zoom to fit or percentage', args: ['level'] },
  { command: '/measure', description: 'Enable measurement tool' },

  // Help
  { command: '/help', description: 'Show available commands' },

  // Debug
  { command: '/debug', description: 'Show debug info' },
  { command: '/clear', description: 'Clear conversation' },
];

// =============================================================================
// Component
// =============================================================================

export function CommandAutocomplete({
  input,
  onSelect,
  onClose,
  visible,
}: CommandAutocompleteProps) {
  const [suggestions, setSuggestions] = useState<Command[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter suggestions based on input
  useEffect(() => {
    if (!input.startsWith('/')) {
      setSuggestions([]);
      return;
    }

    const query = input.slice(1).toLowerCase();
    const matches = COMMANDS.filter((c) =>
      c.command.slice(1).toLowerCase().startsWith(query)
    );
    setSuggestions(matches);
    setSelectedIndex(0);
  }, [input]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!visible || suggestions.length === 0) return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : 0
          );
          break;

        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev > 0 ? prev - 1 : suggestions.length - 1
          );
          break;

        case 'Tab':
        case 'Enter':
          if (suggestions.length > 0) {
            e.preventDefault();
            const selected = suggestions[selectedIndex];
            onSelect(selected.command + (selected.args ? ' ' : ''));
          }
          break;

        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    },
    [visible, suggestions, selectedIndex, onSelect, onClose]
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  // Scroll selected item into view
  useEffect(() => {
    if (containerRef.current && suggestions.length > 0) {
      const selectedElement = containerRef.current.querySelector(
        `[data-index="${selectedIndex}"]`
      );
      // Guard for test environment where scrollIntoView may not be available
      if (selectedElement && typeof selectedElement.scrollIntoView === 'function') {
        selectedElement.scrollIntoView({ block: 'nearest' });
      }
    }
  }, [selectedIndex, suggestions.length]);

  if (!visible || suggestions.length === 0) {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="absolute bottom-full left-0 mb-2 w-full max-w-md 
                 bg-white dark:bg-gray-800 shadow-lg rounded-lg 
                 border border-gray-200 dark:border-gray-700
                 max-h-64 overflow-y-auto z-50"
      role="listbox"
    >
      <div className="p-2 text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
        Commands (↑↓ to navigate, Tab/Enter to select)
      </div>

      {suggestions.map((cmd, index) => (
        <button
          key={cmd.command}
          data-index={index}
          onClick={() => onSelect(cmd.command + (cmd.args ? ' ' : ''))}
          className={`
            w-full px-4 py-2.5 text-left flex items-start gap-3
            hover:bg-gray-50 dark:hover:bg-gray-700
            ${index === selectedIndex
              ? 'bg-blue-50 dark:bg-blue-900/30'
              : ''
            }
          `}
          role="option"
          aria-selected={index === selectedIndex}
        >
          <span className="font-mono text-blue-600 dark:text-blue-400 font-medium">
            {cmd.command}
          </span>
          <span className="text-gray-600 dark:text-gray-300 text-sm">
            {cmd.description}
          </span>
          {cmd.args && (
            <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">
              {cmd.args.map((a) => `<${a}>`).join(' ')}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

// =============================================================================
// Hook for command detection
// =============================================================================

export function useCommandAutocomplete(_options: UseCommandAutocompleteOptions = {}) {
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [inputValue, setInputValue] = useState('');

  const handleInputChange = useCallback((value: string) => {
    setInputValue(value);

    // Show autocomplete when typing a command
    if (value.startsWith('/') && !value.includes(' ')) {
      setShowAutocomplete(true);
    } else {
      setShowAutocomplete(false);
    }
  }, []);

  const handleCommandSelect = useCallback((command: string) => {
    setInputValue(command);
    setShowAutocomplete(false);
  }, []);

  const handleClose = useCallback(() => {
    setShowAutocomplete(false);
  }, []);

  const isCommand = inputValue.startsWith('/');

  const parseCommand = useCallback((): { command: string; args: string[] } | null => {
    if (!isCommand) return null;

    const parts = inputValue.slice(1).split(/\s+/);
    const command = parts[0]?.toLowerCase();
    const args = parts.slice(1);

    return { command, args };
  }, [inputValue, isCommand]);

  return {
    showAutocomplete,
    inputValue,
    setInputValue,
    handleInputChange,
    handleCommandSelect,
    handleClose,
    isCommand,
    parseCommand,
  };
}

export default CommandAutocomplete;
