/**
 * Comments Panel for designs.
 *
 * Threaded comments with markdown support and @mentions.
 */

import {
  MessageCircle,
  Send,
  MoreVertical,
  Edit3,
  Trash2,
  Reply,
  X,
  AtSign,
  Bold,
  Italic,
  Link2,
  Check,
  Clock,
} from 'lucide-react';
import { useState, useEffect, useRef } from 'react';
import { apiClient } from '../../lib/api/client';

// --- Types ---

interface CommentAuthor {
  id: string;
  display_name: string;
  email: string;
  avatar_url: string | null;
}

interface Comment {
  id: string;
  design_id: string;
  author: CommentAuthor;
  content: string;
  parent_id: string | null;
  position: { x: number; y: number; z: number } | null;
  camera: { x: number; y: number; z: number } | null;
  reply_count: number;
  is_edited: boolean;
  created_at: string;
  updated_at: string;
}

interface CommentsPanelProps {
  designId: string;
  className?: string;
}

interface CommentItemProps {
  comment: Comment;
  currentUserId: string;
  onReply: (comment: Comment) => void;
  onEdit: (comment: Comment) => void;
  onDelete: (commentId: string) => void;
  onNavigateToPosition?: (position: { x: number; y: number; z: number }) => void;
  isReply?: boolean;
  replies?: Comment[];
}

// --- Helper Functions ---

function getTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n.charAt(0))
    .slice(0, 2)
    .join('')
    .toUpperCase();
}

// --- Components ---

/**
 * Single comment item with actions.
 */
