/**
 * Job Status Card Component.
 * 
 * Displays job status with progress bar, status icon,
 * and action buttons (cancel, retry, save).
 */

import { useState, useCallback } from 'react';
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  X,
  ChevronDown,
  ChevronUp,
  Save,
} from 'lucide-react';
import type { Job, JobStatus } from '@/types';
import { useAuth } from '@/contexts/AuthContext';
import { SaveDesignModal } from './SaveDesignModal';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

interface JobStatusCardProps {
  job: Job;
  onStatusChange?: (job: Job) => void;
  onCancel?: (jobId: string) => void;
  onRetry?: (jobId: string) => void;
  onSave?: (jobId: string, designId: string, projectId: string) => void;
  showDetails?: boolean;
  className?: string;
}

// Status configuration
const STATUS_CONFIG: Record<JobStatus, {
  icon: typeof Clock;
  color: string;
  bgColor: string;
  label: string;
}> = {
  pending: {
    icon: Clock,
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
    label: 'Pending',
  },
  queued: {
    icon: Clock,
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
    label: 'Queued',
  },
  processing: {
    icon: Loader2,
    color: 'text-yellow-500',
    bgColor: 'bg-yellow-50',
    label: 'Processing',
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-green-500',
    bgColor: 'bg-green-50',
    label: 'Completed',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    label: 'Failed',
  },
  cancelled: {
    icon: AlertCircle,
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
    label: 'Cancelled',
  },
};

// Format job type for display
function formatJobType(type: string): string {
  const labels: Record<string, string> = {
    generate: 'Generate Part',
    convert: 'Convert File',
    modify: 'Modify CAD',
    export: 'Export File',
    validate: 'Validate',
    thumbnail: 'Thumbnail',
  };
  return labels[type] || type;
}

// Format time difference
function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

