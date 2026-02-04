/**
 * Templates browsing page.
 * Allows users to browse, filter, and customize parametric templates.
 * 
 * DEPRECATED: This page is being replaced by the Starters system.
 * Users should use /starters for browsing and remixing starter designs.
 */

import { 
  Box, 
  Search, 
  Filter, 
  Grid, 
  List, 
  ChevronRight,
  Loader2,
  AlertCircle,
  Star,
  Lock,
  Plus,
  X,
  Save,
  ArrowRight,
} from 'lucide-react';
import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Template types matching backend
interface TemplateParameter {
  name: string;
  type: 'float' | 'int' | 'bool' | 'string' | 'choice';
  label: string;
  description?: string;
  default: number | string | boolean;
  min?: number;
  max?: number;
  step?: number;
  choices?: string[];
  unit?: string;
}

interface Template {
  id: string;
  slug: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  thumbnail_url?: string;
  tier_required: 'free' | 'basic' | 'pro' | 'enterprise';
  parameters: TemplateParameter[];
  is_featured: boolean;
  usage_count: number;
}

interface TemplateCategory {
  slug: string;
  name: string;
  count: number;
}

// Custom debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

export function TemplatesPage() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // State
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [initialLoading, setInitialLoading] = useState(true);  // Initial page load
  const [searchLoading, setSearchLoading] = useState(false);   // Searching/filtering only
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  
  // Create template modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTemplateName, setNewTemplateName] = useState('');
  const [newTemplateDescription, setNewTemplateDescription] = useState('');
  const [newTemplateCategory, setNewTemplateCategory] = useState('custom');
  const [newTemplateTags, setNewTemplateTags] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  
  // Local search input state (for debouncing)
  const [searchInput, setSearchInput] = useState(searchParams.get('q') || '');
  
  // Debounce search input (300ms delay)
  const debouncedSearchQuery = useDebounce(searchInput, 300);
  
  // Filter state from URL params
  const selectedCategory = searchParams.get('category') || '';
  const tierFilter = searchParams.get('tier') || '';
  
  // Update URL when debounced search changes
  useEffect(() => {
    const newParams = new URLSearchParams(searchParams);
    if (debouncedSearchQuery) {
      newParams.set('q', debouncedSearchQuery);
    } else {
      newParams.delete('q');
    }
    // Only update if actually changed to avoid loops
    if (newParams.toString() !== searchParams.toString()) {
      setSearchParams(newParams, { replace: true });
    }
  }, [debouncedSearchQuery, setSearchParams, searchParams]);

  // Fetch templates
  const fetchTemplates = useCallback(async (isInitial: boolean = false) => {
    if (isInitial) {
      setInitialLoading(true);
    } else {
      setSearchLoading(true);
    }
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.set('category', selectedCategory);
      if (debouncedSearchQuery) params.set('search', debouncedSearchQuery);
      if (tierFilter) params.set('min_tier', tierFilter);
      
      const response = await fetch(`${API_BASE}/templates?${params}`);
      if (!response.ok) throw new Error('Failed to fetch templates');
      
      const data = await response.json();
      setTemplates(data.templates || data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setInitialLoading(false);
      setSearchLoading(false);
    }
  }, [selectedCategory, debouncedSearchQuery, tierFilter]);

  // Fetch categories
  const fetchCategories = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/templates/categories`);
      if (!response.ok) throw new Error('Failed to fetch categories');
      
      const data = await response.json();
      setCategories(data.categories || data);
    } catch (err) {
      console.error('Failed to load categories:', err);
    }
  }, []);

  // Initial load - fetch templates and categories
  useEffect(() => {
    fetchTemplates(true);
    fetchCategories();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Refetch when filters change (not initial load)
  useEffect(() => {
    // Skip first render - handled by initial load
    if (initialLoading) return;
    fetchTemplates(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedCategory, debouncedSearchQuery, tierFilter]);

  // Update URL params (without triggering navigation)
  const updateFilters = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        newParams.set(key, value);
      } else {
        newParams.delete(key);
      }
    });
    setSearchParams(newParams, { replace: true });
  };

  // Check if user can access template
  const canAccessTemplate = (template: Template): boolean => {
    const tierLevels = { free: 0, basic: 1, pro: 2, enterprise: 3 };
    const userTier = user?.tier || 'free';
    return tierLevels[userTier as keyof typeof tierLevels] >= tierLevels[template.tier_required];
  };

  // Navigate to template detail/customization
  const handleTemplateClick = (template: Template) => {
    if (canAccessTemplate(template)) {
      navigate(`/templates/${template.slug}`);
    }
  };

  // Tier badge component
  const TierBadge = ({ tier }: { tier: string }) => {
    const colors: Record<string, string> = {
      free: 'bg-green-100 text-green-700',
      basic: 'bg-blue-100 text-blue-700',
      pro: 'bg-purple-100 text-purple-700',
      enterprise: 'bg-amber-100 text-amber-700',
    };
    
    return (
      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${colors[tier] || colors.free}`}>
        {tier.charAt(0).toUpperCase() + tier.slice(1)}
      </span>
    );
  };

  // Template card component
  const TemplateCard = ({ template }: { template: Template }) => {
    const accessible = canAccessTemplate(template);
    
    return (
      <div
        data-testid="template-card"
        onClick={() => handleTemplateClick(template)}
        className={`
          relative bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden
          transition-all duration-200
          ${accessible 
            ? 'hover:border-primary-300 hover:shadow-md cursor-pointer' 
            : 'opacity-75 cursor-not-allowed'
          }
        `}
      >
        {/* Thumbnail */}
        <div className="aspect-video bg-gray-100 dark:bg-gray-700 flex items-center justify-center relative">
          {template.thumbnail_url ? (
            <img 
              src={template.thumbnail_url} 
              alt={template.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <Box className="h-12 w-12 text-gray-400" />
          )}
          
          {/* Featured badge */}
          {template.is_featured && (
            <div className="absolute top-2 left-2 flex items-center gap-1 bg-amber-500 text-white px-2 py-0.5 rounded-full text-xs">
              <Star className="h-3 w-3" />
              Featured
            </div>
          )}
          
          {/* Lock overlay for inaccessible templates */}
          {!accessible && (
            <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-3 flex items-center gap-2">
                <Lock className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Requires {template.tier_required} plan
                </span>
              </div>
            </div>
          )}
        </div>
        
        {/* Content */}
        <div className="p-4">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 line-clamp-1">
              {template.name}
            </h3>
            <TierBadge tier={template.tier_required} />
          </div>
          
          <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
            {template.description}
          </p>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {(template.parameters || []).length} parameters
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {(template.usage_count || 0).toLocaleString()} uses
            </span>
          </div>
          
          {/* Tags */}
          {(template.tags || []).length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {(template.tags || []).slice(0, 3).map((tag) => (
                <span 
                  key={tag}
                  className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 text-xs rounded"
                >
                  {tag}
                </span>
              ))}
              {(template.tags || []).length > 3 && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  +{(template.tags || []).length - 3}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Template list item component
  const TemplateListItem = ({ template }: { template: Template }) => {
    const accessible = canAccessTemplate(template);
    
    return (
      <div
        onClick={() => handleTemplateClick(template)}
        className={`
          flex items-center gap-4 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700
          transition-all duration-200
          ${accessible 
            ? 'hover:border-primary-300 hover:shadow-md cursor-pointer' 
            : 'opacity-75 cursor-not-allowed'
          }
        `}
      >
        {/* Thumbnail */}
        <div className="h-16 w-16 flex-shrink-0 bg-gray-100 dark:bg-gray-700 rounded-lg flex items-center justify-center relative overflow-hidden">
          {template.thumbnail_url ? (
            <img 
              src={template.thumbnail_url} 
              alt={template.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <Box className="h-8 w-8 text-gray-400" />
          )}
          {!accessible && (
            <div className="absolute inset-0 bg-gray-900/50 flex items-center justify-center">
              <Lock className="h-4 w-4 text-white" />
            </div>
          )}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100 truncate">
              {template.name}
            </h3>
            {template.is_featured && (
              <Star className="h-4 w-4 text-amber-500 flex-shrink-0" />
            )}
            <TierBadge tier={template.tier_required} />
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
            {template.description}
          </p>
        </div>
        
        {/* Meta */}
        <div className="flex items-center gap-6 text-sm text-gray-500 dark:text-gray-400">
          <span>{(template.parameters || []).length} params</span>
          <span>{(template.usage_count || 0).toLocaleString()} uses</span>
          <ChevronRight className="h-5 w-5" />
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Deprecation Notice */}
      <div className="mb-6 bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-medium text-amber-800 dark:text-amber-200">
              Templates are being replaced by Starters
            </h3>
            <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
              We've introduced a new Starters system with better customization options. 
              Browse starter designs and remix them to create your own variations.
            </p>
            <Link
              to="/starters"
              className="mt-3 inline-flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-200 hover:text-amber-900 dark:hover:text-amber-100"
            >
              Go to Starter Designs
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Part Templates</h1>
          <p className="mt-1 text-gray-600 dark:text-gray-400">
            Browse and customize parametric templates for common mechanical parts.
          </p>
        </div>
        {user && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Template
          </button>
        )}
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        {/* Search with debouncing */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
          />
          {/* Show typing indicator when input differs from debounced value */}
          {searchInput !== debouncedSearchQuery && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <Loader2 className="h-4 w-4 animate-spin text-gray-400" />
            </div>
          )}
        </div>
        
        {/* Category Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <select
            value={selectedCategory}
            onChange={(e) => updateFilters({ category: e.target.value })}
            className="pl-10 pr-8 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent appearance-none bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 min-w-[180px]"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.slug} value={cat.slug}>
                {cat.name} ({cat.count})
              </option>
            ))}
          </select>
        </div>
        
        {/* Tier Filter */}
        <select
          value={tierFilter}
          onChange={(e) => updateFilters({ tier: e.target.value })}
          className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent appearance-none bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 min-w-[140px]"
        >
          <option value="">All Tiers</option>
          <option value="free">Free</option>
          <option value="basic">Basic</option>
          <option value="pro">Pro</option>
          <option value="enterprise">Enterprise</option>
        </select>
        
        {/* View Mode Toggle */}
        <div className="flex border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 ${viewMode === 'grid' ? 'bg-gray-100 dark:bg-gray-700' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}
            aria-label="Grid view"
          >
            <Grid className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 ${viewMode === 'list' ? 'bg-gray-100 dark:bg-gray-700' : 'hover:bg-gray-50 dark:hover:bg-gray-700'}`}
            aria-label="List view"
          >
            <List className="h-5 w-5 text-gray-600 dark:text-gray-400" />
          </button>
        </div>
      </div>

      {/* Category Pills */}
      {categories.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => updateFilters({ category: '' })}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              !selectedCategory
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            All
          </button>
          {categories.map((cat) => (
            <button
              key={cat.slug}
              onClick={() => updateFilters({ category: cat.slug })}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
                selectedCategory === cat.slug
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      )}

      {/* Content - show skeleton on initial load, inline spinner on search */}
      {initialLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
          <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
          <button
            onClick={() => fetchTemplates(false)}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Try Again
          </button>
        </div>
      ) : templates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Box className="h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600 dark:text-gray-400">No templates found matching your criteria.</p>
        </div>
      ) : (
        <div className="relative">
          {/* Search loading overlay - only covers the template grid */}
          {searchLoading && (
            <div className="absolute inset-0 bg-white/50 dark:bg-gray-800/50 flex items-center justify-center z-10">
              <Loader2 className="h-6 w-6 animate-spin text-primary-600" />
            </div>
          )}
          
          {viewMode === 'grid' ? (
            <div data-testid="template-grid" className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {templates.map((template) => (
                <TemplateCard key={template.id} template={template} />
              ))}
            </div>
          ) : (
            <div data-testid="template-list" className="space-y-3">
              {templates.map((template) => (
                <TemplateListItem key={template.id} template={template} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Results count */}
      {!initialLoading && templates.length > 0 && (
        <p className="mt-6 text-sm text-gray-500 dark:text-gray-400 text-center">
          Showing {templates.length} template{templates.length !== 1 ? 's' : ''}
        </p>
      )}
      
      {/* Create Template Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Create New Template</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4 space-y-4">
              {/* Name input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Template Name *
                </label>
                <input
                  type="text"
                  value={newTemplateName}
                  onChange={(e) => setNewTemplateName(e.target.value)}
                  placeholder="My Custom Template"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
              
              {/* Description input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  value={newTemplateDescription}
                  onChange={(e) => setNewTemplateDescription(e.target.value)}
                  placeholder="Describe what this template creates..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
              
              {/* Category selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Category
                </label>
                <select
                  value={newTemplateCategory}
                  onChange={(e) => setNewTemplateCategory(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                >
                  <option value="custom">Custom</option>
                  <option value="enclosures">Enclosures</option>
                  <option value="mechanical">Mechanical</option>
                  <option value="connectors">Connectors</option>
                  <option value="organizational">Organizational</option>
                  <option value="decorative">Decorative</option>
                </select>
              </div>
              
              {/* Tags input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={newTemplateTags}
                  onChange={(e) => setNewTemplateTags(e.target.value)}
                  placeholder="3d-printable, enclosure, electronics"
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
                />
              </div>
            </div>
            
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!token || !newTemplateName.trim()) return;
                  
                  setIsCreating(true);
                  try {
                    const response = await fetch(`${API_BASE}/templates`, {
                      method: 'POST',
                      headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json',
                      },
                      body: JSON.stringify({
                        name: newTemplateName,
                        description: newTemplateDescription || null,
                        category: newTemplateCategory,
                        tags: newTemplateTags.split(',').map(t => t.trim()).filter(Boolean),
                        parameters: {},
                        default_values: {},
                        is_public: false,
                      }),
                    });
                    
                    if (!response.ok) {
                      const error = await response.json();
                      throw new Error(error.detail || 'Failed to create template');
                    }
                    
                    const created = await response.json();
                    setShowCreateModal(false);
                    setNewTemplateName('');
                    setNewTemplateDescription('');
                    setNewTemplateCategory('custom');
                    setNewTemplateTags('');
                    
                    // Navigate to the new template
                    navigate(`/templates/${created.slug}`);
                  } catch (err) {
                    setError(err instanceof Error ? err.message : 'Failed to create template');
                  } finally {
                    setIsCreating(false);
                  }
                }}
                disabled={isCreating || !newTemplateName.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Create Template
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
