/**
 * Template comments section component.
 */

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { MessageSquare, Reply, Edit, Trash2, MoreHorizontal, Flag, EyeOff } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

interface CommentUser {
  id: string;
  display_name: string;
}

interface Comment {
  id: string;
  template_id: string;
  user_id: string;
  parent_id: string | null;
  content: string;
  is_hidden: boolean;
  is_edited: boolean;
  edited_at: string | null;
  created_at: string;
  user: CommentUser | null;
  reply_count: number;
}

interface TemplateCommentsProps {
  /** Template ID */
  templateId: string;
  /** List of comments */
  comments: Comment[];
  /** Current user ID (null if not logged in) */
  currentUserId?: string | null;
  /** Whether current user is admin */
  isAdmin?: boolean;
  /** Callback when adding a comment */
  onAddComment?: (content: string, parentId?: string) => Promise<void>;
  /** Callback when editing a comment */
  onEditComment?: (commentId: string, content: string) => Promise<void>;
  /** Callback when deleting a comment */
  onDeleteComment?: (commentId: string) => Promise<void>;
  /** Callback when reporting a comment */
  onReportComment?: (commentId: string) => void;
  /** Callback when loading replies */
  onLoadReplies?: (commentId: string) => Promise<Comment[]>;
  /** Callback for admin moderation */
  onModerateComment?: (commentId: string, action: 'hide' | 'unhide' | 'delete') => Promise<void>;
  /** Loading state */
  isLoading?: boolean;
  /** Additional class names */
  className?: string;
}

/**
 * Template comments section with threading support.
 */
export function TemplateComments({
  templateId,
  comments,
  currentUserId,
  isAdmin = false,
  onAddComment,
  onEditComment,
  onDeleteComment,
  onReportComment,
  onLoadReplies,
  onModerateComment,
  isLoading = false,
  className,
}: TemplateCommentsProps) {
  const [newComment, setNewComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const handleSubmit = async () => {
    if (!newComment.trim() || !onAddComment) return;
    
    setIsSubmitting(true);
    try {
      await onAddComment(newComment.trim());
      setNewComment('');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <div className={cn('space-y-6', className)}>
      <div className="flex items-center gap-2">
        <MessageSquare className="h-5 w-5" />
        <h3 className="text-lg font-semibold">Comments</h3>
        <span className="text-muted-foreground text-sm">
          ({comments.length})
        </span>
      </div>
      
      {/* New comment form */}
      {currentUserId && onAddComment && (
        <div className="space-y-2">
          <Textarea
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            placeholder="Write a comment..."
            className="min-h-[80px] resize-none"
          />
          <div className="flex justify-end">
            <Button
              onClick={handleSubmit}
              disabled={!newComment.trim() || isSubmitting}
            >
              {isSubmitting ? 'Posting...' : 'Post Comment'}
            </Button>
          </div>
        </div>
      )}
      
      {/* Comments list */}
      <div className="space-y-4">
        {comments.length === 0 ? (
          <p className="text-muted-foreground text-center py-8">
            No comments yet. Be the first to share your thoughts!
          </p>
        ) : (
          comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              currentUserId={currentUserId}
              isAdmin={isAdmin}
              onEdit={onEditComment}
              onDelete={onDeleteComment}
              onReport={onReportComment}
              onReply={onAddComment ? (content) => onAddComment(content, comment.id) : undefined}
              onLoadReplies={onLoadReplies}
              onModerate={onModerateComment}
            />
          ))
        )}
      </div>
      
      {isLoading && (
        <div className="text-center py-4">
          <span className="text-muted-foreground">Loading comments...</span>
        </div>
      )}
    </div>
  );
}

interface CommentItemProps {
  comment: Comment;
  currentUserId?: string | null;
  isAdmin?: boolean;
  depth?: number;
  onEdit?: (commentId: string, content: string) => Promise<void>;
  onDelete?: (commentId: string) => Promise<void>;
  onReport?: (commentId: string) => void;
  onReply?: (content: string) => Promise<void>;
  onLoadReplies?: (commentId: string) => Promise<Comment[]>;
  onModerate?: (commentId: string, action: 'hide' | 'unhide' | 'delete') => Promise<void>;
}