function CommentItem({
  comment,
  currentUserId,
  onReply,
  onEdit,
  onDelete,
  onNavigateToPosition,
  isReply = false,
  replies = [],
}: CommentItemProps) {
  const [showActions, setShowActions] = useState(false);
  const [showReplies, setShowReplies] = useState(true);
  const isOwner = comment.author.id === currentUserId;

  return (
    <div className={`${isReply ? 'ml-8 border-l-2 border-gray-100 pl-4' : ''}`}>
      <div
        className="py-3 group"
        onMouseEnter={() => setShowActions(true)}
        onMouseLeave={() => setShowActions(false)}
      >
        <div className="flex gap-3">
          {/* Avatar */}
          <div className="flex-shrink-0">
            {comment.author.avatar_url ? (
              <img
                src={comment.author.avatar_url}
                alt={comment.author.display_name}
                className="w-8 h-8 rounded-full"
              />
            ) : (
              <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-xs font-medium text-blue-600">
                {getInitials(comment.author.display_name)}
              </div>
            )}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-gray-900 text-sm">
                {comment.author.display_name}
              </span>
              <span className="text-xs text-gray-400">{getTimeAgo(comment.created_at)}</span>
              {comment.is_edited && (
                <span className="text-xs text-gray-400 italic">(edited)</span>
              )}
              {comment.position && onNavigateToPosition && (
                <button
                  onClick={() => onNavigateToPosition(comment.position!)}
                  className="text-xs text-blue-500 hover:text-blue-600"
                  title="Go to location"
                >
                  📍
                </button>
              )}
            </div>
            <div className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">
              {renderContent(comment.content)}
            </div>

            {/* Actions */}
            {showActions && (
              <div className="flex items-center gap-2 mt-2">
                <button
                  onClick={() => onReply(comment)}
                  className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                >
                  <Reply className="h-3 w-3" />
                  Reply
                </button>
                {isOwner && (
                  <>
                    <button
                      onClick={() => onEdit(comment)}
                      className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1"
                    >
                      <Edit3 className="h-3 w-3" />
                      Edit
                    </button>
                    <button
                      onClick={() => onDelete(comment.id)}
                      className="text-xs text-red-500 hover:text-red-600 flex items-center gap-1"
                    >
                      <Trash2 className="h-3 w-3" />
                      Delete
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Replies */}
      {!isReply && replies.length > 0 && (
        <div className="mt-1">
          {!showReplies && (
            <button
              onClick={() => setShowReplies(true)}
              className="text-xs text-blue-500 hover:text-blue-600 mb-2"
            >
              Show {replies.length} {replies.length === 1 ? 'reply' : 'replies'}
            </button>
          )}
          {showReplies && (
            <>
              {replies.map((reply) => (
                <CommentItem
                  key={reply.id}
                  comment={reply}
                  currentUserId={currentUserId}
                  onReply={onReply}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onNavigateToPosition={onNavigateToPosition}
                  isReply
                />
              ))}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Render comment content with @mentions highlighted.
 */
function renderContent(content: string): React.ReactNode {
  // Parse @mentions
  const parts = content.split(/(@\w+)/g);
  return parts.map((part, index) => {
    if (part.startsWith('@')) {
      return (
        <span key={index} className="text-blue-500 font-medium">
          {part}
        </span>
      );
    }
    return part;
  });
}

/**
 * Comment input with markdown toolbar.
 */
function CommentInput({
  value,
  onChange,
  onSubmit,
  onCancel,
  placeholder = 'Add a comment...',
  submitLabel = 'Post',
  isLoading = false,
  autoFocus = false,
  replyingTo,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCancel?: () => void;
  placeholder?: string;
  submitLabel?: string;
  isLoading?: boolean;
  autoFocus?: boolean;
  replyingTo?: Comment | null;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSubmit();
    }
  };

  const insertAtCursor = (before: string, after: string = '') => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = value.substring(start, end);
    const newValue =
      value.substring(0, start) + before + selectedText + after + value.substring(end);
    onChange(newValue);

    // Restore cursor position
    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(start + before.length, end + before.length);
    }, 0);
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Replying to indicator */}
      {replyingTo && onCancel && (
        <div className="px-3 py-2 bg-gray-50 border-b flex items-center justify-between text-xs text-gray-500">
          <span>
            Replying to <strong>{replyingTo.author.display_name}</strong>
          </span>
          <button onClick={onCancel} className="text-gray-400 hover:text-gray-600">
            <X className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* Toolbar */}
      <div className="px-2 py-1 bg-gray-50 border-b flex items-center gap-1">
        <button
          type="button"
          onClick={() => insertAtCursor('**', '**')}
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
          title="Bold"
        >
          <Bold className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => insertAtCursor('*', '*')}
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
          title="Italic"
        >
          <Italic className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => insertAtCursor('[', '](url)')}
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
          title="Link"
        >
          <Link2 className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => insertAtCursor('@')}
          className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
          title="Mention"
        >
          <AtSign className="h-4 w-4" />
        </button>
      </div>

      {/* Textarea */}
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full px-3 py-2 text-sm resize-none focus:outline-none"
        rows={3}
      />

      {/* Actions */}
      <div className="px-3 py-2 bg-gray-50 border-t flex items-center justify-between">
        <span className="text-xs text-gray-400">
          ⌘+Enter to {submitLabel.toLowerCase()}
        </span>
        <div className="flex items-center gap-2">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded"
            >
              Cancel
            </button>
          )}
          <button
            type="button"
            onClick={onSubmit}
            disabled={!value.trim() || isLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Clock className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Comments panel component.
 */
export function CommentsPanel({ designId, className = '' }: CommentsPanelProps) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newComment, setNewComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [replyingTo, setReplyingTo] = useState<Comment | null>(null);
  const [editingComment, setEditingComment] = useState<Comment | null>(null);

  // TODO: Get from auth context
  const currentUserId = 'current-user-id';

  useEffect(() => {
    loadComments();
  }, [designId]);

  const loadComments = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.get(`/comments/designs/${designId}`);
      setComments(response.data.items || []);
    } catch (err) {
      console.error('Failed to load comments:', err);
      setError('Failed to load comments');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!newComment.trim()) return;

    setIsSubmitting(true);
    try {
      const payload: any = {
        content: newComment.trim(),
      };
      if (replyingTo) {
        payload.parent_id = replyingTo.id;
      }

      const response = await apiClient.post(`/comments/designs/${designId}`, payload);
      
      if (replyingTo) {
        // Add as reply
        setComments((prev) =>
          prev.map((c) =>
            c.id === replyingTo.id
              ? { ...c, reply_count: c.reply_count + 1 }
              : c
          )
        );
      } else {
        setComments((prev) => [response.data, ...prev]);
      }
      
      setNewComment('');
      setReplyingTo(null);
    } catch (err) {
      console.error('Failed to post comment:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = async () => {
    if (!editingComment || !newComment.trim()) return;

    setIsSubmitting(true);
    try {
      const response = await apiClient.patch(
        `/comments/designs/${designId}/${editingComment.id}`,
        { content: newComment.trim() }
      );
      setComments((prev) =>
        prev.map((c) => (c.id === editingComment.id ? response.data : c))
      );
      setNewComment('');
      setEditingComment(null);
    } catch (err) {
      console.error('Failed to edit comment:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (commentId: string) => {
    if (!confirm('Delete this comment?')) return;

    try {
      await apiClient.delete(`/comments/designs/${designId}/${commentId}`);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch (err) {
      console.error('Failed to delete comment:', err);
    }
  };

  const startReply = (comment: Comment) => {
    setReplyingTo(comment);
    setEditingComment(null);
    setNewComment('');
  };

  const startEdit = (comment: Comment) => {
    setEditingComment(comment);
    setReplyingTo(null);
    setNewComment(comment.content);
  };

  const cancelInput = () => {
    setReplyingTo(null);
    setEditingComment(null);
    setNewComment('');
  };

  // Organize comments into threads
  const rootComments = comments.filter((c) => !c.parent_id);
  const repliesByParent = comments.reduce((acc, comment) => {
    if (comment.parent_id) {
      acc[comment.parent_id] = [...(acc[comment.parent_id] || []), comment];
    }
    return acc;
  }, {} as Record<string, Comment[]>);

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Header */}
      <div className="px-4 py-3 border-b flex items-center gap-2">
        <MessageCircle className="h-5 w-5 text-gray-400" />
        <h3 className="font-medium text-gray-900">Comments</h3>
        <span className="text-sm text-gray-400">({comments.length})</span>
      </div>

      {/* Comment input */}
      <div className="p-4 border-b">
        <CommentInput
          value={newComment}
          onChange={setNewComment}
          onSubmit={editingComment ? handleEdit : handleSubmit}
          onCancel={replyingTo || editingComment ? cancelInput : undefined}
          placeholder={
            editingComment
              ? 'Edit your comment...'
              : replyingTo
              ? `Reply to ${replyingTo.author.display_name}...`
              : 'Add a comment...'
          }
          submitLabel={editingComment ? 'Save' : 'Post'}
          isLoading={isSubmitting}
          autoFocus={!!replyingTo || !!editingComment}
          replyingTo={replyingTo}
        />
      </div>

      {/* Comments list */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-8 text-center text-gray-400">Loading comments...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-500">{error}</div>
        ) : rootComments.length === 0 ? (
          <div className="p-8 text-center">
            <MessageCircle className="h-8 w-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm text-gray-500">No comments yet</p>
            <p className="text-xs text-gray-400 mt-1">Be the first to comment!</p>
          </div>
        ) : (
          <div className="divide-y px-4">
            {rootComments.map((comment) => (
              <CommentItem
                key={comment.id}
                comment={comment}
                currentUserId={currentUserId}
                onReply={startReply}
                onEdit={startEdit}
                onDelete={handleDelete}
                replies={repliesByParent[comment.id] || []}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default CommentsPanel;
