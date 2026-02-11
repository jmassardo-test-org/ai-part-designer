/**
 * Trash Page - View and manage deleted items.
 */

import { formatDistanceToNow } from 'date-fns';
import {
  AlertTriangle,
  Clock,
  FileIcon,
  FolderIcon,
  Box,
  RotateCcw,
  Trash2,
  Settings,
  AlertCircle,
} from 'lucide-react';
import { useState } from 'react';
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useTrash } from '@/hooks/useTrash';
import { cn } from '@/lib/utils';
import { TrashedItem } from '@/lib/api/trash';

function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === 0) return '—';
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
}

function getItemIcon(itemType: string) {
  switch (itemType) {
    case 'design':
      return <Box className="h-4 w-4 text-accent-500" />;
    case 'project':
      return <FolderIcon className="h-4 w-4 text-blue-500" />;
    case 'file':
      return <FileIcon className="h-4 w-4 text-gray-500" />;
    default:
      return <FileIcon className="h-4 w-4" />;
  }
}

function DeletionWarningBanner({ itemsExpiringSoon }: { itemsExpiringSoon: number }) {
  if (itemsExpiringSoon === 0) return null;

  return (
    <Alert variant="destructive" className="mb-6">
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>Items Expiring Soon</AlertTitle>
      <AlertDescription>
        {itemsExpiringSoon} item{itemsExpiringSoon !== 1 ? 's' : ''} will be permanently 
        deleted within the next 7 days. Restore them now to keep them.
      </AlertDescription>
    </Alert>
  );
}

function TrashItemRow({
  item,
  onRestore,
  onDelete,
  isRestoring,
  isDeleting,
}: {
  item: TrashedItem;
  onRestore: (item: TrashedItem) => void;
  onDelete: (item: TrashedItem) => void;
  isRestoring: boolean;
  isDeleting: boolean;
}) {
  const isExpiringSoon = item.days_until_deletion <= 7;
  const isExpiringSoonCritical = item.days_until_deletion <= 3;

  return (
    <TableRow className={cn(isExpiringSoonCritical && 'bg-red-50 dark:bg-red-950/20')}>
      <TableCell>
        <div className="flex items-center gap-2">
          {getItemIcon(item.item_type)}
          <span className="font-medium">{item.name}</span>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="secondary" className="capitalize">
          {item.item_type}
        </Badge>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {formatDistanceToNow(new Date(item.deleted_at), { addSuffix: true })}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-1">
          <Clock className={cn(
            'h-3 w-3',
            isExpiringSoonCritical ? 'text-red-500' : isExpiringSoon ? 'text-amber-500' : 'text-muted-foreground'
          )} />
          <span className={cn(
            'text-sm',
            isExpiringSoonCritical ? 'text-red-600 font-medium' : isExpiringSoon ? 'text-amber-600' : 'text-muted-foreground'
          )}>
            {item.days_until_deletion} day{item.days_until_deletion !== 1 ? 's' : ''}
          </span>
        </div>
      </TableCell>
      <TableCell className="text-muted-foreground text-sm">
        {formatBytes(item.size_bytes)}
      </TableCell>
      <TableCell>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onRestore(item)}
            disabled={isRestoring || isDeleting}
          >
            <RotateCcw className="h-4 w-4 mr-1" />
            Restore
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="text-red-600 hover:text-red-700 hover:bg-red-50"
            onClick={() => onDelete(item)}
            disabled={isRestoring || isDeleting}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}

