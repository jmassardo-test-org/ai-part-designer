/**
 * Tests for useSlashCommands hook
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useSlashCommands, CommandHandlerContext } from '../useSlashCommands';

describe('useSlashCommands', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getCommands', () => {
    it('returns list of available commands', () => {
      const { result } = renderHook(() => useSlashCommands());
      const commands = result.current.getCommands();
      
      expect(commands).toBeInstanceOf(Array);
      expect(commands.length).toBeGreaterThan(0);
      
      // Check structure
      const saveCmd = commands.find(c => c.command === '/save');
      expect(saveCmd).toBeDefined();
      expect(saveCmd?.description).toBe('Save the current design');
    });

    it('includes aliases for commands', () => {
      const { result } = renderHook(() => useSlashCommands());
      const commands = result.current.getCommands();
      
      const saveCmd = commands.find(c => c.command === '/save');
      expect(saveCmd?.aliases).toContain('/s');
    });
  });

  describe('findCommand', () => {
    it('finds command by name', () => {
      const { result } = renderHook(() => useSlashCommands());
      const command = result.current.findCommand('save');
      
      expect(command).toBeDefined();
      expect(command?.command).toBe('save');
    });

    it('finds command by alias', () => {
      const { result } = renderHook(() => useSlashCommands());
      const command = result.current.findCommand('s');
      
      expect(command).toBeDefined();
      expect(command?.command).toBe('save');
    });

    it('returns undefined for unknown command', () => {
      const { result } = renderHook(() => useSlashCommands());
      const command = result.current.findCommand('nonexistent');
      
      expect(command).toBeUndefined();
    });

    it('is case insensitive', () => {
      const { result } = renderHook(() => useSlashCommands());
      const command = result.current.findCommand('SAVE');
      
      expect(command).toBeDefined();
      expect(command?.command).toBe('save');
    });
  });

  describe('executeCommand', () => {
    describe('/save command', () => {
      it('calls onSaveDesign when available', async () => {
        const onSaveDesign = vi.fn().mockResolvedValue(undefined);
        const context: CommandHandlerContext = { onSaveDesign };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('save', []);
        });
        
        expect(onSaveDesign).toHaveBeenCalledWith(undefined);
        expect(cmdResult?.success).toBe(true);
        expect(cmdResult?.message).toBe('Design saved');
      });

      it('passes name argument to save', async () => {
        const onSaveDesign = vi.fn().mockResolvedValue(undefined);
        const context: CommandHandlerContext = { onSaveDesign };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        await act(async () => {
          await result.current.executeCommand('save', ['My', 'Design']);
        });
        
        expect(onSaveDesign).toHaveBeenCalledWith('My Design');
      });

      it('returns error when onSaveDesign not available', async () => {
        const { result } = renderHook(() => useSlashCommands({}));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('save', []);
        });
        
        expect(cmdResult?.success).toBe(false);
        expect(cmdResult?.message).toBe('Save not available');
      });
    });

    describe('/export command', () => {
      it('exports with default stl format', async () => {
        const onExportDesign = vi.fn().mockResolvedValue(undefined);
        const context: CommandHandlerContext = { onExportDesign };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        await act(async () => {
          await result.current.executeCommand('export', []);
        });
        
        expect(onExportDesign).toHaveBeenCalledWith('stl');
      });

      it('exports with specified format', async () => {
        const onExportDesign = vi.fn().mockResolvedValue(undefined);
        const context: CommandHandlerContext = { onExportDesign };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        await act(async () => {
          await result.current.executeCommand('export', ['step']);
        });
        
        expect(onExportDesign).toHaveBeenCalledWith('step');
      });

      it('rejects invalid formats', async () => {
        const onExportDesign = vi.fn().mockResolvedValue(undefined);
        const context: CommandHandlerContext = { onExportDesign };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('export', ['invalid']);
        });
        
        expect(onExportDesign).not.toHaveBeenCalled();
        expect(cmdResult?.success).toBe(false);
      });
    });

    describe('/help command', () => {
      it('returns help text with all commands', async () => {
        const { result } = renderHook(() => useSlashCommands());
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('help', []);
        });
        
        expect(cmdResult?.success).toBe(true);
        expect(cmdResult?.message).toContain('/save');
        expect(cmdResult?.message).toContain('/export');
        expect(cmdResult?.message).toContain('/help');
        expect(cmdResult?.action).toBe('help');
      });

      it('includes command descriptions', async () => {
        const { result } = renderHook(() => useSlashCommands());
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('help', []);
        });
        
        expect(cmdResult?.message).toContain('Save the current design');
      });
    });

    describe('/clear command', () => {
      it('calls onClearChat when available', async () => {
        const onClearChat = vi.fn();
        const context: CommandHandlerContext = { onClearChat };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        await act(async () => {
          await result.current.executeCommand('clear', []);
        });
        
        expect(onClearChat).toHaveBeenCalled();
      });
    });

    describe('/undo command', () => {
      it('calls onUndo when available and canUndo is true', async () => {
        const onUndo = vi.fn();
        const context: CommandHandlerContext = { onUndo, canUndo: true };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('undo', []);
        });
        
        expect(onUndo).toHaveBeenCalled();
        expect(cmdResult?.success).toBe(true);
      });

      it('returns error when nothing to undo', async () => {
        const onUndo = vi.fn();
        const context: CommandHandlerContext = { onUndo, canUndo: false };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('undo', []);
        });
        
        expect(onUndo).not.toHaveBeenCalled();
        expect(cmdResult?.success).toBe(false);
        expect(cmdResult?.message).toBe('Nothing to undo');
      });
    });

    describe('/redo command', () => {
      it('calls onRedo when available and canRedo is true', async () => {
        const onRedo = vi.fn();
        const context: CommandHandlerContext = { onRedo, canRedo: true };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('redo', []);
        });
        
        expect(onRedo).toHaveBeenCalled();
        expect(cmdResult?.success).toBe(true);
      });

      it('returns error when nothing to redo', async () => {
        const onRedo = vi.fn();
        const context: CommandHandlerContext = { onRedo, canRedo: false };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('redo', []);
        });
        
        expect(onRedo).not.toHaveBeenCalled();
        expect(cmdResult?.success).toBe(false);
      });
    });

    describe('unknown commands', () => {
      it('returns error for unknown command', async () => {
        const { result } = renderHook(() => useSlashCommands());
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('nonexistent', []);
        });
        
        expect(cmdResult?.success).toBe(false);
        expect(cmdResult?.message).toContain('Unknown command');
      });
    });

    describe('error handling', () => {
      it('handles thrown errors gracefully', async () => {
        const onSaveDesign = vi.fn().mockRejectedValue(new Error('Save failed'));
        const context: CommandHandlerContext = { onSaveDesign };
        
        const { result } = renderHook(() => useSlashCommands(context));
        
        let cmdResult;
        await act(async () => {
          cmdResult = await result.current.executeCommand('save', []);
        });
        
        expect(cmdResult?.success).toBe(false);
        expect(cmdResult?.message).toBe('Save failed');
      });
    });
  });

  describe('lastCommand state', () => {
    it('stores the last executed command result', async () => {
      const { result } = renderHook(() => useSlashCommands());
      
      expect(result.current.lastCommand).toBeNull();
      
      await act(async () => {
        await result.current.executeCommand('help', []);
      });
      
      expect(result.current.lastCommand).not.toBeNull();
      expect(result.current.lastCommand?.action).toBe('help');
    });
  });
});
