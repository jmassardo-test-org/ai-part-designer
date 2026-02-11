/**
 * Starter Detail Page - Shows full details of a starter design.
 * 
 * Displays the enclosure spec, 3D preview, and allows users to remix.
 */

import {
  ArrowLeft,
  Box,
  GitFork,
  Layers,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import type { EnclosureSpec } from '@/types/cad-v2';
import type { StarterDetail } from '@/types/marketplace';
import * as api from '@/lib/marketplace';

export function StarterDetailPage() {
  const { starterId } = useParams<{ starterId: string }>();
  const { token, user } = useAuth();
  const navigate = useNavigate();

  const [starter, setStarter] = useState<StarterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [remixing, setRemixing] = useState(false);

  useEffect(() => {
    async function loadStarter() {
      if (!starterId) return;
      
      setLoading(true);
      setError(null);

      try {
        const data = await api.getStarterDetail(starterId);
        setStarter(data);
      } catch (err) {
        console.error('Failed to load starter:', err);
        setError('Failed to load starter design. It may not exist or is no longer available.');
      } finally {
        setLoading(false);
      }
    }

    loadStarter();
  }, [starterId]);

  const handleRemix = async () => {
    if (!starterId) return;

    if (!user) {
      navigate('/auth/login', { state: { from: `/starters/${starterId}` } });
      return;
    }

    setRemixing(true);
    try {
      const remix = await api.remixStarter(starterId, undefined, token || undefined);
      // Navigate to generate page with the enclosure spec pre-loaded
      navigate('/generate', {
        state: {
          remixMode: true,
          enclosureSpec: remix.enclosure_spec,
          remixedFrom: {
            id: remix.remixed_from_id,
            name: remix.remixed_from_name,
          },
          designId: remix.id,
          designName: remix.name,
        },
      });
    } catch (err) {
      console.error('Failed to remix:', err);
      setError('Failed to create remix. Please try again.');
    } finally {
      setRemixing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  if (error || !starter) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-700 dark:text-red-400 mb-2">
            Starter Not Found
          </h2>
          <p className="text-red-600 dark:text-red-300 mb-4">
            {error || 'This starter design could not be found.'}
          </p>
          <Link
            to="/starters"
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-200 rounded-lg hover:bg-red-200 dark:hover:bg-red-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Starters
          </Link>
        </div>
      </div>
    );
  }

  // Extract dimensions from enclosure spec
  const spec = starter.enclosure_spec as EnclosureSpec | null;
  const exterior = spec?.exterior;
  const dimensions = exterior ? {
    width: exterior.width?.value,
    depth: exterior.depth?.value,
    height: exterior.height?.value,
    unit: exterior.width?.unit || 'mm',
  } : null;

  // Extract features from enclosure spec
  const features: string[] = [];
  if (spec) {
    if (spec.lid?.type) {
      features.push(`${spec.lid.type.replace('_', ' ')} lid`);
    }
    if (spec.ventilation?.enabled) {
      features.push('Ventilation');
    }
    if (spec.features?.length) {
      spec.features.forEach((f) => {
        if (!features.includes(f.type)) {
          features.push(f.type.replace('_', ' '));
        }
      });
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Back navigation */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link
            to="/starters"
            className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Starters
          </Link>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Preview */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div className="aspect-square bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 flex items-center justify-center">
              {starter.thumbnail_url ? (
                <img
                  src={starter.thumbnail_url}
                  alt={starter.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <Box className="w-32 h-32 text-indigo-300 dark:text-indigo-600" />
              )}
            </div>
          </div>

          {/* Right: Details */}
          <div className="space-y-6">
            {/* Title and description */}
            <div>
              <div className="flex items-center gap-3 mb-2">
                {starter.category && (
                  <span className="px-3 py-1 bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 text-sm rounded-full">
                    {starter.category.replace('-', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </span>
                )}
                <div className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
                  <GitFork className="w-4 h-4" />
                  {starter.remix_count} remixes
                </div>
              </div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-3">
                {starter.name}
              </h1>
              <p className="text-lg text-gray-600 dark:text-gray-300">
                {starter.description || 'A ready-to-customize enclosure template'}
              </p>
            </div>

            {/* Dimensions */}
            {dimensions && (
              <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-2">
                  <Layers className="w-4 h-4" />
                  Dimensions
                </h3>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {dimensions.width} × {dimensions.depth} × {dimensions.height} {dimensions.unit}
                </p>
              </div>
            )}

            {/* Features */}
            {features.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Features
                </h3>
                <div className="flex flex-wrap gap-2">
                  {features.map((feature) => (
                    <span
                      key={feature}
                      className="px-3 py-1.5 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 text-sm rounded-lg"
                    >
                      {feature}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Tags */}
            {starter.tags && starter.tags.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Tags
                </h3>
                <div className="flex flex-wrap gap-2">
                  {starter.tags.map((tag) => (
                    <span
                      key={tag}
                      className="px-2 py-1 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs rounded"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Remix button */}
            <div className="pt-4">
              <button
                onClick={handleRemix}
                disabled={remixing}
                className="w-full py-4 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-3 font-semibold text-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {remixing ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Creating Your Remix...
                  </>
                ) : (
                  <>
                    <GitFork className="w-5 h-5" />
                    Remix This Design
                  </>
                )}
              </button>
              <p className="text-center text-sm text-gray-500 dark:text-gray-400 mt-3">
                Creates a copy you can customize in the AI chat editor
              </p>
            </div>
          </div>
        </div>

        {/* Enclosure Spec Details (collapsible) */}
        {starter.enclosure_spec && (
          <div className="mt-8 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
            <details className="group">
              <summary className="px-6 py-4 cursor-pointer list-none flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                <h3 className="font-medium text-gray-900 dark:text-white">
                  Technical Specification
                </h3>
                <span className="text-gray-400 group-open:rotate-180 transition-transform">
                  ▼
                </span>
              </summary>
              <div className="px-6 pb-6">
                <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm">
                  {JSON.stringify(starter.enclosure_spec, null, 2)}
                </pre>
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}

export default StarterDetailPage;
