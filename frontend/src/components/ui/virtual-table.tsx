/**
 * Virtual Table Component
 * 
 * Provides efficient rendering of large datasets using virtual scrolling.
 * Only renders visible rows plus a small buffer.
 */

import { useVirtualizer } from '@tanstack/react-virtual';
import { useRef, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface Column<T> {
  key: string;
  header: string;
  width?: string;
  render: (item: T, index: number) => ReactNode;
}

interface VirtualTableProps<T> {
  data: T[];
  columns: Column<T>[];
  rowHeight?: number;
  className?: string;
  maxHeight?: number;
  emptyMessage?: string;
  onRowClick?: (item: T, index: number) => void;
  rowClassName?: (item: T, index: number) => string;
}

/**
 * Virtual scrolling table for efficient rendering of large lists.
 * 
 * @example
 * ```tsx
 * <VirtualTable
 *   data={users}
 *   columns={[
 *     { key: 'name', header: 'Name', render: (user) => user.name },
 *     { key: 'email', header: 'Email', render: (user) => user.email },
 *   ]}
 *   maxHeight={500}
 * />
 * ```
 */
export function VirtualTable<T>({
  data,
  columns,
  rowHeight = 52,
  className,
  maxHeight = 600,
  emptyMessage = 'No data available',
  onRowClick,
  rowClassName,
}: VirtualTableProps<T>) {
  const parentRef = useRef<HTMLDivElement>(null);

  const rowVirtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => rowHeight,
    overscan: 5,
  });

  const virtualItems = rowVirtualizer.getVirtualItems();

  // Fallback for when virtualizer hasn't initialized yet (e.g., in tests)
  // Calculate how many items would fit in the viewport plus overscan
  const visibleCount = virtualItems.length > 0 
    ? virtualItems.length 
    : Math.min(data.length, Math.ceil(maxHeight / rowHeight) + 10);
  
  // Items to render - either virtual items or fallback slice
  const itemsToRender = virtualItems.length > 0 
    ? virtualItems 
    : data.slice(0, visibleCount).map((_, index) => ({
        key: index,
        index,
        start: index * rowHeight,
        size: rowHeight,
        end: (index + 1) * rowHeight,
        lane: 0,
      }));

  if (data.length === 0) {
    return (
      <div className={cn('border rounded-lg dark:border-gray-700', className)}>
        <table className="w-full">
          <thead>
            <tr className="border-b dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
              {columns.map((column) => (
                <th
                  key={column.key}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  style={{ width: column.width }}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
        </table>
        <div className="flex items-center justify-center h-32 text-gray-500 dark:text-gray-400">
          {emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('border rounded-lg dark:border-gray-700 overflow-hidden', className)}>
      {/* Fixed header */}
      <div className="bg-gray-50 dark:bg-gray-800 border-b dark:border-gray-700">
        <table className="w-full table-fixed">
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider"
                  style={{ width: column.width }}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
        </table>
      </div>

      {/* Scrollable body */}
      <div
        ref={parentRef}
        className="overflow-auto"
        style={{ maxHeight }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          <table className="w-full table-fixed" style={{ position: 'absolute', top: 0, left: 0 }}>
            <tbody>
              {itemsToRender.map((virtualRow) => {
                const item = data[virtualRow.index];
                const rowClasses = rowClassName?.(item, virtualRow.index) || '';
                
                return (
                  <tr
                    key={virtualRow.key}
                    data-index={virtualRow.index}
                    className={cn(
                      'border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors',
                      onRowClick && 'cursor-pointer',
                      rowClasses
                    )}
                    style={{
                      height: `${rowHeight}px`,
                      transform: `translateY(${virtualRow.start}px)`,
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      display: 'table',
                      tableLayout: 'fixed',
                    }}
                    onClick={() => onRowClick?.(item, virtualRow.index)}
                  >
                    {columns.map((column) => (
                      <td
                        key={column.key}
                        className="px-4 py-3 text-sm text-gray-900 dark:text-gray-100"
                        style={{ width: column.width }}
                      >
                        {column.render(item, virtualRow.index)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook for virtual list rendering (for custom implementations)
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useVirtualList<T>(
  data: T[],
  options: {
    parentRef: React.RefObject<HTMLElement>;
    estimateSize?: number;
    overscan?: number;
  }
) {
  const virtualizer = useVirtualizer({
    count: data.length,
    getScrollElement: () => options.parentRef.current,
    estimateSize: () => options.estimateSize ?? 50,
    overscan: options.overscan ?? 5,
  });

  return {
    virtualizer,
    virtualItems: virtualizer.getVirtualItems(),
    totalSize: virtualizer.getTotalSize(),
  };
}

export default VirtualTable;
