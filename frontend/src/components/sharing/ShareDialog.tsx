/**
 * ShareDialog Component - Share designs with other users.
 */

import {
  X,
  Link2,
  Copy,
  Check,
  Mail,
  Eye,
  MessageSquare,
  Edit3,
  Trash2,
  User,
  Loader2,
  Globe,
} from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// =============================================================================
// Types
// =============================================================================

interface Share {
  id: string;
  shared_with_id: string;
  shared_with_email: string;
  shared_with_name: string;
  permission: 'view' | 'comment' | 'edit';
  shared_at: string;
}

interface ShareDialogProps {
  designId: string;
  designName: string;
  isOpen: boolean;
  onClose: () => void;
}

// =============================================================================
// ShareDialog Component
// =============================================================================

export function ShareDialog({ designId, designName, isOpen, onClose }: ShareDialogProps) {
  const { token } = useAuth();

  // State
  const [email, setEmail] = useState('');
  const [permission, setPermission] = useState<'view' | 'comment' | 'edit'>('view');
  const [shares, setShares] = useState<Share[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingShares] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Link sharing
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [linkCopied, setLinkCopied] = useState(false);
  const [isCreatingLink, setIsCreatingLink] = useState(false);

  // Share with user
  const handleShare = async () => {
    if (!email.trim()) return;

    try {
      setIsLoading(true);
      setError(null);
      setSuccess(null);

      const response = await fetch(`${API_BASE}/shares/designs/${designId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          email,
          permission,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to share design');
      }

      const share = await response.json();
      setShares([share, ...shares]);
      setEmail('');
      setSuccess(`Shared with ${share.shared_with_email}`);
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to share design');
    } finally {
      setIsLoading(false);
    }
  };

  // Update share permission
  const handleUpdatePermission = async (shareId: string, newPermission: string) => {
    try {
      const response = await fetch(`${API_BASE}/shares/${shareId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ permission: newPermission }),
      });

      if (response.ok) {
        setShares(shares.map(s =>
          s.id === shareId ? { ...s, permission: newPermission as Share['permission'] } : s
        ));
      }
    } catch (err) {
      console.error('Failed to update permission:', err);
    }
  };

  // Revoke share
  const handleRevoke = async (shareId: string) => {
    try {
      const response = await fetch(`${API_BASE}/shares/${shareId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setShares(shares.filter(s => s.id !== shareId));
      }
    } catch (err) {
      console.error('Failed to revoke share:', err);
    }
  };

  // Create share link
  const handleCreateLink = async () => {
    try {
      setIsCreatingLink(true);
      const response = await fetch(`${API_BASE}/shares/designs/${designId}/link`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          permission: 'view',
          expires_in_days: 7,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setShareLink(data.link);
      }
    } catch (err) {
      console.error('Failed to create link:', err);
    } finally {
      setIsCreatingLink(false);
    }
  };

  // Copy link to clipboard
  const handleCopyLink = async () => {
    if (shareLink) {
      await navigator.clipboard.writeText(shareLink);
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    }
  };

  // Permission options
  const permissionOptions = [
    { value: 'view', label: 'Can view', icon: Eye },
    { value: 'comment', label: 'Can comment', icon: MessageSquare },
    { value: 'edit', label: 'Can edit', icon: Edit3 },
  ];

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
          <div>
            <h2 className="text-lg font-semibold dark:text-gray-100">Share "{designName}"</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Invite people to view or collaborate</p>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {/* Share with email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Invite by email
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Enter email address"
                  className="w-full pl-9 pr-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500"
                  onKeyDown={(e) => e.key === 'Enter' && handleShare()}
                />
              </div>
              <select
                value={permission}
                onChange={(e) => setPermission(e.target.value as typeof permission)}
                className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100"
              >
                {permissionOptions.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <button
                onClick={handleShare}
                disabled={isLoading || !email.trim()}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 flex items-center gap-2"
              >
                {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Share'}
              </button>
            </div>

            {/* Error/Success messages */}
            {error && (
              <p className="mt-2 text-sm text-red-600">{error}</p>
            )}
            {success && (
              <p className="mt-2 text-sm text-green-600">{success}</p>
            )}
          </div>

          {/* Link sharing */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Get link
            </label>
            {shareLink ? (
              <div className="flex gap-2">
                <div className="flex-1 flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-700 border dark:border-gray-600 rounded-lg">
                  <Globe className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-600 dark:text-gray-300 truncate">{shareLink}</span>
                </div>
                <button
                  onClick={handleCopyLink}
                  className="px-3 py-2 border dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  {linkCopied ? (
                    <>
                      <Check className="w-4 h-4 text-green-600" />
                      <span className="text-green-600">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4" />
                      Copy
                    </>
                  )}
                </button>
              </div>
            ) : (
              <button
                onClick={handleCreateLink}
                disabled={isCreatingLink}
                className="flex items-center gap-2 px-4 py-2 border dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                {isCreatingLink ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Link2 className="w-4 h-4" />
                )}
                Create shareable link
              </button>
            )}
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Anyone with the link can view. Link expires in 7 days.
            </p>
          </div>

          {/* Shared with list */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Shared with ({shares.length})
            </label>
            {isLoadingShares ? (
              <div className="flex justify-center py-4">
                <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
              </div>
            ) : shares.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                Not shared with anyone yet
              </p>
            ) : (
              <div className="space-y-2">
                {shares.map(share => (
                  <div
                    key={share.id}
                    className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700"
                  >
                    <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-600 flex items-center justify-center">
                      <User className="w-4 h-4 text-gray-500 dark:text-gray-300" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate dark:text-gray-100">
                        {share.shared_with_name}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                        {share.shared_with_email}
                      </p>
                    </div>
                    <select
                      value={share.permission}
                      onChange={(e) => handleUpdatePermission(share.id, e.target.value)}
                      className="text-sm px-2 py-1 border dark:border-gray-600 rounded focus:ring-2 focus:ring-primary-500 bg-white dark:bg-gray-700 dark:text-gray-100"
                    >
                      {permissionOptions.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => handleRevoke(share.id)}
                      className="p-1 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded"
                      title="Remove access"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t dark:border-gray-700 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
