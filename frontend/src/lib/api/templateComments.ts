/**
 * API client for template comments.
 */

import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export interface CommentUserInfo {
  id: string;
  display_name: string;
}

export interface CommentCreate {
  content: string;
  parent_id?: string;
}

export interface CommentUpdate {
  content: string;
}

export interface CommentResponse {
  id: string;
  template_id: string;
  user_id: string;
  parent_id: string | null;
  content: string;
  is_hidden: boolean;
  is_edited: boolean;
  edited_at: string | null;
  created_at: string;
  updated_at: string;
  user: CommentUserInfo | null;
  reply_count: number;
}

export interface CommentModerationAction {
  action: 'hide' | 'unhide' | 'delete';
  reason?: string;
}

// =============================================================================
// API
// =============================================================================

export const templateCommentsApi = {
  /**
   * Create a new comment on a template.
   */
  async createComment(
    templateId: string,
    data: CommentCreate
  ): Promise<CommentResponse> {
    const response = await apiClient.post<CommentResponse>(
      `/templates/${templateId}/comments`,
      data
    );
    return response.data;
  },

  /**
   * Get comments for a template.
   */
  async getComments(
    templateId: string,
    limit = 50,
    offset = 0
  ): Promise<CommentResponse[]> {
    const response = await apiClient.get<CommentResponse[]>(
      `/templates/${templateId}/comments`,
      { params: { limit, offset } }
    );
    return response.data;
  },

  /**
   * Get replies to a comment.
   */
  async getReplies(
    templateId: string,
    commentId: string
  ): Promise<CommentResponse[]> {
    const response = await apiClient.get<CommentResponse[]>(
      `/templates/${templateId}/comments/${commentId}/replies`
    );
    return response.data;
  },

  /**
   * Update a comment.
   */
  async updateComment(
    templateId: string,
    commentId: string,
    data: CommentUpdate
  ): Promise<CommentResponse> {
    const response = await apiClient.patch<CommentResponse>(
      `/templates/${templateId}/comments/${commentId}`,
      data
    );
    return response.data;
  },

  /**
   * Delete a comment.
   */
  async deleteComment(templateId: string, commentId: string): Promise<void> {
    await apiClient.delete(`/templates/${templateId}/comments/${commentId}`);
  },

  /**
   * Moderate a comment (admin only).
   */
  async moderateComment(
    templateId: string,
    commentId: string,
    data: CommentModerationAction
  ): Promise<CommentResponse> {
    const response = await apiClient.post<CommentResponse>(
      `/templates/${templateId}/comments/${commentId}/moderate`,
      data
    );
    return response.data;
  },
};
