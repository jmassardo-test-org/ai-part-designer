/**
 * Marketplace page for browsing public designs.
 * 
 * Allows users to discover, filter, and save community designs.
 */

import {
  Search,
  Grid,
  List,
  Loader2,
  AlertCircle,
  Heart,
  GitFork,
  Star,
  TrendingUp,
  Clock,
  X,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { SaveButton } from '@/components/marketplace/SaveButton';
import { useAuth } from '@/contexts/AuthContext';
import type {
  BrowseFilters,
  CategoryResponse,
  DesignSummary,
} from '@/types/marketplace';
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
// Design Card Component
// =============================================================================

interface DesignCardProps {
  design: DesignSummary;
  viewMode: 'grid' | 'list';
  onSaveToggle?: (designId: string, saved: boolean) => void;
}

function DesignCard({ design, viewMode, onSaveToggle }: DesignCardProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    navigate(`/marketplace/${design.id}`);
  };

  if (viewMode === 'list') {
    return (
      <div
        className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-500 dark:hover:border-indigo-400 transition-colors cursor-pointer"
        onClick={handleClick}
      >
        {/* Thumbnail */}
        <div className="w-20 h-20 bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden flex-shrink-0">
          {design.thumbnail_url ? (
            <img
              src={design.thumbnail_url}
              alt={design.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-gray-400">
              <Grid className="w-8 h-8" />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-gray-900 dark:text-white truncate">
              {design.name}
            </h3>
            {design.is_starter && (
              <span className="px-2 py-0.5 text-xs font-medium bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300 rounded-full">
                Starter
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
            {design.description || 'No description'}
          </p>
          <div className="flex items-center gap-4 mt-1 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <Heart className="w-3 h-3" />
              {design.save_count}
            </span>
            <span className="flex items-center gap-1">
              <GitFork className="w-3 h-3" />
              {design.remix_count}
            </span>
            <span>by {design.author_name}</span>
          </div>
        </div>

        {/* Tags */}
        <div className="hidden md:flex items-center gap-1 flex-shrink-0">
          {design.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Save button */}
        <div onClick={(e) => e.stopPropagation()}>
          <SaveButton designId={design.id} onSaveChange={onSaveToggle} />
        </div>
      </div>
    );
  }

  // Grid view
  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-indigo-500 dark:hover:border-indigo-400 transition-colors overflow-hidden cursor-pointer group"
      onClick={handleClick}
    >
      {/* Thumbnail */}
      <div className="aspect-video bg-gray-100 dark:bg-gray-700 relative">
        {design.thumbnail_url ? (
          <img
            src={design.thumbnail_url}
            alt={design.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <Grid className="w-12 h-12" />
          </div>
        )}

        {/* Overlay badges */}
        {design.is_starter && (
          <div className="absolute top-2 left-2">
            <span className="px-2 py-1 text-xs font-medium bg-indigo-500 text-white rounded-full shadow">
              Starter
            </span>
          </div>
        )}

        {/* Save button overlay */}
        <div
          className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={(e) => e.stopPropagation()}
        >
          <SaveButton designId={design.id} onSaveChange={onSaveToggle} variant="icon" />
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        <h3 className="font-medium text-gray-900 dark:text-white truncate">
          {design.name}
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">
          {design.description || 'No description'}
        </p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mt-2">
          {design.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* Stats & author */}
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-3 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <Heart className="w-3 h-3" />
              {design.save_count}
            </span>
            <span className="flex items-center gap-1">
              <GitFork className="w-3 h-3" />
              {design.remix_count}
            </span>
          </div>
          <span className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-[120px]">
            by {design.author_name}
          </span>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Sort Options
// =============================================================================

const SORT_OPTIONS = [
  { value: 'popular', label: 'Most Popular', icon: TrendingUp },
  { value: 'recent', label: 'Most Recent', icon: Clock },
  { value: 'trending', label: 'Trending', icon: Star },
] as const;

// =============================================================================
// Main Component
// =============================================================================

export function MarketplacePage() {
  const { token } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // State
  const [designs, setDesigns] = useState<DesignSummary[]>([]);
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [featuredDesigns, setFeaturedDesigns] = useState<DesignSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);

  // Filters from URL
  const currentCategory = searchParams.get('category') || '';
  const currentSort = (searchParams.get('sort') as BrowseFilters['sort']) || 'popular';
  const currentPage = parseInt(searchParams.get('page') || '1', 10);
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const debouncedSearch = useDebounce(searchInput, 300);

  // Load categories and featured designs on mount
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [cats, featured] = await Promise.all([
          api.getCategories(token || undefined),
          api.getFeaturedDesigns(6, token || undefined),
        ]);
        setCategories(cats);
        setFeaturedDesigns(featured);
      } catch (err) {
        console.error('Failed to load initial data:', err);
      }
    }
    loadInitialData();
  }, [token]);

  // Load designs when filters change
  useEffect(() => {
    async function loadDesigns() {
      setSearchLoading(true);
      setError(null);

      try {
        const filters: BrowseFilters = {
          category: currentCategory || undefined,
          search: debouncedSearch || undefined,
          sort: currentSort,
          page: currentPage,
          page_size: 20,
        };

        const response = await api.browseDesigns(filters, token || undefined);
        setDesigns(response.items);
        setTotalPages(response.total_pages);
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load designs');
      } finally {
        setLoading(false);
        setSearchLoading(false);
      }
    }

    loadDesigns();
  }, [currentCategory, currentSort, currentPage, debouncedSearch, token]);

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
      // Reset to page 1 when changing filters (except when explicitly setting page)
      if (!('page' in updates)) {
        newParams.delete('page');
      }
      setSearchParams(newParams);
    },
    [searchParams, setSearchParams]
  );

  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    updateFilters({ search: value });
  };

  const handleCategoryChange = (category: string) => {
    updateFilters({ category });
  };

  const handleSortChange = (sort: string) => {
    updateFilters({ sort });
  };

  const handlePageChange = (page: number) => {
    updateFilters({ page: page.toString() });
  };

  const clearFilters = () => {
    setSearchInput('');
    setSearchParams(new URLSearchParams());
  };

  const hasActiveFilters = currentCategory || searchInput;

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Marketplace
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Discover and save enclosure designs from the community
          </p>

          {/* Search and filters */}
          <div className="mt-6 flex flex-col sm:flex-row gap-4">
            {/* Search input */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search designs..."
                value={searchInput}
                onChange={(e) => handleSearchChange(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
              {searchLoading && (
                <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-gray-400" />
              )}
            </div>

            {/* Sort dropdown */}
            <select
              value={currentSort}
              onChange={(e) => handleSortChange(e.target.value)}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            {/* View mode toggle */}
            <div className="flex border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 ${
                  viewMode === 'grid'
                    ? 'bg-indigo-500 text-white'
                    : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                }`}
                title="Grid view"
              >
                <Grid className="w-5 h-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 ${
                  viewMode === 'list'
                    ? 'bg-indigo-500 text-white'
                    : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300'
                }`}
                title="List view"
              >
                <List className="w-5 h-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Sidebar - Categories */}
          <div className="hidden lg:block w-64 flex-shrink-0">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <h2 className="font-semibold text-gray-900 dark:text-white mb-4">
                Categories
              </h2>
              <div className="space-y-1">
                <button
                  onClick={() => handleCategoryChange('')}
                  className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                    !currentCategory
                      ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                  }`}
                >
                  All Designs
                </button>
                {categories.map((category) => (
                  <button
                    key={category.slug}
                    onClick={() => handleCategoryChange(category.slug)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-colors flex items-center justify-between ${
                      currentCategory === category.slug
                        ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'
                        : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                    }`}
                  >
                    <span>{category.name}</span>
                    <span className="text-xs text-gray-400">{category.design_count}</span>
                  </button>
                ))}
              </div>

              {/* Quick links */}
              <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-2">
                  Quick Links
                </h3>
                <div className="space-y-1">
                  <Link
                    to="/starters"
                    className="flex items-center gap-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <Star className="w-4 h-4" />
                    Starter Designs
                  </Link>
                  <Link
                    to="/lists"
                    className="flex items-center gap-2 px-3 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 rounded-lg"
                  >
                    <Heart className="w-4 h-4" />
                    My Lists
                  </Link>
                </div>
              </div>
            </div>
          </div>

          {/* Main content */}
          <div className="flex-1 min-w-0">
            {/* Featured section (only on first page without search) */}
            {!hasActiveFilters && currentPage === 1 && featuredDesigns.length > 0 && (
              <div className="mb-8">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
                  <Star className="w-5 h-5 text-yellow-500" />
                  Featured Designs
                </h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {featuredDesigns.slice(0, 3).map((design) => (
                    <DesignCard key={design.id} design={design} viewMode="grid" />
                  ))}
                </div>
              </div>
            )}

            {/* Active filters */}
            {hasActiveFilters && (
              <div className="flex items-center gap-2 mb-4">
                <span className="text-sm text-gray-500 dark:text-gray-400">Filters:</span>
                {currentCategory && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 rounded text-sm">
                    {categories.find((c) => c.slug === currentCategory)?.name || currentCategory}
                    <button onClick={() => handleCategoryChange('')}>
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                {searchInput && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-sm">
                    "{searchInput}"
                    <button onClick={() => handleSearchChange('')}>
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                <button
                  onClick={clearFilters}
                  className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                >
                  Clear all
                </button>
              </div>
            )}

            {/* Results count */}
            <div className="flex items-center justify-between mb-4">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {total} {total === 1 ? 'design' : 'designs'} found
              </p>
            </div>

            {/* Error state */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                  <AlertCircle className="w-5 h-5" />
                  <p>{error}</p>
                </div>
              </div>
            )}

            {/* Design grid/list */}
            {designs.length === 0 && !error ? (
              <div className="text-center py-12">
                <Grid className="w-12 h-12 mx-auto text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No designs found
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  Try adjusting your filters or search terms
                </p>
              </div>
            ) : viewMode === 'grid' ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {designs.map((design) => (
                  <DesignCard key={design.id} design={design} viewMode="grid" />
                ))}
              </div>
            ) : (
              <div className="space-y-3">
                {designs.map((design) => (
                  <DesignCard key={design.id} design={design} viewMode="list" />
                ))}
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="mt-8 flex items-center justify-center gap-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage <= 1}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="px-4 py-2 text-gray-600 dark:text-gray-400">
                  Page {currentPage} of {totalPages}
                </span>
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage >= totalPages}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MarketplacePage;
