/**
 * BOM Table Component
 * 
 * Interactive Bill of Materials table with inline editing,
 * sorting, and export functionality.
 */

import { useState, useMemo, useCallback } from 'react';
import {
  Plus,
  Trash2,
  Download,
  Edit2,
  Check,
  X,
  ChevronUp,
  ChevronDown,
  DollarSign,
  Package,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface BOMItem {
  id: string;
  component_id: string;
  component_name: string;
  part_number: string | null;
  vendor_part_number: string | null;
  description: string;
  category: string;
  vendor_id: string | null;
  vendor_name: string | null;
  quantity: number;
  unit_cost: number | null;
  total_cost: number | null;
  currency: string;
  lead_time_days: number | null;
  minimum_order_quantity: number;
  in_stock: boolean | null;
  notes: string | null;
}

interface BOMSummary {
  total_items: number;
  total_quantity: number;
  total_cost: number | null;
  currency: string;
  categories: Record<string, number>;
  longest_lead_time: number | null;
}

interface Vendor {
  id: string;
  name: string;
  display_name: string;
}

interface BOMTableProps {
  assemblyId: string;
  items: BOMItem[];
  summary: BOMSummary;
  vendors: Vendor[];
  onItemUpdate?: (itemId: string, data: Partial<BOMItem>) => void;
  onItemDelete?: (itemId: string) => void;
  onItemAdd?: () => void;
  onRefresh?: () => void;
  className?: string;
}

type SortField = 'part_number' | 'description' | 'category' | 'quantity' | 'unit_cost' | 'total_cost' | 'lead_time_days';
type SortDirection = 'asc' | 'desc';

// =============================================================================
// Inline Edit Cell
// =============================================================================

interface EditableCellProps {
  value: string | number | null;
  type?: 'text' | 'number';
  onSave: (value: string | number | null) => void;
  className?: string;
  placeholder?: string;
}

function EditableCell({
  value,
  type = 'text',
  onSave,
  className = '',
  placeholder = '',
}: EditableCellProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(String(value ?? ''));

  const handleSave = () => {
    const newValue = type === 'number' 
      ? (editValue ? parseFloat(editValue) : null)
      : (editValue || null);
    onSave(newValue);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(String(value ?? ''));
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="flex items-center gap-1">
        <input
          type={type}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSave();
            if (e.key === 'Escape') handleCancel();
          }}
          className="w-full px-2 py-1 text-sm border border-primary-300 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
          autoFocus
        />
        <button onClick={handleSave} className="p-1 text-green-600 hover:text-green-700">
          <Check className="w-4 h-4" />
        </button>
        <button onClick={handleCancel} className="p-1 text-gray-400 hover:text-gray-600">
          <X className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <div
      className={`group cursor-pointer hover:bg-gray-50 rounded px-2 py-1 -mx-2 -my-1 ${className}`}
      onClick={() => setIsEditing(true)}
    >
      <span className={value ? '' : 'text-gray-400 italic'}>
        {value ?? placeholder}
      </span>
      <Edit2 className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 inline ml-2" />
    </div>
  );
}

// =============================================================================
// Category Badge
// =============================================================================

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  custom: { bg: 'bg-purple-100', text: 'text-purple-700' },
  printed: { bg: 'bg-blue-100', text: 'text-blue-700' },
  fastener: { bg: 'bg-gray-100', text: 'text-gray-700' },
  electronic: { bg: 'bg-green-100', text: 'text-green-700' },
  mechanical: { bg: 'bg-orange-100', text: 'text-orange-700' },
  hardware: { bg: 'bg-yellow-100', text: 'text-yellow-700' },
};

