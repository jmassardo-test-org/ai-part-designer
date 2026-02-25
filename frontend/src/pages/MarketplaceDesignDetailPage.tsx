/**
 * Marketplace Design Detail Page.
 *
 * Shows full details of a marketplace design with ratings,
 * comments, remix, and report functionality.
 */

import {
  ArrowLeft,
  Box,
  Eye,
  Flag,
  GitFork,
  Heart,
  Loader2,
  AlertCircle,
  MessageSquare,
  Star,
  Send,
  Edit2,
  Trash2,
  CornerDownRight,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { SaveButton } from '@/components/marketplace/SaveButton';
import { useAuth } from '@/contexts/AuthContext';
import * as api from '@/lib/marketplace';
import type {
  MarketplaceDesign,
  RatingSummary,
  DesignCommentThread,
  DesignRatingWithUser,
  ReportReason,
} from '@/types/marketplace';

// =============================================================================
// Star Rating Component (inline)
// =============================================================================

interface StarRatingProps {
  rating: number;
  maxStars?: number;
  size?: 'sm' | 'md' | 'lg';
  interactive?: boolean;
  onChange?: (rating: number) => void;
}

function StarRating({ rating, maxStars = 5, size = 'md', interactive = false, onChange }: StarRatingProps) {
  const [hoverRating, setHoverRating] = useState(0);
  const sizeClasses = { sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-6 h-6' };

  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: maxStars }, (_, i) => {
        const starValue = i + 1;
        const filled = starValue <= (hoverRating || rating);
        return (
          <button
            key={i}
            type="button"
            disabled={!interactive}
            className={`${interactive ? 'cursor-pointer hover:scale-110' : 'cursor-default'} transition-transform`}
            onClick={() => interactive && onChange?.(starValue)}
            onMouseEnter={() => interactive && setHoverRating(starValue)}
            onMouseLeave={() => interactive && setHoverRating(0)}
          >
            <Star
              className={`${sizeClasses[size]} ${
                filled
                  ? 'text-yellow-400 fill-yellow-400'
                  : 'text-gray-300 dark:text-gray-600'
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}

// =============================================================================
// Rating Summary Component
// =============================================================================

interface RatingSummaryDisplayProps {
  summary: RatingSummary;
}

function RatingSummaryDisplay({ summary }: RatingSummaryDisplayProps) {
  const maxCount = Math.max(...Object.values(summary.rating_distribution), 1);

  return (
    <div className="flex items-start gap-6">
      <div className="text-center">
        <div className="text-4xl font-bold text-gray-900 dark:text-white">
          {summary.average_rating.toFixed(1)}
        </div>
        <StarRating rating={Math.round(summary.average_rating)} size="sm" />
        <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          {summary.total_ratings} {summary.total_ratings === 1 ? 'rating' : 'ratings'}
        </div>
      </div>
      <div className="flex-1 space-y-1">
        {[5, 4, 3, 2, 1].map((stars) => (
          <div key={stars} className="flex items-center gap-2 text-sm">
            <span className="w-3 text-gray-500 dark:text-gray-400">{stars}</span>
            <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
            <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-yellow-400 rounded-full transition-all"
                style={{
                  width: `${((summary.rating_distribution[stars] || 0) / maxCount) * 100}%`,
                }}
              />
            </div>
            <span className="w-6 text-right text-gray-400 dark:text-gray-500">
              {summary.rating_distribution[stars] || 0}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

// =============================================================================
// Review Card Component
// =============================================================================

interface ReviewCardProps {
  review: DesignRatingWithUser;
}

function ReviewCard({ review }: ReviewCardProps) {
  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white text-sm">
            {review.user_name}
          </span>
          <StarRating rating={review.rating} size="sm" />
        </div>
        <span className="text-xs text-gray-400">
          {new Date(review.created_at).toLocaleDateString()}
        </span>
      </div>
      {review.review && (
        <p className="text-sm text-gray-600 dark:text-gray-300">{review.review}</p>
      )}
    </div>
  );
}

// =============================================================================
// Comment Component
// =============================================================================

interface CommentProps {
  comment: DesignCommentThread;
  designId: string;
  currentUserId?: string;
  token?: string | null;
  onCommentAdded: () => void;
  depth?: number;
}

function Comment({ comment, designId, currentUserId, token, onCommentAdded, depth = 0 }: CommentProps) {
  const [showReplyForm, setShowReplyForm] = useState(false);
  const [replyContent, setReplyContent] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  const [showReplies, setShowReplies] = useState(true);

  const handleReply = async () => {
    if (!replyContent.trim() || !token) return;
    setSubmitting(true);
    try {
      await api.createComment(designId, replyContent.trim(), comment.id, token);
      setReplyContent('');
      setShowReplyForm(false);
      onCommentAdded();
    } catch (err) {
      console.error('Failed to reply:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = async () => {
    if (!editContent.trim() || !token) return;
    setSubmitting(true);
    try {
      await api.updateComment(comment.id, editContent.trim(), token);
      setEditing(false);
      onCommentAdded();
    } catch (err) {
      console.error('Failed to edit:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!token || !confirm('Delete this comment?')) return;
    try {
      await api.deleteComment(comment.id, token);
      onCommentAdded();
    } catch (err) {
      console.error('Failed to delete:', err);
    }
  };

  const isOwner = currentUserId === comment.user_id;
  const maxDepth = 3;

  return (
    <div className={`${depth > 0 ? 'ml-6 pl-4 border-l-2 border-gray-200 dark:border-gray-700' : ''}`}>
      <div className="py-3">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-gray-900 dark:text-white">
              {comment.user_name || 'Anonymous'}
            </span>
            {comment.is_edited && (
              <span className="text-xs text-gray-400">(edited)</span>
            )}
            <span className="text-xs text-gray-400">
              {new Date(comment.created_at).toLocaleDateString()}
            </span>
          </div>
          {isOwner && !comment.is_hidden && (
            <div className="flex items-center gap-1">
              <button
                onClick={() => { setEditing(!editing); setEditContent(comment.content); }}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                title="Edit"
              >
                <Edit2 className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={handleDelete}
                className="p-1 text-gray-400 hover:text-red-500"
                title="Delete"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {comment.is_hidden ? (
          <p className="text-sm text-gray-400 italic">[This comment has been removed]</p>
        ) : editing ? (
          <div className="space-y-2">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full p-2 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              rows={3}
            />
            <div className="flex gap-2">
              <button
                onClick={handleEdit}
                disabled={submitting || !editContent.trim()}
                className="px-3 py-1 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? 'Saving...' : 'Save'}
              </button>
              <button
                onClick={() => setEditing(false)}
                className="px-3 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-600 dark:text-gray-300">{comment.content}</p>
        )}

        {/* Reply button */}
        {!comment.is_hidden && depth < maxDepth && token && (
          <button
            onClick={() => setShowReplyForm(!showReplyForm)}
            className="mt-1 flex items-center gap-1 text-xs text-gray-400 hover:text-indigo-500 transition-colors"
          >
            <CornerDownRight className="w-3 h-3" />
            Reply
          </button>
        )}

        {/* Reply form */}
        {showReplyForm && (
          <div className="mt-2 flex gap-2">
            <input
              type="text"
              value={replyContent}
              onChange={(e) => setReplyContent(e.target.value)}
              placeholder="Write a reply..."
              className="flex-1 px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              onKeyDown={(e) => e.key === 'Enter' && handleReply()}
            />
            <button
              onClick={handleReply}
              disabled={submitting || !replyContent.trim()}
              className="px-3 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      {/* Nested replies */}
      {comment.replies && comment.replies.length > 0 && (
        <div>
          <button
            onClick={() => setShowReplies(!showReplies)}
            className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 mb-1"
          >
            {showReplies ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {comment.replies.length} {comment.replies.length === 1 ? 'reply' : 'replies'}
          </button>
          {showReplies && comment.replies.map((reply) => (
            <Comment
              key={reply.id}
              comment={reply}
              designId={designId}
              currentUserId={currentUserId}
              token={token}
              onCommentAdded={onCommentAdded}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Report Dialog Component
// =============================================================================

interface ReportDialogProps {
  open: boolean;
  onClose: () => void;
  onSubmit: (reason: ReportReason, description?: string) => void;
  submitting: boolean;
}

function ReportDialog({ open, onClose, onSubmit, submitting }: ReportDialogProps) {
  const [reason, setReason] = useState<ReportReason>('inappropriate');
  const [description, setDescription] = useState('');

  if (!open) return null;

  const reasons: { value: ReportReason; label: string }[] = [
    { value: 'spam', label: 'Spam' },
    { value: 'inappropriate', label: 'Inappropriate content' },
    { value: 'copyright', label: 'Copyright violation' },
    { value: 'misleading', label: 'Misleading' },
    { value: 'offensive', label: 'Offensive' },
    { value: 'other', label: 'Other' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Report Design
        </h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Reason
            </label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value as ReportReason)}
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
            >
              {reasons.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Additional details (optional)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Provide more context..."
              rows={3}
              maxLength={1000}
              className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm resize-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="flex gap-3 justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              Cancel
            </button>
            <button
              onClick={() => onSubmit(reason, description || undefined)}
              disabled={submitting}
              className="px-4 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Report'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export function MarketplaceDesignDetailPage() {
  const { designId } = useParams<{ designId: string }>();
  const { token, user } = useAuth();
  const navigate = useNavigate();

  // State
  const [design, setDesign] = useState<MarketplaceDesign | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ratingSummary, setRatingSummary] = useState<RatingSummary | null>(null);
  const [reviews, setReviews] = useState<DesignRatingWithUser[]>([]);
  const [comments, setComments] = useState<DesignCommentThread[]>([]);
  const [commentTotal, setCommentTotal] = useState(0);
  const [myRating, setMyRating] = useState<number>(0);
  const [myReview, setMyReview] = useState('');
  const [hasRated, setHasRated] = useState(false);
  const [ratingSubmitting, setRatingSubmitting] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [commentSubmitting, setCommentSubmitting] = useState(false);
  const [remixing, setRemixing] = useState(false);
  const [showReportDialog, setShowReportDialog] = useState(false);
  const [reportSubmitting, setReportSubmitting] = useState(false);
  const [alreadyReported, setAlreadyReported] = useState(false);
  const [activeTab, setActiveTab] = useState<'reviews' | 'comments'>('reviews');

  // Load design details
  useEffect(() => {
    async function load() {
      if (!designId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await api.getDesignDetail(designId, token || undefined);
        setDesign(data);
        void api.trackDesignView(designId);
      } catch (err) {
        console.error('Failed to load design:', err);
        setError('Failed to load design. It may not exist or is no longer available.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [designId, token]);

  // Load ratings and comments
  const loadCommunityData = useCallback(async () => {
    if (!designId) return;
    try {
      const [summaryData, ratingsData, commentsData] = await Promise.all([
        api.getRatingSummary(designId),
        api.getDesignRatings(designId),
        api.getDesignComments(designId),
      ]);
      setRatingSummary(summaryData);
      setReviews(ratingsData.ratings);
      setComments(commentsData.comments);
      setCommentTotal(commentsData.total);

      // Load user's own rating
      if (token) {
        const myRatingData = await api.getMyRating(designId, token);
        if (myRatingData) {
          setMyRating(myRatingData.rating);
          setMyReview(myRatingData.review || '');
          setHasRated(true);
        }

        const reportStatus = await api.checkReportStatus(designId, token);
        setAlreadyReported(reportStatus.already_reported);
      }
    } catch (err) {
      console.error('Failed to load community data:', err);
    }
  }, [designId, token]);

  useEffect(() => {
    if (design) {
      loadCommunityData();
    }
  }, [design, loadCommunityData]);

  // Handlers
  const handleRate = async () => {
    if (!designId || !token || myRating === 0) return;
    setRatingSubmitting(true);
    try {
      await api.rateDesign(designId, myRating, myReview || undefined, token);
      setHasRated(true);
      await loadCommunityData();
    } catch (err) {
      console.error('Failed to rate:', err);
    } finally {
      setRatingSubmitting(false);
    }
  };

  const handleDeleteRating = async () => {
    if (!designId || !token) return;
    setRatingSubmitting(true);
    try {
      await api.deleteRating(designId, token);
      setMyRating(0);
      setMyReview('');
      setHasRated(false);
      await loadCommunityData();
    } catch (err) {
      console.error('Failed to delete rating:', err);
    } finally {
      setRatingSubmitting(false);
    }
  };

  const handleComment = async () => {
    if (!designId || !token || !newComment.trim()) return;
    setCommentSubmitting(true);
    try {
      await api.createComment(designId, newComment.trim(), undefined, token);
      setNewComment('');
      await loadCommunityData();
    } catch (err) {
      console.error('Failed to comment:', err);
    } finally {
      setCommentSubmitting(false);
    }
  };

  const handleRemix = async () => {
    if (!designId) return;
    if (!user) {
      navigate('/login', { state: { from: `/marketplace/${designId}` } });
      return;
    }
    setRemixing(true);
    try {
      const remix = await api.remixDesign(designId, undefined, token || undefined);
      navigate('/generate', {
        state: {
          remixMode: true,
          enclosureSpec: remix.enclosure_spec,
          remixedFrom: { id: remix.remixed_from_id, name: remix.remixed_from_name },
          designId: remix.id,
          designName: remix.name,
        },
      });
    } catch (err) {
      console.error('Failed to remix:', err);
      setError('Failed to create remix. Please try again.');
    } finally {
      setRemixing(false);
    }
  };

  const handleReport = async (reason: ReportReason, description?: string) => {
    if (!designId || !token) return;
    setReportSubmitting(true);
    try {
      await api.reportDesign(designId, reason, description, token);
      setAlreadyReported(true);
      setShowReportDialog(false);
    } catch (err) {
      console.error('Failed to report:', err);
    } finally {
      setReportSubmitting(false);
    }
  };

  const isOwner = user && design && user.id === design.author_id;

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  // Error state
  if (error || !design) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-700 dark:text-red-400 mb-2">
            Design Not Found
          </h2>
          <p className="text-red-600 dark:text-red-300 mb-4">
            {error || 'This design could not be found.'}
          </p>
          <Link
            to="/marketplace"
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-100 dark:bg-red-800 text-red-700 dark:text-red-200 rounded-lg hover:bg-red-200 dark:hover:bg-red-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Marketplace
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Back navigation */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <Link
            to="/marketplace"
            className="inline-flex items-center gap-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Marketplace
          </Link>
        </div>
      </div>

      {/* Main content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: Preview (2 cols) */}
          <div className="lg:col-span-2 space-y-6">
            {/* Thumbnail */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
              <div className="aspect-video bg-gradient-to-br from-indigo-100 to-purple-100 dark:from-indigo-900/30 dark:to-purple-900/30 flex items-center justify-center">
                {design.thumbnail_url ? (
                  <img
                    src={design.thumbnail_url}
                    alt={design.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <Box className="w-32 h-32 text-indigo-300 dark:text-indigo-600" />
                )}
              </div>
            </div>

            {/* Tabs: Reviews / Comments */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
              <div className="flex border-b border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setActiveTab('reviews')}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'reviews'
                      ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-center gap-2">
                    <Star className="w-4 h-4" />
                    Reviews ({ratingSummary?.total_ratings || 0})
                  </div>
                </button>
                <button
                  onClick={() => setActiveTab('comments')}
                  className={`flex-1 px-4 py-3 text-sm font-medium transition-colors ${
                    activeTab === 'comments'
                      ? 'text-indigo-600 dark:text-indigo-400 border-b-2 border-indigo-600 dark:border-indigo-400'
                      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-center gap-2">
                    <MessageSquare className="w-4 h-4" />
                    Comments ({commentTotal})
                  </div>
                </button>
              </div>

              <div className="p-6">
                {activeTab === 'reviews' ? (
                  <div className="space-y-6">
                    {/* Rating Summary */}
                    {ratingSummary && ratingSummary.total_ratings > 0 && (
                      <RatingSummaryDisplay summary={ratingSummary} />
                    )}

                    {/* Write Review */}
                    {token && !isOwner && (
                      <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                          {hasRated ? 'Update Your Rating' : 'Rate This Design'}
                        </h4>
                        <div className="space-y-3">
                          <StarRating
                            rating={myRating}
                            size="lg"
                            interactive
                            onChange={setMyRating}
                          />
                          <textarea
                            value={myReview}
                            onChange={(e) => setMyReview(e.target.value)}
                            placeholder="Write a review (optional)..."
                            rows={3}
                            maxLength={2000}
                            className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm resize-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={handleRate}
                              disabled={ratingSubmitting || myRating === 0}
                              className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                            >
                              {ratingSubmitting ? 'Saving...' : hasRated ? 'Update Rating' : 'Submit Rating'}
                            </button>
                            {hasRated && (
                              <button
                                onClick={handleDeleteRating}
                                disabled={ratingSubmitting}
                                className="px-4 py-2 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
                              >
                                Remove Rating
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Review List */}
                    {reviews.length > 0 ? (
                      <div className="space-y-3 border-t border-gray-200 dark:border-gray-700 pt-4">
                        {reviews.map((review) => (
                          <ReviewCard key={review.id} review={review} />
                        ))}
                      </div>
                    ) : (
                      !ratingSummary?.total_ratings && (
                        <p className="text-center text-sm text-gray-500 dark:text-gray-400 py-8">
                          No reviews yet. Be the first to rate this design!
                        </p>
                      )
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* New Comment */}
                    {token && (
                      <div className="flex gap-3">
                        <input
                          type="text"
                          value={newComment}
                          onChange={(e) => setNewComment(e.target.value)}
                          placeholder="Write a comment..."
                          className="flex-1 px-4 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                          onKeyDown={(e) => e.key === 'Enter' && handleComment()}
                        />
                        <button
                          onClick={handleComment}
                          disabled={commentSubmitting || !newComment.trim()}
                          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                        >
                          {commentSubmitting ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Send className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    )}

                    {/* Comment List */}
                    {comments.length > 0 ? (
                      <div className="divide-y divide-gray-200 dark:divide-gray-700">
                        {comments.map((comment) => (
                          <Comment
                            key={comment.id}
                            comment={comment}
                            designId={designId!}
                            currentUserId={user?.id}
                            token={token}
                            onCommentAdded={loadCommunityData}
                          />
                        ))}
                      </div>
                    ) : (
                      <p className="text-center text-sm text-gray-500 dark:text-gray-400 py-8">
                        No comments yet. Start the conversation!
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right: Sidebar (1 col) */}
          <div className="space-y-6">
            {/* Design Info */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <div className="space-y-4">
                {/* Category */}
                {design.category && (
                  <span className="inline-block px-3 py-1 bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 text-sm rounded-full">
                    {design.category.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </span>
                )}

                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  {design.name}
                </h1>

                {design.description && (
                  <p className="text-gray-600 dark:text-gray-300 text-sm">
                    {design.description}
                  </p>
                )}

                {/* Author */}
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  by <span className="font-medium text-gray-700 dark:text-gray-300">{design.author_name}</span>
                </p>

                {/* Remixed from */}
                {design.remixed_from_name && (
                  <p className="text-xs text-gray-400 flex items-center gap-1">
                    <GitFork className="w-3 h-3" />
                    Remixed from {design.remixed_from_name}
                  </p>
                )}

                {/* Rating */}
                {design.avg_rating !== null && design.avg_rating !== undefined && (
                  <div className="flex items-center gap-2">
                    <StarRating rating={Math.round(design.avg_rating)} size="sm" />
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {design.avg_rating.toFixed(1)} ({design.total_ratings})
                    </span>
                  </div>
                )}

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3 pt-2">
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400">
                      <Eye className="w-4 h-4" />
                    </div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {design.view_count ?? 0}
                    </div>
                    <div className="text-xs text-gray-400">Views</div>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400">
                      <Heart className="w-4 h-4" />
                    </div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {design.save_count}
                    </div>
                    <div className="text-xs text-gray-400">Saves</div>
                  </div>
                  <div className="text-center">
                    <div className="flex items-center justify-center gap-1 text-gray-500 dark:text-gray-400">
                      <GitFork className="w-4 h-4" />
                    </div>
                    <div className="text-lg font-semibold text-gray-900 dark:text-white">
                      {design.remix_count}
                    </div>
                    <div className="text-xs text-gray-400">Remixes</div>
                  </div>
                </div>

                {/* Tags */}
                {design.tags && design.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-2">
                    {design.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-xs rounded"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Action Buttons */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 space-y-3">
              {/* Remix Button */}
              {!isOwner && (
                <button
                  onClick={handleRemix}
                  disabled={remixing}
                  className="w-full py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {remixing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Creating Remix...
                    </>
                  ) : (
                    <>
                      <GitFork className="w-4 h-4" />
                      Remix This Design
                    </>
                  )}
                </button>
              )}

              {/* Save Button */}
              <div className="w-full">
                <SaveButton designId={designId!} />
              </div>

              {/* Report Button */}
              {token && !isOwner && (
                <button
                  onClick={() => setShowReportDialog(true)}
                  disabled={alreadyReported}
                  className="w-full py-2.5 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center justify-center gap-2 text-sm disabled:opacity-50"
                >
                  <Flag className="w-4 h-4" />
                  {alreadyReported ? 'Already Reported' : 'Report Design'}
                </button>
              )}
            </div>

            {/* File Formats */}
            <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
              <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Available Formats
              </h3>
              <div className="flex gap-2">
                {design.has_stl && (
                  <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-sm rounded-lg">
                    STL
                  </span>
                )}
                {design.has_step && (
                  <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400 text-sm rounded-lg">
                    STEP
                  </span>
                )}
                {!design.has_stl && !design.has_step && (
                  <span className="text-sm text-gray-400">No downloadable files</span>
                )}
              </div>
            </div>

            {/* Published date */}
            <div className="text-center text-xs text-gray-400">
              Published {design.published_at ? new Date(design.published_at).toLocaleDateString() : 'recently'}
            </div>
          </div>
        </div>
      </div>

      {/* Report Dialog */}
      <ReportDialog
        open={showReportDialog}
        onClose={() => setShowReportDialog(false)}
        onSubmit={handleReport}
        submitting={reportSubmitting}
      />
    </div>
  );
}
