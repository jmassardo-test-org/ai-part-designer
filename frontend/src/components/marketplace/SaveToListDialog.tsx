/**
 * SaveToListDialog component for selecting which lists to save a design to.
 */

import { 
  X, 
  Plus, 
  Check, 
  Loader2,
  Folder,
  Heart
} from 'lucide-react';
import { useState, useEffect } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import * as api from '@/lib/marketplace';
import type { DesignList } from '@/types/marketplace';

interface SaveToListDialogProps {
  isOpen: boolean;
  onClose: () => void;
  designId: string;
  onSaved?: () => void;
}

export function SaveToListDialog({
  isOpen,
  onClose,
  designId,
  onSaved,
}: SaveToListDialogProps) {
  const { token } = useAuth();
  const [lists, setLists] = useState<DesignList[]>([]);
  const [selectedLists, setSelectedLists] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showCreateNew, setShowCreateNew] = useState(false);
  const [newListName, setNewListName] = useState('');
  const [creating, setCreating] = useState(false);

  // Load lists and check which ones contain the design
  useEffect(() => {
    if (!isOpen || !token) return;

    async function loadData() {
      setLoading(true);
      try {
        const [allLists, saveStatus] = await Promise.all([
          api.getMyLists(token!),
          api.checkSaveStatus(designId, token!),
        ]);
        setLists(allLists);
        setSelectedLists(new Set(saveStatus.in_lists));
      } catch (err) {
        console.error('Failed to load lists:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [isOpen, token, designId]);

  const toggleList = (listId: string) => {
    const newSelected = new Set(selectedLists);
    if (newSelected.has(listId)) {
      newSelected.delete(listId);
    } else {
      newSelected.add(listId);
    }
    setSelectedLists(newSelected);
  };

  const handleSave = async () => {
    if (!token) return;

    setSaving(true);
    try {
      // Save to selected lists
      await api.saveDesign(designId, Array.from(selectedLists), token);
      onSaved?.();
      onClose();
    } catch (err) {
      console.error('Failed to save:', err);
    } finally {
      setSaving(false);
    }
  };

  const handleCreateList = async () => {
    if (!token || !newListName.trim()) return;

    setCreating(true);
    try {
      const newList = await api.createList({ name: newListName.trim() }, token);
      setLists([...lists, newList]);
      setSelectedLists(new Set([...selectedLists, newList.id]));
      setNewListName('');
      setShowCreateNew(false);
    } catch (err) {
      console.error('Failed to create list:', err);
    } finally {
      setCreating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Dialog */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Save to Lists
          </h2>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
            </div>
          ) : (
            <div className="space-y-2">
              {lists.length === 0 && !showCreateNew ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                  <Heart className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No lists yet</p>
                  <p className="text-sm">Create your first list to organize designs</p>
                </div>
              ) : (
                lists.map((list) => (
                  <button
                    key={list.id}
                    onClick={() => toggleList(list.id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                      selectedLists.has(list.id)
                        ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${list.color}20` }}
                    >
                      <Folder className="w-4 h-4" style={{ color: list.color }} />
                    </div>
                    <div className="flex-1 text-left">
                      <div className="font-medium text-gray-900 dark:text-white">
                        {list.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {list.item_count} {list.item_count === 1 ? 'design' : 'designs'}
                      </div>
                    </div>
                    {selectedLists.has(list.id) && (
                      <Check className="w-5 h-5 text-indigo-500" />
                    )}
                  </button>
                ))
              )}

              {/* Create new list form */}
              {showCreateNew ? (
                <div className="p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
                  <input
                    type="text"
                    value={newListName}
                    onChange={(e) => setNewListName(e.target.value)}
                    placeholder="List name..."
                    autoFocus
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCreateList();
                      if (e.key === 'Escape') setShowCreateNew(false);
                    }}
                  />
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={handleCreateList}
                      disabled={!newListName.trim() || creating}
                      className="flex-1 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                    >
                      {creating ? (
                        <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                      ) : (
                        'Create'
                      )}
                    </button>
                    <button
                      onClick={() => setShowCreateNew(false)}
                      className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowCreateNew(true)}
                  className="w-full flex items-center gap-2 p-3 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
                >
                  <Plus className="w-5 h-5" />
                  <span>Create new list</span>
                </button>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex-1 py-2 bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {saving && <Loader2 className="w-4 h-4 animate-spin" />}
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

export default SaveToListDialog;
