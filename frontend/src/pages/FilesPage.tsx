/**
 * Files Page - File Manager with Grid/List View and Version History.
 */

import {
  Grid3X3,
  List,
  Search,
  SortAsc,
  SortDesc,
  Trash2,
  Clock,
  FileBox,
  MoreVertical,
  Upload,
  RefreshCw,
  FolderOpen,
  X,
  Globe,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { PublishToMarketplaceDialog } from '@/components/marketplace/PublishToMarketplaceDialog';
import { FileUploader } from '@/components/upload/FileUploader';
import { useAuth } from '@/contexts/AuthContext';
import type { DesignFile } from '@/types';
import { VersionHistoryPanel } from './VersionHistoryPanel';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

type ViewMode = 'grid' | 'list';
type SortField = 'name' | 'created_at' | 'updated_at' | 'size';
type SortOrder = 'asc' | 'desc';

interface FilesPageProps {
  projectId?: string;
}

export function FilesPage({ projectId }: FilesPageProps) {
  const { token } = useAuth();
  
  // View state
  const [viewMode, setViewMode] = useState<ViewMode>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>('updated_at');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');
  const [filterTags] = useState<string[]>([]);
  
  // Data state
  const [files, setFiles] = useState<DesignFile[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Selection state
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [activeFile, setActiveFile] = useState<DesignFile | null>(null);
  
  // UI state
  const [showUploader, setShowUploader] = useState(false);
  const [showVersionHistory, setShowVersionHistory] = useState(false);
  const [showPublishDialog, setShowPublishDialog] = useState(false);
  const [fileToPublish, setFileToPublish] = useState<DesignFile | null>(null);

  // Fetch files
  const fetchFiles = useCallback(async () => {
    if (!token) return;

    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        sort_by: sortField,
        sort_order: sortOrder,
      });
      
      if (searchQuery) {
        params.append('search', searchQuery);
      }
      if (projectId) {
        params.append('project_id', projectId);
      }
      if (filterTags.length > 0) {
        filterTags.forEach(tag => params.append('tags', tag));
      }

      const response = await fetch(`${API_BASE}/files?${params}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch files');
      }

      const data = await response.json();
      setFiles(data.files || data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
    } finally {
      setIsLoading(false);
    }
  }, [token, sortField, sortOrder, searchQuery, projectId, filterTags]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  // Toggle file selection
  const toggleSelection = useCallback((fileId: string) => {
    setSelectedFiles(prev => {
      const next = new Set(prev);
      if (next.has(fileId)) {
        next.delete(fileId);
      } else {
        next.add(fileId);
      }
      return next;
    });
  }, []);

  // Select all files
  const selectAll = useCallback(() => {
    if (selectedFiles.size === files.length) {
      setSelectedFiles(new Set());
    } else {
      setSelectedFiles(new Set(files.map(f => f.id)));
    }
  }, [files, selectedFiles.size]);

  // Delete selected files
  const deleteSelected = useCallback(async () => {
    if (!token || selectedFiles.size === 0) return;

    const confirmed = window.confirm(
      `Delete ${selectedFiles.size} file(s)? This action cannot be undone.`
    );
    
    if (!confirmed) return;

    try {
      await Promise.all(
        Array.from(selectedFiles).map(id =>
          fetch(`${API_BASE}/files/${id}`, {
            method: 'DELETE',
            headers: { Authorization: `Bearer ${token}` },
          })
        )
      );
      setSelectedFiles(new Set());
      fetchFiles();
    } catch (err) {
      console.error('Failed to delete files:', err);
    }
  }, [token, selectedFiles, fetchFiles]);

  // Toggle sort
  const toggleSort = useCallback((field: SortField) => {
    if (sortField === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortOrder('asc');
    }
  }, [sortField]);

  // Open version history
  const openVersionHistory = useCallback((file: DesignFile) => {
    setActiveFile(file);
    setShowVersionHistory(true);
  }, []);

  // Open publish dialog
  const openPublishDialog = useCallback((file: DesignFile) => {
    setFileToPublish(file);
    setShowPublishDialog(true);
  }, []);

  // Format file size
  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Format date
  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b dark:border-gray-700 bg-white dark:bg-gray-800 px-6 py-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Files</h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {files.length} file{files.length !== 1 ? 's' : ''}
              {selectedFiles.size > 0 && ` • ${selectedFiles.size} selected`}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowUploader(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Upload className="w-4 h-4" />
              Upload
            </button>
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex items-center gap-4 mt-4">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search files..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
            />
          </div>

          {/* View toggle */}
          <div className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <button
              onClick={() => setViewMode('grid')}
              className={`p-2 ${viewMode === 'grid' ? 'bg-gray-100 dark:bg-gray-700 text-blue-600' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
              title="Grid view"
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`p-2 ${viewMode === 'list' ? 'bg-gray-100 dark:bg-gray-700 text-blue-600' : 'text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'}`}
              title="List view"
            >
              <List className="w-4 h-4" />
            </button>
          </div>

          {/* Refresh */}
          <button
            onClick={fetchFiles}
            disabled={isLoading}
            className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          {/* Bulk actions */}
          {selectedFiles.size > 0 && (
            <div className="flex items-center gap-2 pl-4 border-l">
              <button
                onClick={deleteSelected}
                className="p-2 text-red-500 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                title="Delete selected"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-6">
        {isLoading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="w-8 h-8 text-gray-400 animate-spin" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <p className="text-red-500 mb-4">{error}</p>
            <button
              onClick={fetchFiles}
              className="px-4 py-2 text-blue-600 hover:text-blue-700"
            >
              Try again
            </button>
          </div>
        ) : files.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center">
            <FolderOpen className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">No files yet</h3>
            <p className="text-gray-500 dark:text-gray-400 mb-4">Upload your first CAD file to get started</p>
            <button
              onClick={() => setShowUploader(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <Upload className="w-4 h-4" />
              Upload File
            </button>
          </div>
        ) : viewMode === 'grid' ? (
          <FileGrid
            files={files}
            selectedFiles={selectedFiles}
            onToggleSelect={toggleSelection}
            onOpenVersionHistory={openVersionHistory}
            onPublish={openPublishDialog}
            formatDate={formatDate}
          />
        ) : (
          <FileList
            files={files}
            selectedFiles={selectedFiles}
            sortField={sortField}
            sortOrder={sortOrder}
            onToggleSort={toggleSort}
            onToggleSelect={toggleSelection}
            onSelectAll={selectAll}
            onOpenVersionHistory={openVersionHistory}
            onPublish={openPublishDialog}
            formatSize={formatSize}
            formatDate={formatDate}
          />
        )}
      </div>

      {/* Upload Modal */}
      {showUploader && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Upload Files</h2>
              <button
                onClick={() => setShowUploader(false)}
                className="p-1 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <FileUploader
              onUploadComplete={() => {
                setShowUploader(false);
                fetchFiles();
              }}
            />
          </div>
        </div>
      )}

      {/* Version History Panel */}
      {showVersionHistory && activeFile && (
        <VersionHistoryPanel
          designId={activeFile.id}
          designName={activeFile.name}
          onClose={() => {
            setShowVersionHistory(false);
            setActiveFile(null);
          }}
        />
      )}

      {/* Publish to Marketplace Dialog */}
      {fileToPublish && (
        <PublishToMarketplaceDialog
          isOpen={showPublishDialog}
          onClose={() => {
            setShowPublishDialog(false);
            setFileToPublish(null);
          }}
          designId={fileToPublish.id}
          designName={fileToPublish.name}
          onPublished={() => {
            fetchFiles();
          }}
        />
      )}
    </div>
  );
}


// =============================================================================
// Grid View Component
// =============================================================================

interface FileGridProps {
  files: DesignFile[];
  selectedFiles: Set<string>;
  onToggleSelect: (id: string) => void;
  onOpenVersionHistory: (file: DesignFile) => void;
  onPublish: (file: DesignFile) => void;
  formatDate: (date: string) => string;
}

function FileGrid({
  files,
  selectedFiles,
  onToggleSelect,
  onOpenVersionHistory,
  onPublish,
  formatDate,
}: FileGridProps) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  
  return (
    <div data-testid="file-list" className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 file-grid">
      {files.map(file => (
        <div
          key={file.id}
          data-testid="file-item"
          className={`group relative bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden hover:shadow-md transition-shadow cursor-pointer file-card ${
            selectedFiles.has(file.id) ? 'ring-2 ring-blue-500' : ''
          }`}
        >
          {/* Action menu button */}
          <div className="absolute top-2 right-2 z-10">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setOpenMenuId(openMenuId === file.id ? null : file.id);
              }}
              className="p-1 bg-white/80 dark:bg-gray-800/80 rounded-full opacity-0 group-hover:opacity-100 transition-opacity hover:bg-white dark:hover:bg-gray-700"
            >
              <MoreVertical className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </button>
            
            {/* Dropdown menu */}
            {openMenuId === file.id && (
              <div className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-1 z-20">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onPublish(file);
                    setOpenMenuId(null);
                  }}
                  className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                  data-testid="publish-menu-item"
                >
                  <Globe className="w-4 h-4" />
                  Publish
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onOpenVersionHistory(file);
                    setOpenMenuId(null);
                  }}
                  className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                >
                  <Clock className="w-4 h-4" />
                  Version History
                </button>
              </div>
            )}
          </div>

          {/* Thumbnail */}
          <div
            className="aspect-square bg-gray-100 dark:bg-gray-700 relative"
            onClick={() => onOpenVersionHistory(file)}
          >
            {file.thumbnail_url ? (
              <img
                src={file.thumbnail_url}
                alt={file.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <FileBox className="w-12 h-12 text-gray-300" />
              </div>
            )}

            {/* Selection checkbox */}
            <div
              className={`absolute top-2 left-2 ${
                selectedFiles.has(file.id) || 'opacity-0 group-hover:opacity-100'
              } transition-opacity`}
              onClick={e => {
                e.stopPropagation();
                onToggleSelect(file.id);
              }}
            >
              <input
                type="checkbox"
                checked={selectedFiles.has(file.id)}
                onChange={() => onToggleSelect(file.id)}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </div>

            {/* Version badge */}
            {file.versions_count > 1 && (
              <div className="absolute bottom-2 right-2 bg-black/70 text-white text-xs px-1.5 py-0.5 rounded">
                v{file.versions_count}
              </div>
            )}
          </div>

          {/* Info */}
          <div className="p-3">
            <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate" title={file.name}>
              {file.name}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {formatDate(file.updated_at)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}


// =============================================================================
// List View Component
// =============================================================================

interface FileListProps {
  files: DesignFile[];
  selectedFiles: Set<string>;
  sortField: SortField;
  sortOrder: SortOrder;
  onToggleSort: (field: SortField) => void;
  onToggleSelect: (id: string) => void;
  onSelectAll: () => void;
  onOpenVersionHistory: (file: DesignFile) => void;
  onPublish: (file: DesignFile) => void;
  formatSize: (bytes: number) => string;
  formatDate: (date: string) => string;
}

function FileList({
  files,
  selectedFiles,
  sortField,
  sortOrder,
  onToggleSort,
  onToggleSelect,
  onSelectAll,
  onOpenVersionHistory,
  onPublish,
  formatSize: _formatSize,
  formatDate,
}: FileListProps) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const SortIcon = sortOrder === 'asc' ? SortAsc : SortDesc;

  const headerClass = "px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-600";

  return (
    <div data-testid="file-list" className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-700">
          <tr>
            <th className="px-4 py-3 w-10">
              <input
                type="checkbox"
                checked={selectedFiles.size === files.length && files.length > 0}
                onChange={onSelectAll}
                className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
            </th>
            <th 
              className={headerClass}
              onClick={() => onToggleSort('name')}
            >
              <span className="flex items-center gap-1">
                Name
                {sortField === 'name' && <SortIcon className="w-3 h-3" />}
              </span>
            </th>
            <th className={headerClass}>Type</th>
            <th 
              className={headerClass}
              onClick={() => onToggleSort('updated_at')}
            >
              <span className="flex items-center gap-1">
                Modified
                {sortField === 'updated_at' && <SortIcon className="w-3 h-3" />}
              </span>
            </th>
            <th className={headerClass}>Versions</th>
            <th className="px-4 py-3 w-10"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
          {files.map(file => (
            <tr
              key={file.id}
              data-testid="file-item"
              className={`hover:bg-gray-50 dark:hover:bg-gray-700 ${
                selectedFiles.has(file.id) ? 'bg-blue-50 dark:bg-blue-900/30' : ''
              }`}
            >
              <td className="px-4 py-3">
                <input
                  type="checkbox"
                  checked={selectedFiles.has(file.id)}
                  onChange={() => onToggleSelect(file.id)}
                  className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </td>
              <td 
                className="px-4 py-3 cursor-pointer"
                onClick={() => onOpenVersionHistory(file)}
              >
                <div className="flex items-center gap-3">
                  {file.thumbnail_url ? (
                    <img
                      src={file.thumbnail_url}
                      alt=""
                      className="w-10 h-10 rounded object-cover"
                    />
                  ) : (
                    <div className="w-10 h-10 bg-gray-100 dark:bg-gray-700 rounded flex items-center justify-center">
                      <FileBox className="w-5 h-5 text-gray-400" />
                    </div>
                  )}
                  <div>
                    <p className="font-medium text-gray-900 dark:text-gray-100">{file.name}</p>
                    {file.description && (
                      <p className="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                        {file.description}
                      </p>
                    )}
                  </div>
                </div>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                {file.source_type.replace('_', ' ')}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                {formatDate(file.updated_at)}
              </td>
              <td className="px-4 py-3">
                <button
                  onClick={() => onOpenVersionHistory(file)}
                  className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600"
                >
                  <Clock className="w-3.5 h-3.5" />
                  {file.versions_count}
                </button>
              </td>
              <td className="px-4 py-3 relative">
                <button 
                  onClick={() => setOpenMenuId(openMenuId === file.id ? null : file.id)}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <MoreVertical className="w-4 h-4" />
                </button>
                
                {/* Dropdown menu */}
                {openMenuId === file.id && (
                  <div className="absolute right-0 top-full mt-1 w-40 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-1 z-20">
                    <button
                      onClick={() => {
                        onPublish(file);
                        setOpenMenuId(null);
                      }}
                      className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                      data-testid="publish-menu-item"
                    >
                      <Globe className="w-4 h-4" />
                      Publish
                    </button>
                    <button
                      onClick={() => {
                        onOpenVersionHistory(file);
                        setOpenMenuId(null);
                      }}
                      className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700"
                    >
                      <Clock className="w-4 h-4" />
                      Version History
                    </button>
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default FilesPage;
