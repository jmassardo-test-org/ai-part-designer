/**
 * Version History Panel - Slide-out panel showing design version history.
 */

import {
  X,
  Clock,
  Download,
  RotateCcw,
  GitCompare,
  ChevronDown,
  ChevronUp,
  Check,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import type { DesignVersion } from '@/types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

interface VersionHistoryPanelProps {
  designId: string;
  designName: string;
  onClose: () => void;
  onVersionRestore?: (newVersion: DesignVersion) => void;
}

export function VersionHistoryPanel({
  designId,
  designName,
  onClose,
  onVersionRestore,
}: VersionHistoryPanelProps) {
  const { token } = useAuth();
  
  const [versions, setVersions] = useState<DesignVersion[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [selectedVersions, setSelectedVersions] = useState<Set<string>>(new Set());
  const [restoringVersionId, setRestoringVersionId] = useState<string | null>(null);
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);
  const [showCompare, setShowCompare] = useState(false);

  // Fetch version history
  const fetchVersions = useCallback(async () => {
    if (!token) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE}/designs/${designId}/versions?page_size=50`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error('Failed to fetch version history');
      }

      const data = await response.json();
      setVersions(data.versions);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load versions');
    } finally {
      setIsLoading(false);
    }
  }, [token, designId]);

  useEffect(() => {
    fetchVersions();
  }, [fetchVersions]);

  // Restore version
  const restoreVersion = useCallback(async (versionId: string) => {
    if (!token) return;

    setRestoringVersionId(versionId);

    try {
      const response = await fetch(
        `${API_BASE}/versions/${versionId}/restore`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({}),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to restore version');
      }

      const result = await response.json();
      
      // Refresh version list
      await fetchVersions();
      
      // Notify parent
      if (onVersionRestore && versions.length > 0) {
        const newVersion = versions.find(v => v.id === result.new_version_id);
        if (newVersion) {
          onVersionRestore(newVersion);
        }
      }
    } catch (err) {
      console.error('Failed to restore version:', err);
    } finally {
      setRestoringVersionId(null);
    }
  }, [token, fetchVersions, onVersionRestore, versions]);

  // Toggle version selection for comparison
  const toggleVersionSelection = useCallback((versionId: string) => {
    setSelectedVersions(prev => {
      const next = new Set(prev);
      if (next.has(versionId)) {
        next.delete(versionId);
      } else if (next.size < 2) {
        next.add(versionId);
      }
      return next;
    });
  }, []);

  // Format date
  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Format geometry info
  const formatGeometry = (info: DesignVersion['geometry_info']): string => {
    const parts = [];
    if (info.volume) {
      parts.push(`${info.volume.toFixed(1)} mm³`);
    }
    if (info.bounding_box) {
      const { x, y, z } = info.bounding_box;
      parts.push(`${x.toFixed(1)} × ${y.toFixed(1)} × ${z.toFixed(1)} mm`);
    }
    return parts.join(' • ') || 'No geometry data';
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/30" 
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-md bg-white shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex-shrink-0 border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                Version History
              </h2>
              <p className="text-sm text-gray-500 mt-0.5 truncate">
                {designName}
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-gray-500 hover:text-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Compare button */}
          {selectedVersions.size === 2 && (
            <button
              onClick={() => setShowCompare(true)}
              className="mt-3 w-full inline-flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              <GitCompare className="w-4 h-4" />
              Compare Selected Versions
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto">
          {isLoading ? (
            <div className="flex items-center justify-center h-48">
              <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-48 text-center px-6">
              <AlertCircle className="w-8 h-8 text-red-400 mb-2" />
              <p className="text-red-500">{error}</p>
              <button
                onClick={fetchVersions}
                className="mt-3 text-blue-600 hover:text-blue-700"
              >
                Try again
              </button>
            </div>
          ) : versions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center px-6">
              <Clock className="w-8 h-8 text-gray-300 mb-2" />
              <p className="text-gray-500">No version history available</p>
            </div>
          ) : (
            <div className="divide-y">
              {versions.map((version, index) => {
                const isLatest = index === 0;
                const isExpanded = expandedVersionId === version.id;
                const isSelected = selectedVersions.has(version.id);
                const isRestoring = restoringVersionId === version.id;

                return (
                  <div
                    key={version.id}
                    className={`px-6 py-4 ${isSelected ? 'bg-blue-50' : ''}`}
                  >
                    {/* Version header */}
                    <div className="flex items-start gap-3">
                      {/* Selection checkbox */}
                      <div className="pt-0.5">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleVersionSelection(version.id)}
                          disabled={selectedVersions.size >= 2 && !isSelected}
                          className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                        />
                      </div>

                      {/* Version info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">
                            Version {version.version_number}
                          </span>
                          {isLatest && (
                            <span className="text-xs px-1.5 py-0.5 bg-green-100 text-green-700 rounded">
                              Current
                            </span>
                          )}
                        </div>

                        <p className="text-sm text-gray-500 mt-0.5">
                          {formatDate(version.created_at)}
                        </p>

                        {version.created_by_name && (
                          <p className="text-xs text-gray-400 mt-0.5">
                            by {version.created_by_name}
                          </p>
                        )}

                        {version.change_description && (
                          <p className="text-sm text-gray-600 mt-2 italic">
                            "{version.change_description}"
                          </p>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1">
                        {!isLatest && (
                          <button
                            onClick={() => restoreVersion(version.id)}
                            disabled={isRestoring}
                            className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50"
                            title="Restore this version"
                          >
                            {isRestoring ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <RotateCcw className="w-4 h-4" />
                            )}
                          </button>
                        )}

                        <a
                          href={version.file_url}
                          download
                          className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Download"
                        >
                          <Download className="w-4 h-4" />
                        </a>

                        <button
                          onClick={() => setExpandedVersionId(
                            isExpanded ? null : version.id
                          )}
                          className="p-1.5 text-gray-500 hover:text-gray-700 rounded-lg transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Expanded details */}
                    {isExpanded && (
                      <div className="mt-3 pt-3 border-t border-gray-100 ml-7">
                        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                          <dt className="text-gray-500">Geometry</dt>
                          <dd className="text-gray-900">
                            {formatGeometry(version.geometry_info)}
                          </dd>

                          {Object.keys(version.file_formats).length > 0 && (
                            <>
                              <dt className="text-gray-500">Formats</dt>
                              <dd className="text-gray-900">
                                {Object.keys(version.file_formats).join(', ').toUpperCase()}
                              </dd>
                            </>
                          )}

                          {Object.keys(version.parameters).length > 0 && (
                            <>
                              <dt className="text-gray-500 col-span-2 mt-2 mb-1">
                                Parameters
                              </dt>
                              {Object.entries(version.parameters).map(([key, value]) => (
                                <div key={key} className="col-span-2 flex justify-between text-xs bg-gray-50 px-2 py-1 rounded">
                                  <span className="text-gray-500">{key}</span>
                                  <span className="text-gray-900 font-mono">
                                    {String(value)}
                                  </span>
                                </div>
                              ))}
                            </>
                          )}
                        </dl>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Compare modal */}
      {showCompare && selectedVersions.size === 2 && (
        <VersionCompareModal
          designId={designId}
          versionIds={Array.from(selectedVersions)}
          versions={versions}
          onClose={() => setShowCompare(false)}
        />
      )}
    </div>
  );
}


// =============================================================================
// Version Compare Modal
// =============================================================================

interface VersionCompareModalProps {
  designId: string;
  versionIds: string[];
  versions: DesignVersion[];
  onClose: () => void;
}

function VersionCompareModal({
  designId,
  versionIds,
  versions,
  onClose,
}: VersionCompareModalProps) {
  const { token } = useAuth();
  
  const [diff, setDiff] = useState<{
    parameter_changes: Array<{
      field: string;
      old_value: unknown;
      new_value: unknown;
      change_type: string;
    }>;
    geometry_changes: Array<{
      field: string;
      old_value: unknown;
      new_value: unknown;
      change_type: string;
    }>;
    summary: string;
  } | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Get version numbers from IDs
  const version1 = versions.find(v => v.id === versionIds[0]);
  const version2 = versions.find(v => v.id === versionIds[1]);

  useEffect(() => {
    if (!token || !version1 || !version2) return;

    const fetchDiff = async () => {
      try {
        const params = new URLSearchParams({
          from_version: String(version1.version_number),
          to_version: String(version2.version_number),
        });

        const response = await fetch(
          `${API_BASE}/designs/${designId}/versions/diff?${params}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.ok) {
          const data = await response.json();
          setDiff(data);
        }
      } catch (err) {
        console.error('Failed to fetch diff:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDiff();
  }, [token, designId, version1, version2]);

  if (!version1 || !version2) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <div>
            <h3 className="text-lg font-semibold">Compare Versions</h3>
            <p className="text-sm text-gray-500">
              v{version1.version_number} → v{version2.version_number}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          ) : diff ? (
            <div className="space-y-6">
              {/* Summary */}
              <div className="text-center py-3 px-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-600">{diff.summary}</p>
              </div>

              {/* Parameter changes */}
              {diff.parameter_changes.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">
                    Parameter Changes
                  </h4>
                  <div className="space-y-2">
                    {diff.parameter_changes.map((change, i) => (
                      <DiffRow key={i} change={change} />
                    ))}
                  </div>
                </div>
              )}

              {/* Geometry changes */}
              {diff.geometry_changes.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">
                    Geometry Changes
                  </h4>
                  <div className="space-y-2">
                    {diff.geometry_changes.map((change, i) => (
                      <DiffRow key={i} change={change} />
                    ))}
                  </div>
                </div>
              )}

              {/* No changes */}
              {diff.parameter_changes.length === 0 && 
               diff.geometry_changes.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <Check className="w-8 h-8 mx-auto mb-2 text-green-500" />
                  <p>No differences found between versions</p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-red-500">
              Failed to load comparison
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Diff row component
interface DiffRowProps {
  change: {
    field: string;
    old_value: unknown;
    new_value: unknown;
    change_type: string;
  };
}

function DiffRow({ change }: DiffRowProps) {
  const typeColors: Record<string, string> = {
    added: 'bg-green-50 border-green-200',
    removed: 'bg-red-50 border-red-200',
    modified: 'bg-yellow-50 border-yellow-200',
  };

  const typeLabels: Record<string, string> = {
    added: '+',
    removed: '-',
    modified: '~',
  };

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${typeColors[change.change_type] || ''}`}>
      <span className="font-mono text-sm font-bold text-gray-500">
        {typeLabels[change.change_type]}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900">{change.field}</p>
        <div className="mt-1 text-sm">
          {change.old_value !== null && (
            <span className="text-red-600 line-through mr-2">
              {String(change.old_value)}
            </span>
          )}
          {change.new_value !== null && (
            <span className="text-green-600">
              {String(change.new_value)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
