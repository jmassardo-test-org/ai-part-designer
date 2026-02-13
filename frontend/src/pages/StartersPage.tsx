/**
 * Starters page for browsing vendor-published starter designs.
 * 
 * Allows users to discover and remix starter templates.
 */

import {
  Search,
  Loader2,
  AlertCircle,
  Star,
  GitFork,
  ChevronRight,
  X,
  Box,
  Layers,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import type { StarterDesign } from '@/types/marketplace';
import * as api from '@/lib/marketplace';

// =============================================================================
// Custom Hooks
// =============================================================================

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
}

// =============================================================================
// Starter Card Component
// =============================================================================

interface StarterCardProps {
  starter: StarterDesign;
  onRemix: (id: string) => void;
}

function StarterCard({ starter, onRemix }: StarterCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/starters/${starter.id}`);
  };

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-indigo-500 dark:hover:border-indigo-400 transition-all hover:shadow-lg cursor-pointer overflow-hidden group"
      onClick={handleClick}
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 relative">
        {starter.thumbnail_url ? (
          <img
            src={starter.thumbnail_url}
            alt={starter.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Box className="w-16 h-16 text-indigo-300 dark:text-indigo-600" />
          </div>
        )}

        {/* Remix count badge */}
        <div className="absolute top-3 right-3 px-2 py-1 bg-black/50 backdrop-blur-sm rounded-full text-white text-xs flex items-center gap-1">
          <GitFork className="w-3 h-3" />
          {starter.remix_count}
        </div>
      </div>

      {/* Content */}
      <div className="p-5">
        <h3 className="font-semibold text-gray-900 dark:text-white text-lg">
          {starter.name}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
          {starter.description || 'A ready-to-customize enclosure template'}
        </p>

        {/* Dimensions */}
        {starter.exterior_dimensions && (
          <div className="flex items-center gap-2 mt-3 text-xs text-gray-500 dark:text-gray-400">
            <Layers className="w-4 h-4" />
            <span>
              {starter.exterior_dimensions.width} × {starter.exterior_dimensions.depth} ×{' '}
              {starter.exterior_dimensions.height} {starter.exterior_dimensions.unit}
            </span>
          </div>
        )}

        {/* Features */}
        {starter.features.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {starter.features.slice(0, 4).map((feature) => (
              <span
                key={feature}
                className="px-2 py-0.5 text-xs bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 rounded"
              >
                {feature}
              </span>
            ))}
            {starter.features.length > 4 && (
              <span className="px-2 py-0.5 text-xs text-gray-400">
                +{starter.features.length - 4} more
              </span>
            )}
          </div>
        )}

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mt-3">
          {starter.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Remix button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemix(starter.id);
          }}
          className="w-full mt-4 py-2.5 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors flex items-center justify-center gap-2 font-medium"
        >
          <GitFork className="w-4 h-4" />
          Remix This Design
        </button>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function StartersPage() {
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [starters, setStarters] = useState<StarterDesign[]>([]);
  const [categories, setCategories] = useState<{ name: string; slug: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [remixing, setRemixing] = useState<string | null>(null);

  // Filters
  const currentCategory = searchParams.get('category') || '';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const debouncedSearch = useDebounce(searchInput, 300);

  // Load categories on mount
  useEffect(() => {
    async function loadCategories() {
      try {
        const cats = await api.getStarterCategories();
        setCategories(cats as any);
      } catch (err) {
        console.error('Failed to load categories:', err);
      }
    }
    loadCategories();
  }, []);

  // Load starters when filters change
  useEffect(() => {
    async function loadStarters() {
      setSearchLoading(true);
      setError(null);

      try {
        const response = await api.getStarters({
          category: currentCategory || undefined,
          search: debouncedSearch || undefined,
          page: currentPage,
          page_size: 12,
        });
        setStarters(response.items);
        setTotalPages(Math.ceil(response.total / response.page_size));
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load starters');
      } finally {
        setLoading(false);
        setSearchLoading(false);
      }
    }

    loadStarters();
  }, [currentCategory, currentPage, debouncedSearch]);

  // Update URL params
  const updateFilters = useCallback(
    (updates: Partial<Record<string, string>>) => {
      const newParams = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (value) {
          newParams.set(key, value);
        } else {
          newParams.delete(key);
        }
      });
      if (!('page' in updates)) {
        newParams.delete('page');
      }
      setSearchParams(newParams);
    },
    [searchParams, setSearchParams]
  );

  const handleRemix = async (starterId: string) => {
    if (!user) {
      navigate('/auth/login', { state: { from: `/starters/${starterId}` } });
      return;
    }

    setRemixing(starterId);
    try {
      const remix = await api.remixStarter(starterId, undefined, token || undefined);
      // Navigate to the generate page with the remixed spec
      navigate('/generate', {
        state: {
          remixMode: true,
          enclosureSpec: remix.enclosure_spec,
          remixedFrom: {
            id: remix.remixed_from_id,
            name: remix.remixed_from_name,
          },
          designId: remix.id,
          designName: remix.remixed_from_name,
        },
      });
    } catch (err) {
      console.error('Failed to remix:', err);
      setError('Failed to create remix. Please try again.');
    } finally {
      setRemixing(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Hero Header */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-600 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center max-w-3xl mx-auto">
            <Star className="w-12 h-12 mx-auto mb-4 text-yellow-400" />
            <h1 className="text-4xl font-bold mb-4">Starter Designs</h1>
            <p className="text-xl text-indigo-100 mb-8">
              Pre-built enclosure templates ready to customize. Choose a starting point,
              remix it to your needs, and generate your perfect enclosure.
            </p>

            {/* Search */}
            <div className="max-w-xl mx-auto relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search starter designs..."
                value={searchInput}
                onChange={(e) => {
                  setSearchInput(e.target.value);
                  updateFilters({ search: e.target.value });
                }}
                className="w-full pl-12 pr-4 py-3 rounded-xl bg-white/10 backdrop-blur border border-white/20 text-white placeholder-white/60 focus:ring-2 focus:ring-white/50 focus:border-transparent"
              />
              {searchLoading && (
                <Loader2 className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 animate-spin text-white/60" />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Category pills */}
      {categories.length > 0 && (
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              <button
                onClick={() => updateFilters({ category: '' })}
                className={`px-4 py-2 rounded-full whitespace-nowrap transition-colors ${
                  !currentCategory
                    ? 'bg-indigo-500 text-white'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.slug}
                  onClick={() => updateFilters({ category: cat.slug })}
                  className={`px-4 py-2 rounded-full whitespace-nowrap transition-colors ${
                    currentCategory === cat.slug
                      ? 'bg-indigo-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {cat.name}
                  <span className="ml-1.5 text-xs opacity-70">({cat.count})</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Active filters */}
        {(currentCategory || searchInput) && (
          <div className="flex items-center gap-2 mb-6">
            <span className="text-sm text-gray-500 dark:text-gray-400">Filters:</span>
            {currentCategory && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded text-sm">
                {categories.find((c) => c.slug === currentCategory)?.name || currentCategory}
                <button onClick={() => updateFilters({ category: '' })}>
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {searchInput && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-sm">
                "{searchInput}"
                <button
                  onClick={() => {
                    setSearchInput('');
                    updateFilters({ search: '' });
                  }}
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
          </div>
        )}

        {/* Results count */}
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          {total} starter {total === 1 ? 'design' : 'designs'} available
        </p>

        {/* Error state */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
              <AlertCircle className="w-5 h-5" />
              <p>{error}</p>
            </div>
          </div>
        )}

        {/* Starters grid */}
        {starters.length === 0 && !error ? (
          <div className="text-center py-16">
            <Box className="w-16 h-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              No starters found
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              Try adjusting your search or category filter
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {starters.map((starter) => (
              <StarterCard
                key={starter.id}
                starter={starter}
                onRemix={handleRemix}
              />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-8 flex items-center justify-center gap-2">
            <button
              onClick={() => updateFilters({ page: (currentPage - 1).toString() })}
              disabled={currentPage <= 1}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="px-4 py-2 text-gray-600 dark:text-gray-400">
              Page {currentPage} of {totalPages}
            </span>
            <button
              onClick={() => updateFilters({ page: (currentPage + 1).toString() })}
              disabled={currentPage >= totalPages}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        )}

        {/* CTA section */}
        <div className="mt-16 text-center bg-gradient-to-br from-gray-100 to-gray-50 dark:from-gray-800 dark:to-gray-900 rounded-2xl p-8 border border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Can't find what you need?
          </h2>
          <p className="text-gray-600 dark:text-gray-400 mb-6">
            Start from scratch and describe your perfect enclosure. Our AI will design it for you.
          </p>
          <Link
            to="/create"
            className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 font-medium"
          >
            Create from Scratch
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {/* Loading overlay for remix */}
      {remixing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 flex items-center gap-3">
            <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
            <span className="text-gray-900 dark:text-white">Creating your remix...</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default StartersPage;
