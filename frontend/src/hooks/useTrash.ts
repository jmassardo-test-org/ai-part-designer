/**
 * Hook for managing trash operations.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { useToast } from '@/hooks/use-toast';
import trashApi, { 
  TrashedItem, 
  TrashListResponse, 
  TrashSettings, 
  TrashStats 
} from '@/lib/api/trash';

export interface UseTrashOptions {
  page?: number;
  pageSize?: number;
  itemType?: 'design' | 'project' | 'file';
}

export function useTrash(options: UseTrashOptions = {}) {
  const { page = 1, pageSize = 20, itemType } = options;
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Fetch trashed items
  const {
    data: trashData,
    isLoading,
    error,
    refetch,
  } = useQuery<TrashListResponse>({
    queryKey: ['trash', page, pageSize, itemType],
    queryFn: () => trashApi.listTrash(page, pageSize, itemType),
  });

  // Fetch trash stats
  const { data: stats } = useQuery<TrashStats>({
    queryKey: ['trash-stats'],
    queryFn: () => trashApi.getStats(),
  });

  // Fetch trash settings
  const { data: settings } = useQuery<TrashSettings>({
    queryKey: ['trash-settings'],
    queryFn: () => trashApi.getSettings(),
  });

  // Restore item mutation
  const restoreMutation = useMutation({
    mutationFn: ({ itemId, itemType }: { itemId: string; itemType: string }) =>
      trashApi.restoreItem(itemId, itemType),
    onSuccess: (data) => {
      toast({
        title: 'Item restored',
        description: data.message,
      });
      queryClient.invalidateQueries({ queryKey: ['trash'] });
      queryClient.invalidateQueries({ queryKey: ['trash-stats'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to restore',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Permanently delete mutation
  const deleteMutation = useMutation({
    mutationFn: ({ itemId, itemType }: { itemId: string; itemType: string }) =>
      trashApi.permanentlyDelete(itemId, itemType),
    onSuccess: () => {
      toast({
        title: 'Item permanently deleted',
        description: 'The item has been permanently removed.',
      });
      queryClient.invalidateQueries({ queryKey: ['trash'] });
      queryClient.invalidateQueries({ queryKey: ['trash-stats'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to delete',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Empty trash mutation
  const emptyTrashMutation = useMutation({
    mutationFn: () => trashApi.emptyTrash(),
    onSuccess: (data) => {
      toast({
        title: 'Trash emptied',
        description: `${data.deleted_count} items permanently deleted.`,
      });
      queryClient.invalidateQueries({ queryKey: ['trash'] });
      queryClient.invalidateQueries({ queryKey: ['trash-stats'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to empty trash',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Update settings mutation
  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: Partial<TrashSettings>) =>
      trashApi.updateSettings(newSettings),
    onSuccess: () => {
      toast({
        title: 'Settings updated',
        description: 'Trash settings have been saved.',
      });
      queryClient.invalidateQueries({ queryKey: ['trash-settings'] });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to update settings',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // Actions
  const restoreItem = useCallback(
    (item: TrashedItem) => {
      restoreMutation.mutate({ itemId: item.id, itemType: item.item_type });
    },
    [restoreMutation]
  );

  const deleteItem = useCallback(
    (item: TrashedItem) => {
      deleteMutation.mutate({ itemId: item.id, itemType: item.item_type });
    },
    [deleteMutation]
  );

  const emptyTrash = useCallback(() => {
    emptyTrashMutation.mutate();
  }, [emptyTrashMutation]);

  const updateSettings = useCallback(
    (newSettings: Partial<TrashSettings>) => {
      updateSettingsMutation.mutate(newSettings);
    },
    [updateSettingsMutation]
  );

  return {
    // Data
    items: trashData?.items ?? [],
    total: trashData?.total ?? 0,
    retentionDays: trashData?.retention_days ?? 30,
    stats,
    settings,
    
    // Loading states
    isLoading,
    isRestoring: restoreMutation.isPending,
    isDeleting: deleteMutation.isPending,
    isEmptying: emptyTrashMutation.isPending,
    isUpdatingSettings: updateSettingsMutation.isPending,
    
    // Error
    error,
    
    // Actions
    restoreItem,
    deleteItem,
    emptyTrash,
    updateSettings,
    refetch,
  };
}

export default useTrash;
