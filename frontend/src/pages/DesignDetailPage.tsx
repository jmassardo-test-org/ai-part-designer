/**
 * Design Detail Page - Shows details of a saved design.
 * 
 * Displays the 3D preview and allows downloading files.
 */

import {
  ArrowLeft,
  Box,
  Download,
  Edit2,
  Loader2,
  AlertCircle,
  FileBox,
  Calendar,
  Folder,
  GitFork,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ModelViewer } from '@/components/viewer/ModelViewer';
import { useAuth } from '@/contexts/AuthContext';
import { getDesign, type Design } from '@/lib/designs';
import { getPreviewData, downloadGeneratedFile } from '@/lib/generate';

export function DesignDetailPage() {
  const { designId } = useParams<{ designId: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();

  const [design, setDesign] = useState<Design | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stlData, setStlData] = useState<ArrayBuffer | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  // Get extra_data from design
  const extraData = design?.extra_data || null;

  // Fetch design details
  useEffect(() => {
    async function loadDesign() {
      if (!designId || !token) return;
      
      setLoading(true);
      setError(null);

      try {
        const data = await getDesign(designId, token);
        setDesign(data);
        
        // Load STL preview if job_id exists
        if (data.extra_data?.job_id) {
          try {
            const preview = await getPreviewData(data.extra_data.job_id, token);
            setStlData(preview);
          } catch {
            console.log('No preview available');
          }
        }
      } catch (err) {
        console.error('Failed to load design:', err);
        setError('Failed to load design. It may not exist or you do not have access.');
      } finally {
        setLoading(false);
      }
    }

    loadDesign();
  }, [designId, token]);

  const handleDownload = async (format: 'step' | 'stl') => {
    if (!extraData?.job_id || !token) return;
    
    setDownloading(format);
    try {
      const blob = await downloadGeneratedFile(extraData.job_id, format, token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${design?.name || 'design'}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
      setError('Failed to download file');
    } finally {
      setDownloading(null);
    }
  };

  const handleRemix = () => {
    if (!design || !extraData) return;
    
    navigate('/create', {
      state: {
        initialPrompt: design.description || `Modify the ${design.name}`,
        remixMode: true,
        remixedFrom: {
          id: design.id,
          name: design.name,
        },
        enclosureSpec: extraData.enclosure_schema,
      },
    });
  };

  const handleEdit = () => {
    if (!design || !extraData?.enclosure_schema) return;

    navigate('/generate', {
      state: {
        editMode: true,
        editDesignId: design.id,
        editDesignName: design.name,
        enclosureSpec: extraData.enclosure_schema,
        remixedFrom: { id: design.id, name: design.name },
      },
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-500">Loading design...</p>
        </div>
      </div>
    );
  }

  if (error || !design) {
    return (
      <div className="max-w-lg mx-auto mt-16">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-red-700 dark:text-red-400 mb-2">
            Design Not Found
          </h2>
          <p className="text-red-600 dark:text-red-300 mb-4">
            {error || 'This design could not be loaded.'}
          </p>
          <Link
            to="/projects"
            className="inline-flex items-center gap-2 text-primary-600 hover:text-primary-700"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Projects
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link
          to="/projects"
          className="inline-flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Projects
        </Link>
        
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {design.name}
            </h1>
            {design.description && (
              <p className="mt-2 text-gray-600 dark:text-gray-400">
                {String(design.description)}
              </p>
            )}
          </div>
          
          <div className="flex gap-2">
            {extraData?.enclosure_schema != null && (
              <button
                onClick={handleEdit}
                className="inline-flex items-center gap-2 px-4 py-2 border border-primary-600 text-primary-600 rounded-lg hover:bg-primary-50 dark:hover:bg-primary-900/30"
              >
                <Edit2 className="w-4 h-4" />
                Edit
              </button>
            )}
            <button
              onClick={handleRemix}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            >
              <GitFork className="w-4 h-4" />
              Remix
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 3D Preview */}
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 overflow-hidden">
            <div className="aspect-video bg-gray-100 dark:bg-gray-900">
              {stlData ? (
                <ModelViewer 
                  stlData={stlData}
                  darkMode={true}
                  showGrid={true}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <div className="text-center text-gray-400">
                    <FileBox className="w-16 h-16 mx-auto mb-4" />
                    <p>No preview available</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Details Panel */}
        <div className="space-y-6">
          {/* Info Card */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              Details
            </h2>
            
            <dl className="space-y-4">
              <div className="flex items-center gap-3">
                <Calendar className="w-5 h-5 text-gray-400" />
                <div>
                  <dt className="text-sm text-gray-500 dark:text-gray-400">Created</dt>
                  <dd className="text-gray-900 dark:text-white">{formatDate(design.created_at)}</dd>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <Folder className="w-5 h-5 text-gray-400" />
                <div>
                  <dt className="text-sm text-gray-500 dark:text-gray-400">Project</dt>
                  <dd className="text-gray-900 dark:text-white">{design.project_name}</dd>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <Box className="w-5 h-5 text-gray-400" />
                <div>
                  <dt className="text-sm text-gray-500 dark:text-gray-400">Type</dt>
                  <dd className="text-gray-900 dark:text-white capitalize">{design.source_type.replace('_', ' ')}</dd>
                </div>
              </div>
              
              {extraData?.shape && (
                <div className="flex items-center gap-3">
                  <Box className="w-5 h-5 text-gray-400" />
                  <div>
                    <dt className="text-sm text-gray-500 dark:text-gray-400">Shape</dt>
                    <dd className="text-gray-900 dark:text-white capitalize">{extraData.shape}</dd>
                  </div>
                </div>
              )}
            </dl>
          </div>

          {/* Download Card */}
          {extraData?.downloads && (extraData.downloads.step || extraData.downloads.stl) && (
            <div className="bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                Downloads
              </h2>
              
              <div className="space-y-3">
                {extraData.downloads.step && (
                  <button
                    onClick={() => handleDownload('step')}
                    disabled={downloading === 'step'}
                    className="w-full flex items-center justify-between px-4 py-3 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                  >
                    <span className="font-medium text-gray-900 dark:text-white">STEP File</span>
                    {downloading === 'step' ? (
                      <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
                    ) : (
                      <Download className="w-5 h-5 text-gray-500" />
                    )}
                  </button>
                )}
                
                {extraData.downloads.stl && (
                  <button
                    onClick={() => handleDownload('stl')}
                    disabled={downloading === 'stl'}
                    className="w-full flex items-center justify-between px-4 py-3 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50"
                  >
                    <span className="font-medium text-gray-900 dark:text-white">STL File</span>
                    {downloading === 'stl' ? (
                      <Loader2 className="w-5 h-5 animate-spin text-gray-500" />
                    ) : (
                      <Download className="w-5 h-5 text-gray-500" />
                    )}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default DesignDetailPage;