export default function TrashPage() {
  const [page, setPage] = useState(1);
  const [itemTypeFilter, setItemTypeFilter] = useState<'all' | 'design' | 'project' | 'file'>('all');
  const [showEmptyDialog, setShowEmptyDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [itemToDelete, setItemToDelete] = useState<TrashedItem | null>(null);

  const {
    items,
    total,
    retentionDays,
    stats,
    settings,
    isLoading,
    isRestoring,
    isDeleting,
    isEmptying,
    restoreItem,
    deleteItem,
    emptyTrash,
    updateSettings,
  } = useTrash({
    page,
    pageSize: 20,
    itemType: itemTypeFilter === 'all' ? undefined : itemTypeFilter,
  });

  const handleDelete = (item: TrashedItem) => {
    setItemToDelete(item);
    setShowDeleteDialog(true);
  };

  const confirmDelete = () => {
    if (itemToDelete) {
      deleteItem(itemToDelete);
      setShowDeleteDialog(false);
      setItemToDelete(null);
    }
  };

  const handleEmptyTrash = () => {
    emptyTrash();
    setShowEmptyDialog(false);
  };

  if (isLoading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Trash2 className="h-6 w-6" />
            Trash
          </h1>
          <p className="text-muted-foreground mt-1">
            Items in trash are automatically deleted after {retentionDays} days
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowSettingsDialog(true)}
          >
            <Settings className="h-4 w-4 mr-1" />
            Settings
          </Button>
          {items.length > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowEmptyDialog(true)}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              Empty Trash
            </Button>
          )}
        </div>
      </div>

      {/* Warning banner for items expiring soon */}
      {stats && <DeletionWarningBanner itemsExpiringSoon={stats.items_expiring_soon} />}

      {/* Stats cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Items
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_items}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Size
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatBytes(stats.total_size_bytes)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Expiring Soon
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className={cn(
                'text-2xl font-bold',
                stats.items_expiring_soon > 0 && 'text-amber-600'
              )}>
                {stats.items_expiring_soon}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Oldest Item
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats.oldest_item_date
                  ? formatDistanceToNow(new Date(stats.oldest_item_date), { addSuffix: true })
                  : '—'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filter and list */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <CardTitle>Deleted Items</CardTitle>
          <Select
            value={itemTypeFilter}
            onValueChange={(value) => setItemTypeFilter(value as typeof itemTypeFilter)}
          >
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="design">Designs</SelectItem>
              <SelectItem value="project">Projects</SelectItem>
              <SelectItem value="file">Files</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-center py-12">
              <Trash2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">Trash is empty</h3>
              <p className="text-muted-foreground mt-1">
                Deleted items will appear here
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Deleted</TableHead>
                  <TableHead>Expires In</TableHead>
                  <TableHead>Size</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TrashItemRow
                    key={`${item.item_type}-${item.id}`}
                    item={item}
                    onRestore={restoreItem}
                    onDelete={handleDelete}
                    isRestoring={isRestoring}
                    isDeleting={isDeleting}
                  />
                ))}
              </TableBody>
            </Table>
          )}

          {/* Pagination */}
          {total > 20 && (
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-muted-foreground">
                Showing {(page - 1) * 20 + 1} to {Math.min(page * 20, total)} of {total} items
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page * 20 >= total}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Empty Trash Dialog */}
      <Dialog open={showEmptyDialog} onOpenChange={setShowEmptyDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Empty Trash
            </DialogTitle>
            <DialogDescription>
              This will permanently delete all {total} item{total !== 1 ? 's' : ''} in your trash.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEmptyDialog(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={handleEmptyTrash}
              disabled={isEmptying}
            >
              {isEmptying ? 'Deleting...' : 'Empty Trash'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Single Item Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Permanently Delete
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to permanently delete "{itemToDelete?.name}"?
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button 
              variant="destructive" 
              onClick={confirmDelete}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete Permanently'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog open={showSettingsDialog} onOpenChange={setShowSettingsDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Trash Settings
            </DialogTitle>
            <DialogDescription>
              Configure how long items stay in trash before permanent deletion.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 py-4">
            {/* Retention Period */}
            <div className="space-y-3">
              <Label>Retention Period: {settings?.retention_days || 30} days</Label>
              <Slider
                defaultValue={[settings?.retention_days || 30]}
                min={7}
                max={90}
                step={1}
                onValueCommit={(value: number[]) => updateSettings({ retention_days: value[0] })}
              />
              <p className="text-sm text-muted-foreground">
                Items will be permanently deleted after this many days in trash.
              </p>
            </div>

            {/* Auto Empty */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Auto-empty trash</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically delete items when they expire
                </p>
              </div>
              <Switch
                checked={settings?.auto_empty ?? true}
                onCheckedChange={(checked: boolean) => updateSettings({ auto_empty: checked })}
              />
            </div>

            {/* Info */}
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Email Notifications</AlertTitle>
              <AlertDescription>
                You'll receive email reminders 7, 3, and 1 day before items are permanently deleted.
              </AlertDescription>
            </Alert>
          </div>

          <DialogFooter>
            <Button onClick={() => setShowSettingsDialog(false)}>
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
