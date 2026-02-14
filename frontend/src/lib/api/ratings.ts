/**
 * API client for ratings and feedback endpoints.
 */

import { apiClient } from './client';

// =============================================================================
// Types
// =============================================================================

export interface TemplateRatingCreate {
  rating: number;
  review?: string;
}

export interface TemplateRatingResponse {
  id: string;
  template_id: string;
  user_id: string;
  rating: number;
  review: string | null;
  created_at: string;
  updated_at: string;
}

export interface TemplateRatingSummary {
  template_id: string;
  average_rating: number;
  total_ratings: number;
  rating_distribution: Record<number, number>;
}

export interface TemplateFeedbackCreate {
  feedback_type: 'thumbs_up' | 'thumbs_down';
}

export interface TemplateFeedbackResponse {
  id: string;
  template_id: string;
  user_id: string;
  feedback_type: string;
  created_at: string;
}

export interface TemplateFeedbackSummary {
  template_id: string;
  thumbs_up: number;
  thumbs_down: number;
  user_feedback: string | null;
}

// =============================================================================
// Rating API
// =============================================================================

export const ratingsApi = {
  /**
   * Create or update a rating for a template.
   */
  async rateTemplate(
    templateId: string,
    data: TemplateRatingCreate
  ): Promise<TemplateRatingResponse> {
    const response = await apiClient.post<TemplateRatingResponse>(
      `/templates/${templateId}/ratings`,
      data
    );
    return response.data;
  },

  /**
   * Get ratings for a template.
   */
  async getTemplateRatings(
    templateId: string,
    limit = 20,
    offset = 0
  ): Promise<TemplateRatingResponse[]> {
    const response = await apiClient.get<TemplateRatingResponse[]>(
      `/templates/${templateId}/ratings`,
      { params: { limit, offset } }
    );
    return response.data;
  },

  /**
   * Get rating summary for a template.
   */
  async getRatingSummary(templateId: string): Promise<TemplateRatingSummary> {
    const response = await apiClient.get<TemplateRatingSummary>(
      `/templates/${templateId}/ratings/summary`
    );
    return response.data;
  },

  /**
   * Get current user's rating for a template.
   */
  async getMyRating(templateId: string): Promise<TemplateRatingResponse | null> {
    const response = await apiClient.get<TemplateRatingResponse | null>(
      `/templates/${templateId}/ratings/me`
    );
    return response.data;
  },

  /**
   * Delete current user's rating for a template.
   */
  async deleteMyRating(templateId: string): Promise<void> {
    await apiClient.delete(`/templates/${templateId}/ratings`);
  },
};

// =============================================================================
// Feedback API
// =============================================================================

export const feedbackApi = {
  /**
   * Set feedback for a template.
   */
  async setFeedback(
    templateId: string,
    data: TemplateFeedbackCreate
  ): Promise<TemplateFeedbackResponse> {
    const response = await apiClient.post<TemplateFeedbackResponse>(
      `/templates/${templateId}/feedback`,
      data
    );
    return response.data;
  },

  /**
   * Get feedback summary for a template.
   */
  async getFeedbackSummary(templateId: string): Promise<TemplateFeedbackSummary> {
    const response = await apiClient.get<TemplateFeedbackSummary>(
      `/templates/${templateId}/feedback`
    );
    return response.data;
  },

  /**
   * Remove feedback for a template.
   */
  async removeFeedback(templateId: string): Promise<void> {
    await apiClient.delete(`/templates/${templateId}/feedback`);
  },
};
