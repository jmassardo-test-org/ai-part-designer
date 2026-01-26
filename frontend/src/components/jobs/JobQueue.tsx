/**
 * Job Queue Component - Shows active jobs in header.
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  Box,
  FileBox,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface Job {
  id: string;
  job_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  metadata: Record<string, unknown>;
}

// =============================================================================
// Job Queue Component
// =============================================================================

export function JobQueue() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Fetch active jobs
  const fetchJobs = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `${API_BASE}/jobs?status=pending&status=processing&limit=10`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.ok) {
        const data = await response.json();
        setJobs(data.items || []);
      }
    } catch (err) {
      console.error('Failed to fetch jobs:', err);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  // Poll for updates
  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 5000); // Poll every 5 seconds
    return () => clearInterval(interval);
  }, [fetchJobs]);

  // Get active job count
  const activeCount = jobs.filter(j => j.status === 'pending' || j.status === 'processing').length;

  // Get job icon
  const getJobIcon = (jobType: string) => {
    switch (jobType) {
      case 'generate':
        return Box;
      case 'export':
        return FileBox;
      default:
        return Activity;
    }
  };

  // Get status color
  const getStatusColor = (status: Job['status']) => {
    switch (status) {
      case 'completed':
        return 'text-green-500';
      case 'failed':
        return 'text-red-500';
      case 'processing':
        return 'text-blue-500';
      case 'pending':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  };

  // Get status icon
  const getStatusIcon = (status: Job['status']) => {
    switch (status) {
      case 'completed':
        return CheckCircle;
      case 'failed':
        return XCircle;
      case 'processing':
        return Loader2;
      case 'pending':
        return Clock;
      default:
        return Activity;
    }
  };

  // Format job type
  const formatJobType = (type: string) => {
    return type.charAt(0).toUpperCase() + type.slice(1).replace(/_/g, ' ');
  };

  // Format time ago
  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="relative">
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
        aria-label="View active jobs"
      >
        <Activity className="w-5 h-5" />
        {activeCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-primary-600 text-white text-xs rounded-full flex items-center justify-center">
            {activeCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Panel */}
          <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50">
            <div className="flex items-center justify-between p-3 border-b">
              <h3 className="font-medium">Active Jobs</h3>
              {activeCount > 0 && (
                <span className="text-xs px-2 py-0.5 bg-primary-100 text-primary-700 rounded-full">
                  {activeCount} running
                </span>
              )}
            </div>

            {isLoading && jobs.length === 0 ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
              </div>
            ) : jobs.length === 0 ? (
              <div className="py-8 text-center text-gray-500">
                <Activity className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                <p className="text-sm">No active jobs</p>
              </div>
            ) : (
              <div className="max-h-80 overflow-y-auto divide-y">
                {jobs.map(job => {
                  const JobIcon = getJobIcon(job.job_type);
                  const StatusIcon = getStatusIcon(job.status);
                  const statusColor = getStatusColor(job.status);

                  return (
                    <div
                      key={job.id}
                      className="p-3 hover:bg-gray-50 cursor-pointer"
                      onClick={() => {
                        setIsOpen(false);
                        navigate(`/jobs/${job.id}`);
                      }}
                    >
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          <JobIcon className="w-4 h-4 text-gray-600" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium truncate">
                              {formatJobType(job.job_type)}
                            </p>
                            <StatusIcon
                              className={`w-4 h-4 ${statusColor} ${
                                job.status === 'processing' ? 'animate-spin' : ''
                              }`}
                            />
                          </div>
                          <p className="text-xs text-gray-500">
                            {formatTimeAgo(job.created_at)}
                          </p>
                          {job.status === 'processing' && (
                            <div className="mt-2">
                              <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-primary-600 transition-all duration-300"
                                  style={{ width: `${job.progress}%` }}
                                />
                              </div>
                              <p className="text-xs text-gray-500 mt-1">
                                {job.progress}% complete
                              </p>
                            </div>
                          )}
                          {job.status === 'failed' && job.error_message && (
                            <p className="text-xs text-red-600 mt-1 truncate">
                              {job.error_message}
                            </p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* Footer */}
            <div className="border-t p-2">
              <button
                onClick={() => {
                  setIsOpen(false);
                  navigate('/jobs');
                }}
                className="w-full text-center text-sm text-primary-600 hover:text-primary-700 py-2"
              >
                View all jobs
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