function CategoryBadge({ category }: { category: string }) {
  const colors = CATEGORY_COLORS[category] || { bg: 'bg-gray-100', text: 'text-gray-700' };
  return (
    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colors.bg} ${colors.text}`}>
      {category}
    </span>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function BOMTable({
  assemblyId,
  items,
  summary,
  vendors: _vendors,
  onItemUpdate,
  onItemDelete,
  onItemAdd,
  onRefresh: _onRefresh,
  className = '',
}: BOMTableProps) {
  const { token } = useAuth();

  const [sortField, setSortField] = useState<SortField>('category');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [isExporting, setIsExporting] = useState(false);

  // Sort and filter items
  const displayedItems = useMemo(() => {
    let filtered = items;

    // Filter by category
    if (filterCategory) {
      filtered = filtered.filter((item) => item.category === filterCategory);
    }

    // Sort
    return [...filtered].sort((a, b) => {
      const aVal = a[sortField];
      const bVal = b[sortField];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      const compare = typeof aVal === 'string'
        ? aVal.localeCompare(String(bVal))
        : Number(aVal) - Number(bVal);

      return sortDirection === 'asc' ? compare : -compare;
    });
  }, [items, sortField, sortDirection, filterCategory]);

  // Categories for filter
  const categories = useMemo(() => {
    return Object.keys(summary.categories);
  }, [summary.categories]);

  // Handle sort
  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Sort indicator
  const SortIndicator = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? (
      <ChevronUp className="w-4 h-4" />
    ) : (
      <ChevronDown className="w-4 h-4" />
    );
  };

  // Export CSV
  const handleExportCSV = useCallback(async () => {
    if (!token) return;

    setIsExporting(true);
    try {
      const response = await fetch(`${API_BASE}/assemblies/${assemblyId}/bom/export/csv`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `BOM_${assemblyId}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  }, [assemblyId, token]);

  // Format currency
  const formatCurrency = (value: number | null, currency: string = 'USD') => {
    if (value === null) return '-';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(value);
  };

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h3 className="font-semibold text-gray-900">Bill of Materials</h3>
          
          {/* Category filter */}
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-2 py-1"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat} ({summary.categories[cat]})
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          {onItemAdd && (
            <button
              onClick={onItemAdd}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <Plus className="w-4 h-4" />
              Add Item
            </button>
          )}
          
          <button
            onClick={handleExportCSV}
            disabled={isExporting}
            className="flex items-center gap-1 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            {isExporting ? 'Exporting...' : 'Export CSV'}
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="px-4 py-3 border-b border-gray-100 grid grid-cols-4 gap-4">
        <div className="flex items-center gap-2">
          <Package className="w-5 h-5 text-gray-400" />
          <div>
            <p className="text-sm text-gray-500">Items</p>
            <p className="font-semibold">{summary.total_items}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Package className="w-5 h-5 text-gray-400" />
          <div>
            <p className="text-sm text-gray-500">Total Qty</p>
            <p className="font-semibold">{summary.total_quantity}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-gray-400" />
          <div>
            <p className="text-sm text-gray-500">Total Cost</p>
            <p className="font-semibold">
              {formatCurrency(summary.total_cost, summary.currency)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-400" />
          <div>
            <p className="text-sm text-gray-500">Max Lead Time</p>
            <p className="font-semibold">
              {summary.longest_lead_time ? `${summary.longest_lead_time} days` : '-'}
            </p>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 text-left text-sm text-gray-600">
              <th className="px-4 py-3 font-medium">#</th>
              <th
                className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('part_number')}
              >
                <div className="flex items-center gap-1">
                  Part Number
                  <SortIndicator field="part_number" />
                </div>
              </th>
              <th
                className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('description')}
              >
                <div className="flex items-center gap-1">
                  Description
                  <SortIndicator field="description" />
                </div>
              </th>
              <th
                className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('category')}
              >
                <div className="flex items-center gap-1">
                  Category
                  <SortIndicator field="category" />
                </div>
              </th>
              <th
                className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100 text-right"
                onClick={() => handleSort('quantity')}
              >
                <div className="flex items-center justify-end gap-1">
                  Qty
                  <SortIndicator field="quantity" />
                </div>
              </th>
              <th
                className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100 text-right"
                onClick={() => handleSort('unit_cost')}
              >
                <div className="flex items-center justify-end gap-1">
                  Unit Cost
                  <SortIndicator field="unit_cost" />
                </div>
              </th>
              <th
                className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100 text-right"
                onClick={() => handleSort('total_cost')}
              >
                <div className="flex items-center justify-end gap-1">
                  Total
                  <SortIndicator field="total_cost" />
                </div>
              </th>
              <th className="px-4 py-3 font-medium">Vendor</th>
              <th
                className="px-4 py-3 font-medium cursor-pointer hover:bg-gray-100 text-right"
                onClick={() => handleSort('lead_time_days')}
              >
                <div className="flex items-center justify-end gap-1">
                  Lead Time
                  <SortIndicator field="lead_time_days" />
                </div>
              </th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {displayedItems.length === 0 ? (
              <tr>
                <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                  <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  No BOM items found
                </td>
              </tr>
            ) : (
              displayedItems.map((item, index) => (
                <tr key={item.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-500">{index + 1}</td>
                  <td className="px-4 py-3 text-sm">
                    <EditableCell
                      value={item.part_number}
                      onSave={(value) => onItemUpdate?.(item.id, { part_number: value as string })}
                      placeholder="—"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm max-w-xs">
                    <div className="truncate" title={item.description}>
                      {item.description}
                    </div>
                    <div className="text-xs text-gray-400">{item.component_name}</div>
                  </td>
                  <td className="px-4 py-3">
                    <CategoryBadge category={item.category} />
                  </td>
                  <td className="px-4 py-3 text-sm text-right">
                    <EditableCell
                      value={item.quantity}
                      type="number"
                      onSave={(value) => onItemUpdate?.(item.id, { quantity: value as number })}
                    />
                  </td>
                  <td className="px-4 py-3 text-sm text-right">
                    <EditableCell
                      value={item.unit_cost}
                      type="number"
                      onSave={(value) => onItemUpdate?.(item.id, { unit_cost: value as number })}
                      placeholder="—"
                    />
                  </td>
                  <td className="px-4 py-3 text-sm text-right font-medium">
                    {formatCurrency(item.total_cost, item.currency)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {item.vendor_name || '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-right">
                    {item.lead_time_days ? `${item.lead_time_days}d` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {item.in_stock === true && (
                      <span className="text-xs px-2 py-0.5 bg-green-100 text-green-700 rounded-full">
                        In Stock
                      </span>
                    )}
                    {item.in_stock === false && (
                      <span className="text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full">
                        Out of Stock
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {onItemDelete && (
                      <button
                        onClick={() => onItemDelete(item.id)}
                        className="p-1 text-gray-400 hover:text-red-600 rounded"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer with totals */}
      <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
        <span className="text-sm text-gray-600">
          Showing {displayedItems.length} of {items.length} items
        </span>
        <div className="text-right">
          <span className="text-sm text-gray-600">Grand Total: </span>
          <span className="font-semibold text-gray-900">
            {formatCurrency(summary.total_cost, summary.currency)}
          </span>
        </div>
      </div>
    </div>
  );
}

export default BOMTable;
