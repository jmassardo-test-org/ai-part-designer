/**
 * File upload component with drag-and-drop support.
 */

import { 
  Upload, 
  X, 
  File as FileIcon, 
  CheckCircle2, 
  AlertCircle,
  Loader2 
} from 'lucide-react';
import { useState, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';

// API base URL
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Allowed file types
const ALLOWED_EXTENSIONS = ['.step', '.stp', '.stl', '.iges', '.igs', '.obj', '.3mf'];

interface UploadedFile {
  id: string;
  filename: string;
  original_filename: string;
  size_bytes: number;
  file_type: string;
  cad_format: string | null;
  status: string;
  download_url: string;
}

interface FileUploaderProps {
  onUploadComplete?: (file: UploadedFile) => void;
  onError?: (error: string) => void;
  maxSizeMB?: number;
  accept?: string;
  multiple?: boolean;
  className?: string;
}

interface UploadingFile {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'complete' | 'error';
  error?: string;
  uploadedFile?: UploadedFile;
}

export function FileUploader({
  onUploadComplete,
  onError,
  maxSizeMB = 50,
  accept = ALLOWED_EXTENSIONS.join(','),
  multiple = false,
  className = '',
}: FileUploaderProps) {
  const { token } = useAuth();
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const [isDragging, setIsDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadingFile[]>([]);

  // Validate file
  const validateFile = useCallback((file: File): string | null => {
    // Check size
    const maxBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxBytes) {
      return `File too large. Maximum size is ${maxSizeMB}MB`;
    }

    // Check extension
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `File type not allowed. Supported: ${ALLOWED_EXTENSIONS.join(', ')}`;
    }

    return null;
  }, [maxSizeMB]);

  // Upload a single file
  const uploadFile = useCallback(async (uploadingFile: UploadingFile) => {
    const formData = new FormData();
    formData.append('file', uploadingFile.file);

    try {
      // Update status to uploading
      setUploads((prev) =>
        prev.map((u) =>
          u.id === uploadingFile.id ? { ...u, status: 'uploading' as const, progress: 0 } : u
        )
      );

      const response = await fetch(`${API_BASE}/files/upload`, {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.detail || 'Upload failed');
      }

      const uploadedFile: UploadedFile = await response.json();

      // Update status to complete
      setUploads((prev) =>
        prev.map((u) =>
          u.id === uploadingFile.id
            ? { ...u, status: 'complete' as const, progress: 100, uploadedFile }
            : u
        )
      );

      onUploadComplete?.(uploadedFile);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      
      // Update status to error
      setUploads((prev) =>
        prev.map((u) =>
          u.id === uploadingFile.id ? { ...u, status: 'error' as const, error: errorMessage } : u
        )
      );

      onError?.(errorMessage);
    }
  }, [token, onUploadComplete, onError]);

  // Handle file selection
  const handleFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files);
    const filesToUpload = multiple ? fileArray : [fileArray[0]];

    const newUploads: UploadingFile[] = [];

    for (const file of filesToUpload) {
      const validationError = validateFile(file);
      
      const uploadingFile: UploadingFile = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
        file,
        progress: 0,
        status: validationError ? 'error' : 'pending',
        error: validationError || undefined,
      };

      newUploads.push(uploadingFile);
    }

    setUploads((prev) => [...prev, ...newUploads]);

    // Start uploads for valid files
    for (const upload of newUploads) {
      if (upload.status === 'pending') {
        uploadFile(upload);
      }
    }
  }, [multiple, validateFile, uploadFile]);

  // Drag handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files?.length) {
      handleFiles(e.dataTransfer.files);
    }
  }, [handleFiles]);

  // Click handler
  const handleClick = () => {
    fileInputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) {
      handleFiles(e.target.files);
    }
    // Reset input to allow re-uploading same file
    e.target.value = '';
  };

  // Remove an upload from the list
  const removeUpload = (id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  };

  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className={className}>
      {/* Drop zone */}
      <div
        data-testid="drop-zone"
        role="button"
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          dropzone relative border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
          transition-colors duration-200
          ${isDragging
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500 hover:bg-gray-50 dark:hover:bg-gray-700'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleInputChange}
          className="hidden"
        />

        <div className="flex flex-col items-center gap-3">
          <div className={`
            h-12 w-12 rounded-full flex items-center justify-center
            ${isDragging ? 'bg-primary-100 dark:bg-primary-900/40' : 'bg-gray-100 dark:bg-gray-700'}
          `}>
            <Upload className={`h-6 w-6 ${isDragging ? 'text-primary-600' : 'text-gray-400'}`} />
          </div>

          <div>
            <p className="font-medium text-gray-900 dark:text-gray-100">
              {isDragging ? 'Drop files here' : 'Drag and drop files here'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              or click to browse
            </p>
          </div>

          <p className="text-xs text-gray-400 dark:text-gray-500">
            Supports {ALLOWED_EXTENSIONS.join(', ')} up to {maxSizeMB}MB
          </p>
        </div>
      </div>

      {/* Upload list */}
      {uploads.length > 0 && (
        <div className="mt-4 space-y-2">
          {uploads.map((upload) => (
            <div
              key={upload.id}
              className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
            >
              {/* Icon */}
              <div className="flex-shrink-0">
                {upload.status === 'complete' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : upload.status === 'error' ? (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                ) : upload.status === 'uploading' ? (
                  <Loader2 className="h-5 w-5 text-primary-600 animate-spin" />
                ) : (
                  <FileIcon className="h-5 w-5 text-gray-400" />
                )}
              </div>

              {/* File info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {upload.file.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {formatSize(upload.file.size)}
                  {upload.error && (
                    <span className="text-red-500 ml-2">• {upload.error}</span>
                  )}
                  {upload.status === 'complete' && (
                    <span className="text-green-600 ml-2">• Uploaded</span>
                  )}
                </p>
              </div>

              {/* Progress or remove button */}
              {upload.status === 'uploading' ? (
                <div className="w-16 h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary-600 transition-all duration-300"
                    style={{ width: `${upload.progress}%` }}
                  />
                </div>
              ) : (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeUpload(upload.id);
                  }}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
