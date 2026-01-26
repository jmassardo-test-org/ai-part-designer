/**
 * Templates browsing page.
 * Allows users to browse, filter, and customize parametric templates.
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
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
  Lock
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';

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

// API base URL from environment
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function TemplatesPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // State
  const [templates, setTemplates] = useState<Template[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  
  // Filter state from URL params
  const searchQuery = searchParams.get('q') || '';
  const selectedCategory = searchParams.get('category') || '';
  const tierFilter = searchParams.get('tier') || '';

  // Fetch templates
  const fetchTemplates = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.set('category', selectedCategory);
      if (searchQuery) params.set('search', searchQuery);
      
      const response = await fetch(`${API_BASE}/templates?${params}`);
      if (!response.ok) throw new Error('Failed to fetch templates');
      
      const data = await response.json();
      setTemplates(data.templates || data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load templates');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, searchQuery]);

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

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  // Update URL params
  const updateFilters = (updates: Record<string, string>) => {
    const newParams = new URLSearchParams(searchParams);
    Object.entries(updates).forEach(([key, value]) => {
      if (value) {
        newParams.set(key, value);
      } else {
        newParams.delete(key);
      }
    });
    setSearchParams(newParams);
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
          relative bg-white rounded-lg border border-gray-200 overflow-hidden
          transition-all duration-200
          ${accessible 
            ? 'hover:border-primary-300 hover:shadow-md cursor-pointer' 
            : 'opacity-75 cursor-not-allowed'
          }
        `}
      >
        {/* Thumbnail */}
        <div className="aspect-video bg-gray-100 flex items-center justify-center relative">
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
              <div className="bg-white rounded-lg p-3 flex items-center gap-2">
                <Lock className="h-4 w-4 text-gray-600" />
                <span className="text-sm font-medium text-gray-700">
                  Requires {template.tier_required} plan
                </span>
              </div>
            </div>
          )}
        </div>
        
        {/* Content */}
        <div className="p-4">
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-semibold text-gray-900 line-clamp-1">
              {template.name}
            </h3>
            <TierBadge tier={template.tier_required} />
          </div>
          
          <p className="text-sm text-gray-600 line-clamp-2 mb-3">
            {template.description}
          </p>
          
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {template.parameters.length} parameters
            </span>
            <span className="text-xs text-gray-500">
              {template.usage_count.toLocaleString()} uses
            </span>
          </div>
          
          {/* Tags */}
          {template.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-3">
              {template.tags.slice(0, 3).map((tag) => (
                <span 
                  key={tag}
                  className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded"
                >
                  {tag}
                </span>
              ))}
              {template.tags.length > 3 && (
                <span className="text-xs text-gray-400">
                  +{template.tags.length - 3}
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
          flex items-center gap-4 p-4 bg-white rounded-lg border border-gray-200
          transition-all duration-200
          ${accessible 
            ? 'hover:border-primary-300 hover:shadow-md cursor-pointer' 
            : 'opacity-75 cursor-not-allowed'
          }
        `}
      >
        {/* Thumbnail */}
        <div className="h-16 w-16 flex-shrink-0 bg-gray-100 rounded-lg flex items-center justify-center relative overflow-hidden">
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
            <h3 className="font-semibold text-gray-900 truncate">
              {template.name}
            </h3>
            {template.is_featured && (
              <Star className="h-4 w-4 text-amber-500 flex-shrink-0" />
            )}
            <TierBadge tier={template.tier_required} />
          </div>
          <p className="text-sm text-gray-600 truncate">
            {template.description}
          </p>
        </div>
        
        {/* Meta */}
        <div className="flex items-center gap-6 text-sm text-gray-500">
          <span>{template.parameters.length} params</span>
          <span>{template.usage_count.toLocaleString()} uses</span>
          <ChevronRight className="h-5 w-5" />
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Part Templates</h1>
        <p className="mt-1 text-gray-600">
          Browse and customize parametric templates for common mechanical parts.
        </p>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => updateFilters({ q: e.target.value })}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
          />
        </div>
        
        {/* Category Filter */}
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <select
            value={selectedCategory}
            onChange={(e) => updateFilters({ category: e.target.value })}
            className="pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent appearance-none bg-white min-w-[180px]"
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
          className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent appearance-none bg-white min-w-[140px]"
        >
          <option value="">All Tiers</option>
          <option value="free">Free</option>
          <option value="basic">Basic</option>
          <option value="pro">Pro</option>
          <option value="enterprise">Enterprise</option>
        </select>
        
        {/* View Mode Toggle */}
        <div className="flex border border-gray-300 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-2 ${viewMode === 'grid' ? 'bg-gray-100' : 'hover:bg-gray-50'}`}
            aria-label="Grid view"
          >
            <Grid className="h-5 w-5 text-gray-600" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-2 ${viewMode === 'list' ? 'bg-gray-100' : 'hover:bg-gray-50'}`}
            aria-label="List view"
          >
            <List className="h-5 w-5 text-gray-600" />
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
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
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
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {cat.name}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={fetchTemplates}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          >
            Try Again
          </button>
        </div>
      ) : templates.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12">
          <Box className="h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-600">No templates found matching your criteria.</p>
        </div>
      ) : viewMode === 'grid' ? (
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

      {/* Results count */}
      {!loading && templates.length > 0 && (
        <p className="mt-6 text-sm text-gray-500 text-center">
          Showing {templates.length} template{templates.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
}
