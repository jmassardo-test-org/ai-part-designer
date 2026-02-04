/**
 * Dialog for publishing a design to the marketplace.
 * 
 * Allows users to set category, tags, and description before publishing.
 */

import { useState, useEffect } from 'react';
import {
  X,
  Globe,
  Tag,
  Loader2,
  CheckCircle,
  AlertCircle,
  Info,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { getCategories, publishDesign, unpublishDesign } from '@/lib/marketplace';
import type { CategoryResponse } from '@/types/marketplace';

interface PublishToMarketplaceDialogProps {
  isOpen: boolean;
  onClose: () => void;
  designId: string;
  designName: string;
  currentCategory?: string | null;
  currentTags?: string[];
  isPublished?: boolean;
  onPublished?: () => void;
}

export function PublishToMarketplaceDialog({
  isOpen,
  onClose,
  designId,
  designName,
  currentCategory,
  currentTags = [],
  isPublished = false,
  onPublished,
}: PublishToMarketplaceDialogProps) {
  const { token } = useAuth();
  
  // Form state
  const [category, setCategory] = useState(currentCategory || '');
  const [tags, setTags] = useState<string[]>(currentTags);
  const [tagInput, setTagInput] = useState('');
  const [description, setDescription] = useState('');
  
  // UI state
  const [categories, setCategories] = useState<CategoryResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  
  // Fetch categories on mount
  useEffect(() => {
    if (!isOpen || !token) return;
    
    const fetchCategoriesData = async () => {
      setIsLoading(true);
      try {
        const data = await getCategories(token);
        setCategories(data);
      } catch (err) {
        console.error('Failed to fetch categories:', err);
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchCategoriesData();
  }, [isOpen, token]);
  
  // Reset form when dialog opens
  // Note: currentTags is intentionally excluded from deps to prevent infinite loops
  // when a default empty array is passed. The tags are only initialized when dialog opens.
  useEffect(() => {
    if (isOpen) {
      setCategory(currentCategory || '');
      setTags(currentTags);
      setTagInput('');
      setDescription('');
      setError(null);
      setSuccess(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, currentCategory]);
  
  const handleAddTag = () => {
    const trimmed = tagInput.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed) && tags.length < 10) {
      setTags([...tags, trimmed]);
      setTagInput('');
    }
  };
  
  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter(t => t !== tag));
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      handleAddTag();
    }
  };
  
  const handlePublish = async () => {
    if (!token) return;
    
    if (!category) {
      setError('Please select a category');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await publishDesign(designId, { category, tags }, token);
      setSuccess(true);
      onPublished?.();
      
      // Auto close after success
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to publish design');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleUnpublish = async () => {
    if (!token) return;
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await unpublishDesign(designId, token);
      setSuccess(true);
      onPublished?.();
      
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to unpublish design');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div 
        className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col"
        data-testid="publish-dialog"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Globe className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {isPublished ? 'Marketplace Settings' : 'Publish to Marketplace'}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {designName}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Success message */}
          {success && (
            <div className="flex items-center gap-3 p-4 bg-green-50 dark:bg-green-900/30 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
              <span className="text-green-700 dark:text-green-300">
                {isPublished ? 'Updated successfully!' : 'Design published successfully!'}
              </span>
            </div>
          )}
          
          {/* Error message */}
          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/30 rounded-lg">
              <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
              <span className="text-red-700 dark:text-red-300">{error}</span>
            </div>
          )}
          
          {/* Info box for new publish */}
          {!isPublished && (
            <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
              <Info className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-700 dark:text-blue-300">
                <p className="font-medium mb-1">Share your design with the community</p>
                <p className="text-blue-600 dark:text-blue-400">
                  Published designs are visible to all users and can be saved or remixed.
                  You can unpublish at any time.
                </p>
              </div>
            </div>
          )}
          
          {/* Category selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Category *
            </label>
            <select
              value={category}
              onChange={e => setCategory(e.target.value)}
              disabled={isLoading || isSubmitting}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50"
              data-testid="category-select"
            >
              <option value="">Select a category...</option>
              {categories.map(cat => (
                <option key={cat.slug} value={cat.slug}>
                  {cat.name} ({cat.design_count} designs)
                </option>
              ))}
            </select>
          </div>
          
          {/* Tags input */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <div className="flex items-center gap-2">
                <Tag className="w-4 h-4" />
                Tags (up to 10)
              </div>
            </label>
            
            {/* Tag pills */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {tags.map(tag => (
                  <span
                    key={tag}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 rounded-full text-sm text-gray-700 dark:text-gray-300"
                  >
                    {tag}
                    <button
                      onClick={() => handleRemoveTag(tag)}
                      className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-full"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            
            <div className="flex gap-2">
              <input
                type="text"
                value={tagInput}
                onChange={e => setTagInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Add a tag..."
                disabled={tags.length >= 10 || isSubmitting}
                className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 disabled:opacity-50"
                data-testid="tag-input"
              />
              <button
                onClick={handleAddTag}
                disabled={!tagInput.trim() || tags.length >= 10 || isSubmitting}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Add
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Press Enter or comma to add tags
            </p>
          </div>
        </div>
        
        {/* Footer */}
        <div className="flex items-center justify-between p-4 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          {isPublished ? (
            <>
              <button
                onClick={handleUnpublish}
                disabled={isSubmitting}
                className="px-4 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
              >
                Unpublish
              </button>
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePublish}
                  disabled={isSubmitting || !category}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                  Update
                </button>
              </div>
            </>
          ) : (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handlePublish}
                disabled={isSubmitting || !category}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                data-testid="publish-submit"
              >
                {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                <Globe className="w-4 h-4" />
                Publish
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
