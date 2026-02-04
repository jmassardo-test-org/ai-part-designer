/**
 * Slash Command Handler Hook
 * 
 * Provides command execution logic for slash commands in chat.
 * Handles /save, /export, /help, /clear, /undo, /redo, etc.
 */

import { useCallback, useState } from 'react';

// =============================================================================
// Types
// =============================================================================

export interface CommandResult {
  success: boolean;
  message: string;
  action?: string;
  data?: unknown;
}

export interface CommandHandlerContext {
  // Design operations
  currentDesignId?: string;
  onSaveDesign?: (name?: string) => Promise<void>;
  onExportDesign?: (format: string) => Promise<void>;
  onSaveAsTemplate?: (name?: string) => Promise<void>;
  
  // History operations
  onUndo?: () => void;
  onRedo?: () => void;
  canUndo?: boolean;
  canRedo?: boolean;
  
  // Chat operations
  onClearChat?: () => void;
  onShowMessage?: (message: string, type?: 'info' | 'success' | 'error') => void;
}

interface CommandDefinition {
  command: string;
  aliases: string[];
  description: string;
  usage: string;
  handler: (args: string[], ctx: CommandHandlerContext) => Promise<CommandResult> | CommandResult;
}

// =============================================================================
// Command Definitions
// =============================================================================

const COMMAND_DEFINITIONS: CommandDefinition[] = [
  {
    command: 'save',
    aliases: ['s'],
    description: 'Save the current design',
    usage: '/save [name]',
    handler: async (args, ctx) => {
      if (!ctx.onSaveDesign) {
        return { success: false, message: 'Save not available' };
      }
      const name = args.join(' ') || undefined;
      await ctx.onSaveDesign(name);
      return { 
        success: true, 
        message: name ? `Design saved as "${name}"` : 'Design saved',
        action: 'save',
      };
    },
  },
  {
    command: 'export',
    aliases: ['e'],
    description: 'Export design to format (stl, step, obj)',
    usage: '/export <format>',
    handler: async (args, ctx) => {
      if (!ctx.onExportDesign) {
        return { success: false, message: 'Export not available' };
      }
      const format = args[0]?.toLowerCase() || 'stl';
      const validFormats = ['stl', 'step', 'obj', 'gltf', 'glb'];
      
      if (!validFormats.includes(format)) {
        return { 
          success: false, 
          message: `Invalid format "${format}". Available: ${validFormats.join(', ')}`,
        };
      }
      
      await ctx.onExportDesign(format);
      return { 
        success: true, 
        message: `Exporting design as ${format.toUpperCase()}...`,
        action: 'export',
      };
    },
  },
  {
    command: 'template',
    aliases: ['mt', 'maketemplate'],
    description: 'Save current design as a reusable template',
    usage: '/template [name]',
    handler: async (args, ctx) => {
      if (!ctx.onSaveAsTemplate) {
        return { success: false, message: 'Template creation not available' };
      }
      const name = args.join(' ') || undefined;
      await ctx.onSaveAsTemplate(name);
      return { 
        success: true, 
        message: name ? `Template "${name}" created` : 'Template created',
        action: 'template',
      };
    },
  },
  {
    command: 'help',
    aliases: ['h', '?'],
    description: 'Show available commands',
    usage: '/help',
    handler: () => {
      const helpText = COMMAND_DEFINITIONS.map(cmd => {
        const aliases = cmd.aliases.length > 0 
          ? ` (or /${cmd.aliases.join(', /')})` 
          : '';
        return `**/${cmd.command}**${aliases}\n  ${cmd.description}\n  Usage: \`${cmd.usage}\``;
      }).join('\n\n');
      
      return { 
        success: true, 
        message: helpText,
        action: 'help',
        data: COMMAND_DEFINITIONS,
      };
    },
  },
  {
    command: 'clear',
    aliases: [],
    description: 'Clear chat conversation history',
    usage: '/clear',
    handler: (_, ctx) => {
      if (!ctx.onClearChat) {
        return { success: false, message: 'Clear not available' };
      }
      ctx.onClearChat();
      return { 
        success: true, 
        message: 'Chat cleared',
        action: 'clear',
      };
    },
  },
  {
    command: 'undo',
    aliases: [],
    description: 'Undo last design change',
    usage: '/undo',
    handler: (_, ctx) => {
      if (!ctx.onUndo) {
        return { success: false, message: 'Undo not available' };
      }
      if (!ctx.canUndo) {
        return { success: false, message: 'Nothing to undo' };
      }
      ctx.onUndo();
      return { 
        success: true, 
        message: 'Undone',
        action: 'undo',
      };
    },
  },
  {
    command: 'redo',
    aliases: [],
    description: 'Redo last undone change',
    usage: '/redo',
    handler: (_, ctx) => {
      if (!ctx.onRedo) {
        return { success: false, message: 'Redo not available' };
      }
      if (!ctx.canRedo) {
        return { success: false, message: 'Nothing to redo' };
      }
      ctx.onRedo();
      return { 
        success: true, 
        message: 'Redone',
        action: 'redo',
      };
    },
  },
];

// =============================================================================
// Hook
// =============================================================================

export function useSlashCommands(context: CommandHandlerContext = {}) {
  const [lastCommand, setLastCommand] = useState<CommandResult | null>(null);

  const findCommand = useCallback((cmdName: string): CommandDefinition | undefined => {
    const normalized = cmdName.toLowerCase();
    return COMMAND_DEFINITIONS.find(
      def => def.command === normalized || def.aliases.includes(normalized)
    );
  }, []);

  const executeCommand = useCallback(async (
    commandName: string, 
    args: string[]
  ): Promise<CommandResult> => {
    const definition = findCommand(commandName);
    
    if (!definition) {
      const result: CommandResult = {
        success: false,
        message: `Unknown command "/${commandName}". Type /help for available commands.`,
      };
      return result;
    }
    
    try {
      const result = await definition.handler(args, context);
      setLastCommand(result);
      return result;
    } catch (error) {
      const result: CommandResult = {
        success: false,
        message: error instanceof Error ? error.message : 'Command failed',
      };
      return result;
    }
  }, [findCommand, context]);

  const getCommands = useCallback(() => {
    return COMMAND_DEFINITIONS.map(def => ({
      command: `/${def.command}`,
      aliases: def.aliases.map(a => `/${a}`),
      description: def.description,
      usage: def.usage,
    }));
  }, []);

  return {
    executeCommand,
    findCommand,
    getCommands,
    lastCommand,
    commandDefinitions: COMMAND_DEFINITIONS,
  };
}

export default useSlashCommands;