// Format duration
function formatDuration(startDate: string, endDate?: string): string {
  const start = new Date(startDate);
  const end = endDate ? new Date(endDate) : new Date();
  const diff = Math.floor((end.getTime() - start.getTime()) / 1000);

  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ${diff % 60}s`;
  return `${Math.floor(diff / 3600)}h ${Math.floor((diff % 3600) / 60)}m`;
}

export function JobStatusCard({
  job,
  onStatusChange,
  onCancel,
  onRetry,
  onSave,
  showDetails = false,
  className = '',
}: JobStatusCardProps) {
  const { token } = useAuth();
  const [isExpanded, setIsExpanded] = useState(showDetails);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);

  const statusConfig = STATUS_CONFIG[job.status];
  const StatusIcon = statusConfig.icon;
  const isActive = job.status === 'processing' || job.status === 'queued';
  const canCancel = job.status === 'pending' || job.status === 'queued' || job.status === 'processing';
  const canRetry = job.status === 'failed' && job.retry_count < job.max_retries;
  // Can save if completed AI generation and not already saved
  const canSave = job.status === 'completed' && 
                  (job.type === 'generate' || job.type === 'ai_generation') && 
                  !job.design_id;

  // Handle cancel
  const handleCancel = useCallback(async () => {
    if (!token || isCancelling) return;

    setIsCancelling(true);
    try {
      const response = await fetch(`${API_BASE}/jobs/${job.id}/cancel`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const updatedJob = await response.json();
        onStatusChange?.(updatedJob);
        onCancel?.(job.id);
      }
    } catch (error) {
      console.error('Failed to cancel job:', error);
    } finally {
      setIsCancelling(false);
    }
  }, [job.id, token, isCancelling, onStatusChange, onCancel]);

  // Handle retry
  const handleRetry = useCallback(async () => {
    if (!token || isRetrying) return;

    setIsRetrying(true);
    try {
      const response = await fetch(`${API_BASE}/jobs/${job.id}/retry`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const updatedJob = await response.json();
        onStatusChange?.(updatedJob);
        onRetry?.(job.id);
      }
    } catch (error) {
      console.error('Failed to retry job:', error);
    } finally {
      setIsRetrying(false);
    }
  }, [job.id, token, isRetrying, onStatusChange, onRetry]);

  // Progress percentage
  const progress = job.progress?.percentage ?? 0;

  return (
    <div className={`rounded-lg border ${statusConfig.bgColor} ${className}`}>
      {/* Main content */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          {/* Left side: Status and info */}
          <div className="flex items-start gap-3 flex-1 min-w-0">
            {/* Status icon */}
            <div className={`p-2 rounded-full bg-white shadow-sm ${statusConfig.color}`}>
              <StatusIcon 
                className={`w-5 h-5 ${job.status === 'processing' ? 'animate-spin' : ''}`} 
              />
            </div>

            {/* Job info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900">
                  {formatJobType(job.type)}
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${statusConfig.color} ${statusConfig.bgColor}`}>
                  {statusConfig.label}
                </span>
              </div>

              {/* Progress bar for active jobs */}
              {isActive && job.progress && (
                <div className="mt-2">
                  <div className="flex justify-between text-xs text-gray-600 mb-1">
                    <span>{job.progress.stage || 'Processing...'}</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all duration-300"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Error message */}
              {job.status === 'failed' && job.error_message && (
                <p className="mt-1 text-sm text-red-600 truncate">
                  {job.error_message}
                </p>
              )}

              {/* Timing info */}
              <div className="mt-1 text-xs text-gray-500">
                {job.started_at && job.completed_at ? (
                  <span>Completed in {formatDuration(job.started_at, job.completed_at)}</span>
                ) : job.started_at ? (
                  <span>Running for {formatDuration(job.started_at)}</span>
                ) : (
                  <span>Created {formatTimeAgo(job.created_at)}</span>
                )}
              </div>
            </div>
          </div>

          {/* Right side: Actions */}
          <div className="flex items-center gap-2">
            {canSave && (
              <button
                onClick={() => setShowSaveModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
                title="Save design"
              >
                <Save className="w-4 h-4" />
                Save
              </button>
            )}

            {canRetry && (
              <button
                onClick={handleRetry}
                disabled={isRetrying}
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-white rounded-lg transition-colors disabled:opacity-50"
                title="Retry job"
              >
                <RefreshCw className={`w-4 h-4 ${isRetrying ? 'animate-spin' : ''}`} />
              </button>
            )}

            {canCancel && (
              <button
                onClick={handleCancel}
                disabled={isCancelling}
                className="p-2 text-gray-500 hover:text-red-600 hover:bg-white rounded-lg transition-colors disabled:opacity-50"
                title="Cancel job"
              >
                <X className={`w-4 h-4 ${isCancelling ? 'animate-pulse' : ''}`} />
              </button>
            )}

            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-white rounded-lg transition-colors"
              title={isExpanded ? 'Hide details' : 'Show details'}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-0">
          <div className="mt-2 pt-3 border-t border-gray-200/50">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              <dt className="text-gray-500">Job ID</dt>
              <dd className="text-gray-900 font-mono text-xs truncate">{job.id}</dd>

              <dt className="text-gray-500">Priority</dt>
              <dd className="text-gray-900">{job.priority}</dd>

              <dt className="text-gray-500">Retries</dt>
              <dd className="text-gray-900">{job.retry_count} / {job.max_retries}</dd>

              {job.started_at && (
                <>
                  <dt className="text-gray-500">Started</dt>
                  <dd className="text-gray-900">{new Date(job.started_at).toLocaleString()}</dd>
                </>
              )}

              {job.completed_at && (
                <>
                  <dt className="text-gray-500">Completed</dt>
                  <dd className="text-gray-900">{new Date(job.completed_at).toLocaleString()}</dd>
                </>
              )}

              {job.result?.geometry_info && (
                <>
                  <dt className="text-gray-500">Volume</dt>
                  <dd className="text-gray-900">
                    {job.result.geometry_info.volume?.toFixed(2)} mm³
                  </dd>

                  {job.result.geometry_info.bounding_box && (
                    <>
                      <dt className="text-gray-500">Size</dt>
                      <dd className="text-gray-900">
                        {job.result.geometry_info.bounding_box.x.toFixed(1)} × {' '}
                        {job.result.geometry_info.bounding_box.y.toFixed(1)} × {' '}
                        {job.result.geometry_info.bounding_box.z.toFixed(1)} mm
                      </dd>
                    </>
                  )}
                </>
              )}
            </dl>
          </div>
        </div>
      )}

      {/* Save Design Modal */}
      <SaveDesignModal
        job={job}
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        onSaved={(designId, projectId) => {
          setShowSaveModal(false);
          onSave?.(job.id, designId, projectId);
        }}
      />
    </div>
  );
}


/**
 * Compact job status indicator (for inline use).
 */
interface JobStatusBadgeProps {
  status: JobStatus;
  className?: string;
}

export function JobStatusBadge({ status, className = '' }: JobStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  const Icon = config.icon;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium ${config.color} ${config.bgColor} ${className}`}>
      <Icon className={`w-3 h-3 ${status === 'processing' ? 'animate-spin' : ''}`} />
      {config.label}
    </span>
  );
}


/**
 * Mini progress indicator for job status.
 */
interface JobProgressIndicatorProps {
  job: Job;
  size?: 'sm' | 'md';
}

export function JobProgressIndicator({ job, size = 'md' }: JobProgressIndicatorProps) {
  const isActive = job.status === 'processing' || job.status === 'queued';
  const progress = job.progress?.percentage ?? 0;
  const sizePx = size === 'sm' ? 20 : 32;
  const strokeWidth = size === 'sm' ? 2 : 3;
  const radius = (sizePx - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (progress / 100) * circumference;

  if (!isActive) {
    return <JobStatusBadge status={job.status} />;
  }

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={sizePx} height={sizePx} className="-rotate-90">
        {/* Background circle */}
        <circle
          cx={sizePx / 2}
          cy={sizePx / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          className="text-gray-200"
        />
        {/* Progress circle */}
        <circle
          cx={sizePx / 2}
          cy={sizePx / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="text-blue-500 transition-all duration-300"
        />
      </svg>
      <span className="absolute text-[8px] font-medium text-gray-600">
        {progress}
      </span>
    </div>
  );
}
