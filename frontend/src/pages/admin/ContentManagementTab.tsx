/**
 * Content Management Tab Component (US-10.10).
 *
 * FAQ and article management: list, create/edit, publish/unpublish,
 * category management, and content analytics.
 */

import { useCallback, useEffect, useState } from 'react';
import {
  Plus,
  Search,
  RefreshCw,
  Pencil,
  Trash2,
  BarChart3,
  X,
  Eye,
  EyeOff,
  Folder,
} from 'lucide-react';
import { adminApi } from '../../lib/api/admin';
import type {
  ContentItem,
  ContentItemListResponse,
  ContentItemCreateRequest,
  ContentItemUpdateRequest,
  ContentCategory,
  ContentCategoryCreateRequest,
  ContentAnalytics,
} from '../../types/admin';

// =============================================================================
// Sub-views
// =============================================================================

type ContentView = 'faqs' | 'articles' | 'categories' | 'analytics';

// =============================================================================
// Create / Edit Content Modal
// =============================================================================

interface ContentFormModalProps {
  item: ContentItem | null;
  contentType: 'faq' | 'article';
  categories: ContentCategory[];
  onClose: () => void;
  onSaved: () => void;
}

function ContentFormModal({ item, contentType, categories, onClose, onSaved }: ContentFormModalProps) {
  const isEdit = !!item;
  const [title, setTitle] = useState(item?.title ?? '');
  const [body, setBody] = useState(item?.body ?? '');
  const [category, setCategory] = useState(item?.category ?? '');
  const [status, setStatus] = useState(item?.status ?? 'draft');
  const [displayOrder, setDisplayOrder] = useState<number>(item?.display_order ?? 0);
  const [isFeatured, setIsFeatured] = useState(item?.is_featured ?? false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (isEdit) {
        const payload: ContentItemUpdateRequest = {
          title,
          body,
          category: category || undefined,
          status,
          display_order: displayOrder,
          is_featured: isFeatured,
        };
        if (contentType === 'faq') {
          await adminApi.content.updateFaq(item!.id, payload);
        } else {
          await adminApi.content.updateArticle(item!.id, payload);
        }
      } else {
        const payload: ContentItemCreateRequest = {
          title,
          body: body || undefined,
          category: category || undefined,
          status,
          display_order: displayOrder,
          is_featured: isFeatured,
        };
        if (contentType === 'faq') {
          await adminApi.content.createFaq(payload);
        } else {
          await adminApi.content.createArticle(payload);
        }
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {isEdit ? 'Edit' : 'Create'} {contentType === 'faq' ? 'FAQ' : 'Article'}
          </h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Title *</label>
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Body</label>
            <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={8} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
                <option value="">No Category</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.slug}>{cat.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Status</label>
              <select value={status} onChange={(e) => setStatus(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Display Order</label>
              <input type="number" value={displayOrder} onChange={(e) => setDisplayOrder(Number(e.target.value))} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
            </div>
            <div className="flex items-end pb-2">
              <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <input type="checkbox" checked={isFeatured} onChange={(e) => setIsFeatured(e.target.checked)} className="rounded" />
                Featured
              </label>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Saving…' : isEdit ? 'Update' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Create Category Modal
// =============================================================================

interface CategoryModalProps {
  onClose: () => void;
  onSaved: () => void;
}

function CategoryModal({ onClose, onSaved }: CategoryModalProps) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [displayOrder, setDisplayOrder] = useState(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSlug(name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, ''));
  }, [name]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body: ContentCategoryCreateRequest = { name, slug, description: description || undefined, display_order: displayOrder };
      await adminApi.content.createCategory(body);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create category');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Create Category</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"><X className="h-5 w-5" /></button>
        </div>
        {error && <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Name *</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} required className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Slug</label>
            <input type="text" value={slug} onChange={(e) => setSlug(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Description</label>
            <input type="text" value={description} onChange={(e) => setDescription(e.target.value)} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Display Order</label>
            <input type="number" value={displayOrder} onChange={(e) => setDisplayOrder(Number(e.target.value))} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
            <button type="submit" disabled={saving} className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">{saving ? 'Creating…' : 'Create'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

// =============================================================================
// Content List Table
// =============================================================================

interface ContentListTableProps {
  items: ContentItem[];
  onEdit: (item: ContentItem) => void;
  onDelete: (item: ContentItem) => void;
  onPublish: (item: ContentItem) => void;
}

function ContentListTable({ items, onEdit, onDelete, onPublish }: ContentListTableProps) {
  if (items.length === 0) {
    return <div className="py-12 text-center text-sm text-gray-500">No items found.</div>;
  }

  return (
    <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Title</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Category</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Status</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Views</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Helpful</th>
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Updated</th>
            <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 dark:text-gray-400">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                <div className="max-w-xs truncate">{item.title}</div>
                {item.is_featured && <span className="ml-2 inline-flex rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400">Featured</span>}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{item.category ?? '—'}</td>
              <td className="px-4 py-3">
                <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                  item.status === 'published' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' :
                  item.status === 'draft' ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400' :
                  'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-400'
                }`}>
                  {item.status}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{item.view_count}</td>
              <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                {item.helpful_count} / {item.not_helpful_count}
              </td>
              <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">
                {item.updated_at ? new Date(item.updated_at).toLocaleDateString() : new Date(item.created_at).toLocaleDateString()}
              </td>
              <td className="whitespace-nowrap px-4 py-3 text-right">
                <div className="flex justify-end gap-1">
                  <button onClick={() => onPublish(item)} title={item.status === 'published' ? 'Unpublish' : 'Publish'} className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700">
                    {item.status === 'published' ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                  <button onClick={() => onEdit(item)} title="Edit" className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700">
                    <Pencil className="h-4 w-4" />
                  </button>
                  <button onClick={() => onDelete(item)} title="Delete" className="rounded p-1 text-gray-400 hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-900/30">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

/**
 * ContentManagementTab provides full CRUD for FAQs, articles, and categories
 * plus content analytics.
 */
export function ContentManagementTab() {
  const [view, setView] = useState<ContentView>('faqs');
  const [items, setItems] = useState<ContentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const pageSize = 20;

  // Categories
  const [categories, setCategories] = useState<ContentCategory[]>([]);
  const [showCategoryModal, setShowCategoryModal] = useState(false);

  // Content form
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editItem, setEditItem] = useState<ContentItem | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<ContentItem | null>(null);

  // Analytics
  const [analytics, setAnalytics] = useState<ContentAnalytics | null>(null);

  const fetchCategories = useCallback(async () => {
    try {
      const data = await adminApi.content.listCategories();
      setCategories(data);
    } catch {
      // silent
    }
  }, []);

  const fetchItems = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = {
        page,
        page_size: pageSize,
        category: categoryFilter || undefined,
        status: statusFilter || undefined,
      };
      let data: ContentItemListResponse;
      if (view === 'faqs') {
        data = await adminApi.content.listFaqs(params);
      } else {
        data = await adminApi.content.listArticles(params);
      }
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError('Failed to load content');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [view, page, categoryFilter, statusFilter]);

  const fetchAnalytics = useCallback(async () => {
    try {
      const data = await adminApi.content.getAnalytics();
      setAnalytics(data);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  useEffect(() => {
    if (view === 'faqs' || view === 'articles') {
      fetchItems();
    }
    if (view === 'analytics') {
      fetchAnalytics();
    }
  }, [view, fetchItems, fetchAnalytics]);

  const handlePublish = async (item: ContentItem) => {
    try {
      if (item.status === 'published') {
        // Unpublish by updating status
        if (item.content_type === 'faq') {
          await adminApi.content.updateFaq(item.id, { status: 'draft' });
        } else {
          await adminApi.content.updateArticle(item.id, { status: 'draft' });
        }
      } else {
        if (item.content_type === 'faq') {
          await adminApi.content.publishFaq(item.id);
        } else {
          await adminApi.content.publishArticle(item.id);
        }
      }
      fetchItems();
    } catch (err) {
      console.error('Failed to update publish status', err);
    }
  };

  const handleDelete = async (item: ContentItem) => {
    try {
      if (view === 'faqs' || item.content_type === 'faq') {
        await adminApi.content.deleteFaq(item.id);
      } else {
        await adminApi.content.deleteArticle(item.id);
      }
      setDeleteConfirm(null);
      fetchItems();
    } catch (err) {
      console.error('Failed to delete', err);
    }
  };

  // -------------------------------------------------------------------------
  // Render — Analytics view
  // -------------------------------------------------------------------------

  if (view === 'analytics') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Content Analytics</h2>
          <button onClick={() => setView('faqs')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back to FAQs</button>
        </div>
        {!analytics ? (
          <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total FAQs" value={analytics.total_faqs} />
            <StatCard label="Total Articles" value={analytics.total_articles} />
            <StatCard label="Published FAQs" value={analytics.published_faqs} />
            <StatCard label="Published Articles" value={analytics.published_articles} />
            <StatCard label="Total Views" value={analytics.total_views.toLocaleString()} />
            <StatCard label="Helpful Votes" value={analytics.total_helpful.toLocaleString()} />
            <StatCard label="Not Helpful Votes" value={analytics.total_not_helpful.toLocaleString()} />
            <StatCard label="Categories" value={categories.length} />
          </div>
        )}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — Categories view
  // -------------------------------------------------------------------------

  if (view === 'categories') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Content Categories</h2>
          <div className="flex gap-2">
            <button onClick={() => setView('faqs')} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Back to FAQs</button>
            <button onClick={() => setShowCategoryModal(true)} className="flex items-center gap-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"><Plus className="h-4 w-4" /> New Category</button>
          </div>
        </div>
        {categories.length === 0 ? (
          <div className="py-12 text-center text-sm text-gray-500">No categories yet.</div>
        ) : (
          <div className="overflow-x-auto rounded-lg border dark:border-gray-700">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Name</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Slug</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Description</th>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500 dark:text-gray-400">Order</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-900">
                {categories.map((cat) => (
                  <tr key={cat.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">{cat.name}</td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-500 dark:text-gray-400">{cat.slug}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{cat.description ?? '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400">{cat.display_order}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {showCategoryModal && <CategoryModal onClose={() => setShowCategoryModal(false)} onSaved={() => { setShowCategoryModal(false); fetchCategories(); }} />}
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // Render — List view (FAQs or Articles)
  // -------------------------------------------------------------------------

  const contentType = view === 'faqs' ? 'faq' : 'article';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          Content Management
        </h2>
        <div className="flex gap-2">
          <button onClick={() => setView('analytics')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><BarChart3 className="h-4 w-4" /> Analytics</button>
          <button onClick={() => setView('categories')} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><Folder className="h-4 w-4" /> Categories</button>
          <button onClick={() => setShowCreateModal(true)} className="flex items-center gap-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"><Plus className="h-4 w-4" /> New {contentType === 'faq' ? 'FAQ' : 'Article'}</button>
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
        <button onClick={() => { setView('faqs'); setPage(1); }} className={`px-3 py-1.5 text-sm font-medium rounded-t ${view === 'faqs' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>FAQs</button>
        <button onClick={() => { setView('articles'); setPage(1); }} className={`px-3 py-1.5 text-sm font-medium rounded-t ${view === 'articles' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400'}`}>Articles</button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
          <input type="text" placeholder="Search…" value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 pl-9 pr-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white" />
        </div>
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
          <option value="">All Status</option>
          <option value="draft">Draft</option>
          <option value="published">Published</option>
          <option value="archived">Archived</option>
        </select>
        <select value={categoryFilter} onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }} className="rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
          <option value="">All Categories</option>
          {categories.map((cat) => (<option key={cat.id} value={cat.slug}>{cat.name}</option>))}
        </select>
        <button onClick={fetchItems} className="flex items-center gap-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:text-gray-300"><RefreshCw className="h-4 w-4" /> Refresh</button>
      </div>

      {/* Loading / Error */}
      {isLoading && <div className="flex justify-center py-12"><RefreshCw className="h-6 w-6 animate-spin text-gray-400" /></div>}
      {error && <div className="py-8 text-center text-red-500">{error}</div>}

      {/* Table */}
      {!isLoading && !error && (
        <>
          <ContentListTable items={items} onEdit={(item) => setEditItem(item)} onDelete={(item) => setDeleteConfirm(item)} onPublish={handlePublish} />

          {total > pageSize && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-500 dark:text-gray-400">Showing {((page - 1) * pageSize) + 1}–{Math.min(page * pageSize, total)} of {total}</span>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Previous</button>
                <button onClick={() => setPage((p) => p + 1)} disabled={page * pageSize >= total} className="rounded-md border px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-gray-300">Next</button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      {(showCreateModal || editItem) && (
        <ContentFormModal
          item={editItem}
          contentType={contentType as 'faq' | 'article'}
          categories={categories}
          onClose={() => { setShowCreateModal(false); setEditItem(null); }}
          onSaved={() => { setShowCreateModal(false); setEditItem(null); fetchItems(); }}
        />
      )}

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-full max-w-sm rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Delete Content</h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Are you sure you want to delete &quot;{deleteConfirm.title}&quot;?</p>
            <div className="mt-4 flex justify-end gap-3">
              <button onClick={() => setDeleteConfirm(null)} className="rounded-md border border-gray-300 px-4 py-2 text-sm dark:border-gray-600 dark:text-gray-300">Cancel</button>
              <button onClick={() => handleDelete(deleteConfirm)} className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Stat Card helper
// =============================================================================

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}