function CommentItem({
  comment,
  currentUserId,
  isAdmin = false,
  depth = 0,
  onEdit,
  onDelete,
  onReport,
  onReply,
  onLoadReplies,
  onModerate,
}: CommentItemProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  const [isReplying, setIsReplying] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [showReplies, setShowReplies] = useState(false);
  const [replies, setReplies] = useState<Comment[]>([]);
  const [isLoadingReplies, setIsLoadingReplies] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const isOwner = currentUserId === comment.user_id;
  const canEdit = isOwner && onEdit;
  const canDelete = (isOwner || isAdmin) && onDelete;
  
  const handleSaveEdit = async () => {
    if (!editContent.trim() || !onEdit) return;
    
    setIsSubmitting(true);
    try {
      await onEdit(comment.id, editContent.trim());
      setIsEditing(false);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleSubmitReply = async () => {
    if (!replyContent.trim() || !onReply) return;
    
    setIsSubmitting(true);
    try {
      await onReply(replyContent.trim());
      setReplyContent('');
      setIsReplying(false);
      // Reload replies to show the new one
      if (onLoadReplies) {
        const newReplies = await onLoadReplies(comment.id);
        setReplies(newReplies);
        setShowReplies(true);
      }
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleLoadReplies = async () => {
    if (!onLoadReplies) return;
    
    setIsLoadingReplies(true);
    try {
      const loadedReplies = await onLoadReplies(comment.id);
      setReplies(loadedReplies);
      setShowReplies(true);
    } finally {
      setIsLoadingReplies(false);
    }
  };
  
  const handleDelete = async () => {
    if (!onDelete) return;
    await onDelete(comment.id);
    setShowDeleteDialog(false);
  };
  
  const initials = comment.user?.display_name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2) || '??';
  
  if (comment.is_hidden && !isAdmin) {
    return (
      <div className={cn(
        'p-4 rounded-lg bg-muted/50 text-muted-foreground text-sm italic',
        depth > 0 && 'ml-8',
      )}>
        This comment has been hidden by a moderator.
      </div>
    );
  }
  
  return (
    <div className={cn(depth > 0 && 'ml-8')}>
      <div className={cn(
        'p-4 rounded-lg border',
        comment.is_hidden && 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-900',
      )}>
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs">{initials}</AvatarFallback>
            </Avatar>
            <div>
              <span className="font-medium text-sm">
                {comment.user?.display_name || 'Unknown User'}
              </span>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>
                  {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
                </span>
                {comment.is_edited && (
                  <span className="italic">(edited)</span>
                )}
                {comment.is_hidden && (
                  <span className="flex items-center gap-1 text-red-500">
                    <EyeOff className="h-3 w-3" />
                    Hidden
                  </span>
                )}
              </div>
            </div>
          </div>
          
          {(canEdit || canDelete || onReport || (isAdmin && onModerate)) && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {canEdit && (
                  <DropdownMenuItem onClick={() => setIsEditing(true)}>
                    <Edit className="h-4 w-4 mr-2" />
                    Edit
                  </DropdownMenuItem>
                )}
                {canDelete && (
                  <DropdownMenuItem
                    onClick={() => setShowDeleteDialog(true)}
                    className="text-red-600"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </DropdownMenuItem>
                )}
                {onReport && !isOwner && (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => onReport(comment.id)}>
                      <Flag className="h-4 w-4 mr-2" />
                      Report
                    </DropdownMenuItem>
                  </>
                )}
                {isAdmin && onModerate && (
                  <>
                    <DropdownMenuSeparator />
                    {comment.is_hidden ? (
                      <DropdownMenuItem onClick={() => onModerate(comment.id, 'unhide')}>
                        <EyeOff className="h-4 w-4 mr-2" />
                        Unhide
                      </DropdownMenuItem>
                    ) : (
                      <DropdownMenuItem onClick={() => onModerate(comment.id, 'hide')}>
                        <EyeOff className="h-4 w-4 mr-2" />
                        Hide
                      </DropdownMenuItem>
                    )}
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
        
        {/* Content */}
        {isEditing ? (
          <div className="mt-3 space-y-2">
            <Textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="min-h-[60px] resize-none"
            />
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsEditing(false);
                  setEditContent(comment.content);
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSaveEdit}
                disabled={!editContent.trim() || isSubmitting}
              >
                Save
              </Button>
            </div>
          </div>
        ) : (
          <p className="mt-2 text-sm whitespace-pre-wrap">{comment.content}</p>
        )}
        
        {/* Actions */}
        {!isEditing && (
          <div className="mt-3 flex items-center gap-4">
            {onReply && currentUserId && depth < 2 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setIsReplying(!isReplying)}
              >
                <Reply className="h-3 w-3 mr-1" />
                Reply
              </Button>
            )}
            
            {comment.reply_count > 0 && !showReplies && onLoadReplies && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={handleLoadReplies}
                disabled={isLoadingReplies}
              >
                {isLoadingReplies ? 'Loading...' : `View ${comment.reply_count} replies`}
              </Button>
            )}
            
            {showReplies && replies.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="h-7 text-xs"
                onClick={() => setShowReplies(false)}
              >
                Hide replies
              </Button>
            )}
          </div>
        )}
        
        {/* Reply form */}
        {isReplying && (
          <div className="mt-3 space-y-2">
            <Textarea
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply..."
              className="min-h-[60px] resize-none"
            />
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setIsReplying(false);
                  setReplyContent('');
                }}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSubmitReply}
                disabled={!replyContent.trim() || isSubmitting}
              >
                Reply
              </Button>
            </div>
          </div>
        )}
      </div>
      
      {/* Replies */}
      {showReplies && replies.length > 0 && (
        <div className="mt-2 space-y-2">
          {replies.map((reply) => (
            <CommentItem
              key={reply.id}
              comment={reply}
              currentUserId={currentUserId}
              isAdmin={isAdmin}
              depth={depth + 1}
              onEdit={onEdit}
              onDelete={onDelete}
              onReport={onReport}
              onReply={onReply}
              onLoadReplies={onLoadReplies}
              onModerate={onModerate}
            />
          ))}
        </div>
      )}
      
      {/* Delete confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Comment</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this comment? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
