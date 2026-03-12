/**
 * Admin API client.
 *
 * Comprehensive namespaced module covering all admin endpoints.
 * Uses the shared apiClient for consistent auth header injection.
 */
import { apiClient } from './client';
import type {
  // Generic
  MessageResponse,
  BulkActionResult,
  // Analytics
  AnalyticsOverview,
  UserAnalytics,
  GenerationAnalytics,
  JobAnalytics,
  StorageAnalytics,
  RevenueAnalytics,
  TimeSeriesAnalytics,
  // Moderation
  ModerationQueueResponse,
  ModerationStats,
  ModerationItem,
  ModerationDecisionRequest,
  RejectContentRequest,
  ModerationDecisionResponse,
  // Users
  UserListResponse,
  AdminUserDetails,
  UserUpdateRequest,
  SuspendUserRequest,
  ImpersonateResponse,
  ForceEmailVerifyResponse,
  LoginHistoryResponse,
  ActivityFeedResponse,
  BulkUserActionRequest,
  UserFilterParams,
  UserWarningRequest,
  UserWarning,
  UserBanRequest,
  UserBanResponse,
  PasswordResetResponse,
  // Projects
  ProjectListResponse,
  AdminProject,
  SuspendProjectRequest,
  TransferOwnershipRequest,
  BulkProjectActionRequest,
  ProjectFilterParams,
  // Designs
  DesignListResponse,
  AdminDesign,
  VisibilityChangeRequest,
  DesignVersionListResponse,
  BulkDesignActionRequest,
  TransferDesignRequest,
  DesignFilterParams,
  // Templates
  TemplateListResponse,
  AdminTemplate,
  TemplateCreateRequest,
  TemplateUpdateRequest,
  ReorderTemplatesRequest,
  TemplateAnalyticsResponse,
  TemplateFilterParams,
  // Jobs
  JobListResponse,
  AdminJob,
  JobPriorityRequest,
  JobStatsResponse,
  QueueStatusResponse,
  PurgeJobsResponse,
  WorkerInfo,
  JobFilterParams,
  // Subscriptions
  SubscriptionListResponse,
  AdminSubscription,
  ChangeTierRequest,
  ExtendSubscriptionRequest,
  SubscriptionFilterParams,
  // Credits
  UserCredits,
  CreditHistoryResponse,
  QuotaResponse,
  QuotaOverrideRequest,
  CreditDistributionResponse,
  LowBalanceUsersResponse,
  // Billing
  FailedPaymentsResponse,
  BillingRevenueResponse,
  TierDefinitionResponse,
  UpdateTierRequest,
  // Coupons
  CouponListResponse,
  AdminCoupon,
  CreateCouponRequest,
  UpdateCouponRequest,
  CouponUsageResponse,
  ApplyCouponRequest,
  GrantTrialRequest,
  ExtendTrialRequest,
  BulkApplyCouponRequest,
  PromotionAnalyticsResponse,
  CouponFilterParams,
  // Organizations
  OrganizationListResponse,
  AdminOrganization,
  AdminOrgMember,
  EditOrganizationRequest,
  AddOrgMemberRequest,
  ChangeOrgMemberRoleRequest,
  TransferOrgOwnershipRequest,
  AddOrgCreditsRequest,
  ChangeOrgTierRequest,
  OrgAuditLogResponse,
  OrgStatsResponse,
  OrganizationFilterParams,
  // Components
  ComponentListResponse,
  AdminComponent,
  CreateComponentRequest,
  EditComponentRequest,
  ComponentAnalyticsResponse,
  ComponentFilterParams,
  // Notifications
  NotificationListResponse,
  CreateAnnouncementRequest,
  AnnouncementResponse,
  NotificationStatsResponse,
  TargetedNotificationRequest,
  ScheduledNotificationRequest,
  NotificationTemplate,
  CreateNotificationTemplateRequest,
  NotificationFilterParams,
  // Files & Storage
  FileListResponse,
  AdminFileDetail,
  FlaggedFileListResponse,
  FailedUploadListResponse,
  StorageStats,
  StorageQuotaRequest,
  TopStorageUsersResponse,
  AdminStorageAnalytics,
  GarbageCollectResponse,
  FileFilterParams,
  // Audit
  AuditLogListResponse,
  AuditLogFilterParams,
  // Security
  SecurityEventListResponse,
  FailedLoginListResponse,
  BlockedIPEntry,
  BlockIPRequest,
  ActiveSessionListResponse,
  SecurityDashboard,
  SecurityEventFilterParams,
  // API Keys
  APIKeyListResponse,
  AdminAPIKey,
  APIKeyUsageResponse,
  APIKeyAggregateStats,
  RateLimitViolationsResponse,
  APIKeyFilterParams,
  // System
  SystemHealth,
  SystemVersion,
  ServiceDetail,
  PerformanceMetrics,
  ResourceUtilization,
  ErrorLogListResponse,
  AIProviderListResponse,
  SystemConfig,
  ManualHealthCheckResponse,
  UptimeResponse,
  // CAD v2 / Starters / Marketplace
  CADv2ComponentListResponse,
  AdminCADv2Component,
  CADv2RegistrySyncResponse,
  StarterListResponse,
  AdminStarter,
  StarterUpdateRequest,
  AdminMarketplaceStats,
  // Content
  ContentItemListResponse,
  ContentItem,
  ContentItemCreateRequest,
  ContentItemUpdateRequest,
  ContentCategory,
  ContentCategoryCreateRequest,
  ContentReorderRequest,
  ContentAnalytics,
  // Assemblies & BOM
  AdminAssemblyListResponse,
  AssemblyStats,
  AssemblyFilterParams,
  AdminVendor,
  VendorCreateRequest,
  VendorUpdateRequest,
  VendorAnalytics,
  BulkPriceUpdateRequest,
  BOMAuditItem,
  // Conversations
  ConversationStats,
  FlaggedConversationListResponse,
  ConversationDetail,
  ConversationQualityMetrics,
  ConversationFilterParams,
  // Trash
  TrashStats,
  TrashResourceType,
  RetentionPolicyUpdateRequest,
  ReclamationPotential,
  TrashCleanupResponse,
} from '../../types/admin';

// -----------------------------------------------------------------------------
// Helper to convert filter params to string record for query params
// -----------------------------------------------------------------------------

/** Convert a typed filter/params object into a Record<string, string> for query params. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toParams(obj?: Record<string, any>): Record<string, string> | undefined {
  if (!obj) return undefined;
  const result: Record<string, string> = {};
  for (const [key, val] of Object.entries(obj)) {
    if (val !== undefined && val !== null) {
      result[key] = String(val);
    }
  }
  return Object.keys(result).length > 0 ? result : undefined;
}

// =============================================================================
// Admin API — Comprehensive Namespaced Module
// =============================================================================

/** Admin API methods organised by domain namespace. */
export const adminApi = {
  // ---------------------------------------------------------------------------
  // Moderation
  // ---------------------------------------------------------------------------
  moderation: {
    /** GET /admin/moderation/queue — Fetch moderation queue. */
    async getQueue(params?: { page?: number; page_size?: number; status?: string }, token?: string): Promise<ModerationQueueResponse> {
      const { data } = await apiClient.get<ModerationQueueResponse>('/admin/moderation/queue', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/moderation/stats — Fetch moderation statistics. */
    async getStats(token?: string): Promise<ModerationStats> {
      const { data } = await apiClient.get<ModerationStats>('/admin/moderation/stats', { token });
      return data;
    },
    /** GET /admin/moderation/:id — Get single moderation item. */
    async getItem(itemId: string, token?: string): Promise<ModerationItem> {
      const { data } = await apiClient.get<ModerationItem>(`/admin/moderation/${itemId}`, { token });
      return data;
    },
    /** POST /admin/moderation/:id/approve — Approve moderation item. */
    async approve(itemId: string, body?: ModerationDecisionRequest, token?: string): Promise<ModerationDecisionResponse> {
      const { data } = await apiClient.post<ModerationDecisionResponse>(`/admin/moderation/${itemId}/approve`, body, { token });
      return data;
    },
    /** POST /admin/moderation/:id/reject — Reject moderation item. */
    async reject(itemId: string, body: RejectContentRequest, token?: string): Promise<ModerationDecisionResponse> {
      const { data } = await apiClient.post<ModerationDecisionResponse>(`/admin/moderation/${itemId}/reject`, body, { token });
      return data;
    },
    /** POST /admin/moderation/:id/escalate — Escalate moderation item. */
    async escalate(itemId: string, body?: ModerationDecisionRequest, token?: string): Promise<ModerationDecisionResponse> {
      const { data } = await apiClient.post<ModerationDecisionResponse>(`/admin/moderation/${itemId}/escalate`, body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Analytics
  // ---------------------------------------------------------------------------
  analytics: {
    /** GET /admin/analytics/overview */
    async getOverview(token?: string): Promise<AnalyticsOverview> {
      const { data } = await apiClient.get<AnalyticsOverview>('/admin/analytics/overview', { token });
      return data;
    },
    /** GET /admin/analytics/users */
    async getUsers(params?: { period?: string }, token?: string): Promise<UserAnalytics> {
      const { data } = await apiClient.get<UserAnalytics>('/admin/analytics/users', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/analytics/generations */
    async getGenerations(params?: { period?: string }, token?: string): Promise<GenerationAnalytics> {
      const { data } = await apiClient.get<GenerationAnalytics>('/admin/analytics/generations', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/analytics/jobs */
    async getJobs(params?: { period?: string }, token?: string): Promise<JobAnalytics> {
      const { data } = await apiClient.get<JobAnalytics>('/admin/analytics/jobs', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/analytics/storage */
    async getStorage(token?: string): Promise<StorageAnalytics> {
      const { data } = await apiClient.get<StorageAnalytics>('/admin/analytics/storage', { token });
      return data;
    },
    /** GET /admin/analytics/revenue */
    async getRevenue(params?: { period?: string }, token?: string): Promise<RevenueAnalytics> {
      const { data } = await apiClient.get<RevenueAnalytics>('/admin/analytics/revenue', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/analytics/export */
    async export(params?: { format?: string }, token?: string): Promise<Blob> {
      const { data } = await apiClient.get<Blob>('/admin/analytics/export', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/analytics/time-series */
    async getTimeSeries(params?: { days?: number }, token?: string): Promise<TimeSeriesAnalytics> {
      const { data } = await apiClient.get<TimeSeriesAnalytics>('/admin/analytics/time-series', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Users
  // ---------------------------------------------------------------------------
  users: {
    /** GET /admin/users */
    async list(params?: UserFilterParams, token?: string): Promise<UserListResponse> {
      const { data } = await apiClient.get<UserListResponse>('/admin/users', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/users/:id */
    async get(userId: string, token?: string): Promise<AdminUserDetails> {
      const { data } = await apiClient.get<AdminUserDetails>(`/admin/users/${userId}`, { token });
      return data;
    },
    /** PATCH /admin/users/:id */
    async update(userId: string, body: UserUpdateRequest, token?: string): Promise<AdminUserDetails> {
      const { data } = await apiClient.patch<AdminUserDetails>(`/admin/users/${userId}`, body, { token });
      return data;
    },
    /** POST /admin/users/:id/suspend */
    async suspend(userId: string, body?: SuspendUserRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/suspend`, body, { token });
      return data;
    },
    /** POST /admin/users/:id/unsuspend */
    async unsuspend(userId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/unsuspend`, undefined, { token });
      return data;
    },
    /** DELETE /admin/users/:id */
    async delete(userId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/users/${userId}`, { token });
      return data;
    },
    /** POST /admin/users/:id/impersonate */
    async impersonate(userId: string, token?: string): Promise<ImpersonateResponse> {
      const { data } = await apiClient.post<ImpersonateResponse>(`/admin/users/${userId}/impersonate`, undefined, { token });
      return data;
    },
    /** POST /admin/users/:id/force-email-verify */
    async forceEmailVerify(userId: string, token?: string): Promise<ForceEmailVerifyResponse> {
      const { data } = await apiClient.post<ForceEmailVerifyResponse>(`/admin/users/${userId}/force-email-verify`, undefined, { token });
      return data;
    },
    /** GET /admin/users/:id/login-history */
    async getLoginHistory(userId: string, params?: { page?: number; page_size?: number }, token?: string): Promise<LoginHistoryResponse> {
      const { data } = await apiClient.get<LoginHistoryResponse>(`/admin/users/${userId}/login-history`, { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/users/:id/activity */
    async getActivity(userId: string, params?: { page?: number; page_size?: number }, token?: string): Promise<ActivityFeedResponse> {
      const { data } = await apiClient.get<ActivityFeedResponse>(`/admin/users/${userId}/activity`, { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/users/bulk-action */
    async bulkAction(body: BulkUserActionRequest, token?: string): Promise<BulkActionResult> {
      const { data } = await apiClient.post<BulkActionResult>('/admin/users/bulk-action', body, { token });
      return data;
    },
    /** GET /admin/users/export */
    async export(params?: { format?: string }, token?: string): Promise<Blob> {
      const { data } = await apiClient.get<Blob>('/admin/users/export', { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/users/:id/warn */
    async warn(userId: string, body: UserWarningRequest, token?: string): Promise<UserWarning> {
      const { data } = await apiClient.post<UserWarning>(`/admin/users/${userId}/warn`, body, { token });
      return data;
    },
    /** POST /admin/users/:id/ban */
    async ban(userId: string, body: UserBanRequest, token?: string): Promise<UserBanResponse> {
      const { data } = await apiClient.post<UserBanResponse>(`/admin/users/${userId}/ban`, body, { token });
      return data;
    },
    /** DELETE /admin/users/:id/ban */
    async unban(userId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/users/${userId}/ban`, { token });
      return data;
    },
    /** POST /admin/users/:id/reset-password */
    async resetPassword(userId: string, token?: string): Promise<PasswordResetResponse> {
      const { data } = await apiClient.post<PasswordResetResponse>(`/admin/users/${userId}/reset-password`, undefined, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Projects
  // ---------------------------------------------------------------------------
  projects: {
    /** GET /admin/projects */
    async list(params?: ProjectFilterParams, token?: string): Promise<ProjectListResponse> {
      const { data } = await apiClient.get<ProjectListResponse>('/admin/projects', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/projects/:id */
    async get(projectId: string, token?: string): Promise<AdminProject> {
      const { data } = await apiClient.get<AdminProject>(`/admin/projects/${projectId}`, { token });
      return data;
    },
    /** DELETE /admin/projects/:id */
    async delete(projectId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/projects/${projectId}`, { token });
      return data;
    },
    /** POST /admin/projects/:id/transfer */
    async transfer(projectId: string, body: TransferOwnershipRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/projects/${projectId}/transfer`, body, { token });
      return data;
    },
    /** POST /admin/projects/:id/suspend */
    async suspend(projectId: string, body?: SuspendProjectRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/projects/${projectId}/suspend`, body, { token });
      return data;
    },
    /** POST /admin/projects/:id/unsuspend */
    async unsuspend(projectId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/projects/${projectId}/unsuspend`, undefined, { token });
      return data;
    },
    /** POST /admin/projects/bulk-action */
    async bulkAction(body: BulkProjectActionRequest, token?: string): Promise<BulkActionResult> {
      const { data } = await apiClient.post<BulkActionResult>('/admin/projects/bulk-action', body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Designs
  // ---------------------------------------------------------------------------
  designs: {
    /** GET /admin/designs */
    async list(params?: DesignFilterParams, token?: string): Promise<DesignListResponse> {
      const { data } = await apiClient.get<DesignListResponse>('/admin/designs', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/designs/:id */
    async get(designId: string, token?: string): Promise<AdminDesign> {
      const { data } = await apiClient.get<AdminDesign>(`/admin/designs/${designId}`, { token });
      return data;
    },
    /** DELETE /admin/designs/:id */
    async delete(designId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/designs/${designId}`, { token });
      return data;
    },
    /** POST /admin/designs/:id/restore */
    async restore(designId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/designs/${designId}/restore`, undefined, { token });
      return data;
    },
    /** PATCH /admin/designs/:id/visibility */
    async changeVisibility(designId: string, body: VisibilityChangeRequest, token?: string): Promise<AdminDesign> {
      const { data } = await apiClient.patch<AdminDesign>(`/admin/designs/${designId}/visibility`, body, { token });
      return data;
    },
    /** POST /admin/designs/:id/transfer */
    async transfer(designId: string, body: TransferDesignRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/designs/${designId}/transfer`, body, { token });
      return data;
    },
    /** GET /admin/designs/:id/versions */
    async getVersions(designId: string, token?: string): Promise<DesignVersionListResponse> {
      const { data } = await apiClient.get<DesignVersionListResponse>(`/admin/designs/${designId}/versions`, { token });
      return data;
    },
    /** POST /admin/designs/bulk-action */
    async bulkAction(body: BulkDesignActionRequest, token?: string): Promise<BulkActionResult> {
      const { data } = await apiClient.post<BulkActionResult>('/admin/designs/bulk-action', body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Templates
  // ---------------------------------------------------------------------------
  templates: {
    /** GET /admin/templates */
    async list(params?: TemplateFilterParams, token?: string): Promise<TemplateListResponse> {
      const { data } = await apiClient.get<TemplateListResponse>('/admin/templates', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/templates/:id */
    async get(templateId: string, token?: string): Promise<AdminTemplate> {
      const { data } = await apiClient.get<AdminTemplate>(`/admin/templates/${templateId}`, { token });
      return data;
    },
    /** POST /admin/templates */
    async create(body: TemplateCreateRequest, token?: string): Promise<AdminTemplate> {
      const { data } = await apiClient.post<AdminTemplate>('/admin/templates', body, { token });
      return data;
    },
    /** PATCH /admin/templates/:id */
    async update(templateId: string, body: TemplateUpdateRequest, token?: string): Promise<AdminTemplate> {
      const { data } = await apiClient.patch<AdminTemplate>(`/admin/templates/${templateId}`, body, { token });
      return data;
    },
    /** DELETE /admin/templates/:id */
    async delete(templateId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/templates/${templateId}`, { token });
      return data;
    },
    /** POST /admin/templates/:id/enable */
    async enable(templateId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/templates/${templateId}/enable`, undefined, { token });
      return data;
    },
    /** POST /admin/templates/:id/disable */
    async disable(templateId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/templates/${templateId}/disable`, undefined, { token });
      return data;
    },
    /** POST /admin/templates/:id/feature */
    async feature(templateId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/templates/${templateId}/feature`, undefined, { token });
      return data;
    },
    /** POST /admin/templates/:id/unfeature */
    async unfeature(templateId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/templates/${templateId}/unfeature`, undefined, { token });
      return data;
    },
    /** POST /admin/templates/:id/clone */
    async clone(templateId: string, token?: string): Promise<AdminTemplate> {
      const { data } = await apiClient.post<AdminTemplate>(`/admin/templates/${templateId}/clone`, undefined, { token });
      return data;
    },
    /** POST /admin/templates/:id/preview-image — Upload preview image. */
    async uploadPreviewImage(templateId: string, body: unknown, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/templates/${templateId}/preview-image`, body, { token });
      return data;
    },
    /** PATCH /admin/templates/reorder */
    async reorder(body: ReorderTemplatesRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.patch<MessageResponse>('/admin/templates/reorder', body, { token });
      return data;
    },
    /** GET /admin/templates/analytics */
    async getAnalytics(token?: string): Promise<TemplateAnalyticsResponse> {
      const { data } = await apiClient.get<TemplateAnalyticsResponse>('/admin/templates/analytics', { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Jobs
  // ---------------------------------------------------------------------------
  jobs: {
    /** GET /admin/jobs */
    async list(params?: JobFilterParams, token?: string): Promise<JobListResponse> {
      const { data } = await apiClient.get<JobListResponse>('/admin/jobs', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/jobs/:id */
    async get(jobId: string, token?: string): Promise<AdminJob> {
      const { data } = await apiClient.get<AdminJob>(`/admin/jobs/${jobId}`, { token });
      return data;
    },
    /** POST /admin/jobs/:id/cancel */
    async cancel(jobId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/jobs/${jobId}/cancel`, undefined, { token });
      return data;
    },
    /** POST /admin/jobs/:id/retry */
    async retry(jobId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/jobs/${jobId}/retry`, undefined, { token });
      return data;
    },
    /** PATCH /admin/jobs/:id/priority */
    async setPriority(jobId: string, body: JobPriorityRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.patch<MessageResponse>(`/admin/jobs/${jobId}/priority`, body, { token });
      return data;
    },
    /** GET /admin/jobs/stats */
    async getStats(token?: string): Promise<JobStatsResponse> {
      const { data } = await apiClient.get<JobStatsResponse>('/admin/jobs/stats', { token });
      return data;
    },
    /** GET /admin/jobs/queue-status */
    async getQueueStatus(token?: string): Promise<QueueStatusResponse> {
      const { data } = await apiClient.get<QueueStatusResponse>('/admin/jobs/queue-status', { token });
      return data;
    },
    /** DELETE /admin/jobs/purge */
    async purge(params?: { status?: string; older_than_days?: number }, token?: string): Promise<PurgeJobsResponse> {
      const { data } = await apiClient.delete<PurgeJobsResponse>('/admin/jobs/purge', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/jobs/workers */
    async getWorkers(token?: string): Promise<WorkerInfo[]> {
      const { data } = await apiClient.get<WorkerInfo[]>('/admin/jobs/workers', { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Subscriptions
  // ---------------------------------------------------------------------------
  subscriptions: {
    /** GET /admin/subscriptions */
    async list(params?: SubscriptionFilterParams, token?: string): Promise<SubscriptionListResponse> {
      const { data } = await apiClient.get<SubscriptionListResponse>('/admin/subscriptions', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/subscriptions/:id */
    async get(subscriptionId: string, token?: string): Promise<AdminSubscription> {
      const { data } = await apiClient.get<AdminSubscription>(`/admin/subscriptions/${subscriptionId}`, { token });
      return data;
    },
    /** PATCH /admin/subscriptions/:id/tier */
    async changeTier(subscriptionId: string, body: ChangeTierRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.patch<MessageResponse>(`/admin/subscriptions/${subscriptionId}/tier`, body, { token });
      return data;
    },
    /** POST /admin/subscriptions/:id/cancel */
    async cancel(subscriptionId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/subscriptions/${subscriptionId}/cancel`, undefined, { token });
      return data;
    },
    /** POST /admin/subscriptions/:id/extend */
    async extend(subscriptionId: string, body: ExtendSubscriptionRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/subscriptions/${subscriptionId}/extend`, body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Credits
  // ---------------------------------------------------------------------------
  credits: {
    /** GET /admin/users/:id/credits */
    async getBalance(userId: string, token?: string): Promise<UserCredits> {
      const { data } = await apiClient.get<UserCredits>(`/admin/users/${userId}/credits`, { token });
      return data;
    },
    /** POST /admin/users/:id/credits/add */
    async add(userId: string, body: { amount: number; reason: string }, token?: string): Promise<UserCredits> {
      const { data } = await apiClient.post<UserCredits>(`/admin/users/${userId}/credits/add`, body, { token });
      return data;
    },
    /** POST /admin/users/:id/credits/deduct */
    async deduct(userId: string, body: { amount: number; reason: string }, token?: string): Promise<UserCredits> {
      const { data } = await apiClient.post<UserCredits>(`/admin/users/${userId}/credits/deduct`, body, { token });
      return data;
    },
    /** GET /admin/users/:id/credits/history */
    async getHistory(userId: string, params?: { page?: number; page_size?: number }, token?: string): Promise<CreditHistoryResponse> {
      const { data } = await apiClient.get<CreditHistoryResponse>(`/admin/users/${userId}/credits/history`, { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/users/:id/quota */
    async getQuota(userId: string, token?: string): Promise<QuotaResponse> {
      const { data } = await apiClient.get<QuotaResponse>(`/admin/users/${userId}/quota`, { token });
      return data;
    },
    /** POST /admin/users/:id/quota/override */
    async overrideQuota(userId: string, body: QuotaOverrideRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/quota/override`, body, { token });
      return data;
    },
    /** GET /admin/credits/distribution */
    async getDistribution(token?: string): Promise<CreditDistributionResponse> {
      const { data } = await apiClient.get<CreditDistributionResponse>('/admin/credits/distribution', { token });
      return data;
    },
    /** GET /admin/credits/low-balance-users */
    async getLowBalanceUsers(params?: { threshold?: number; page?: number; page_size?: number }, token?: string): Promise<LowBalanceUsersResponse> {
      const { data } = await apiClient.get<LowBalanceUsersResponse>('/admin/credits/low-balance-users', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Billing
  // ---------------------------------------------------------------------------
  billing: {
    /** GET /admin/billing/failed-payments */
    async getFailedPayments(params?: { page?: number; page_size?: number }, token?: string): Promise<FailedPaymentsResponse> {
      const { data } = await apiClient.get<FailedPaymentsResponse>('/admin/billing/failed-payments', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/billing/revenue */
    async getRevenue(params?: { period?: string }, token?: string): Promise<BillingRevenueResponse> {
      const { data } = await apiClient.get<BillingRevenueResponse>('/admin/billing/revenue', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Subscription Tiers
  // ---------------------------------------------------------------------------
  subscriptionTiers: {
    /** GET /admin/subscription-tiers */
    async list(token?: string): Promise<TierDefinitionResponse[]> {
      const { data } = await apiClient.get<TierDefinitionResponse[]>('/admin/subscription-tiers', { token });
      return data;
    },
    /** PATCH /admin/subscription-tiers/:id */
    async update(tierId: string, body: UpdateTierRequest, token?: string): Promise<TierDefinitionResponse> {
      const { data } = await apiClient.patch<TierDefinitionResponse>(`/admin/subscription-tiers/${tierId}`, body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Coupons & Promotions
  // ---------------------------------------------------------------------------
  coupons: {
    /** GET /admin/coupons */
    async list(params?: CouponFilterParams, token?: string): Promise<CouponListResponse> {
      const { data } = await apiClient.get<CouponListResponse>('/admin/coupons', { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/coupons */
    async create(body: CreateCouponRequest, token?: string): Promise<AdminCoupon> {
      const { data } = await apiClient.post<AdminCoupon>('/admin/coupons', body, { token });
      return data;
    },
    /** GET /admin/coupons/:code */
    async get(code: string, token?: string): Promise<AdminCoupon> {
      const { data } = await apiClient.get<AdminCoupon>(`/admin/coupons/${code}`, { token });
      return data;
    },
    /** PATCH /admin/coupons/:code */
    async update(code: string, body: UpdateCouponRequest, token?: string): Promise<AdminCoupon> {
      const { data } = await apiClient.patch<AdminCoupon>(`/admin/coupons/${code}`, body, { token });
      return data;
    },
    /** DELETE /admin/coupons/:code */
    async delete(code: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/coupons/${code}`, { token });
      return data;
    },
    /** GET /admin/coupons/:code/usage */
    async getUsage(code: string, params?: { page?: number; page_size?: number }, token?: string): Promise<CouponUsageResponse> {
      const { data } = await apiClient.get<CouponUsageResponse>(`/admin/coupons/${code}/usage`, { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/users/:id/apply-coupon */
    async applyToUser(userId: string, body: ApplyCouponRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/apply-coupon`, body, { token });
      return data;
    },
    /** POST /admin/users/:id/grant-trial */
    async grantTrial(userId: string, body: GrantTrialRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/grant-trial`, body, { token });
      return data;
    },
    /** POST /admin/users/:id/extend-trial */
    async extendTrial(userId: string, body: ExtendTrialRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/extend-trial`, body, { token });
      return data;
    },
    /** GET /admin/promotions/analytics */
    async getPromotionAnalytics(token?: string): Promise<PromotionAnalyticsResponse> {
      const { data } = await apiClient.get<PromotionAnalyticsResponse>('/admin/promotions/analytics', { token });
      return data;
    },
    /** POST /admin/coupons/bulk-apply */
    async bulkApply(body: BulkApplyCouponRequest, token?: string): Promise<BulkActionResult> {
      const { data } = await apiClient.post<BulkActionResult>('/admin/coupons/bulk-apply', body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Organizations
  // ---------------------------------------------------------------------------
  organizations: {
    /** GET /admin/organizations */
    async list(params?: OrganizationFilterParams, token?: string): Promise<OrganizationListResponse> {
      const { data } = await apiClient.get<OrganizationListResponse>('/admin/organizations', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/organizations/:id */
    async get(orgId: string, token?: string): Promise<AdminOrganization> {
      const { data } = await apiClient.get<AdminOrganization>(`/admin/organizations/${orgId}`, { token });
      return data;
    },
    /** GET /admin/organizations/:id/members */
    async getMembers(orgId: string, params?: { page?: number; page_size?: number }, token?: string): Promise<{ items: AdminOrgMember[]; total: number }> {
      const { data } = await apiClient.get<{ items: AdminOrgMember[]; total: number }>(`/admin/organizations/${orgId}/members`, { token, params: toParams(params) });
      return data;
    },
    /** DELETE /admin/organizations/:id */
    async delete(orgId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/organizations/${orgId}`, { token });
      return data;
    },
    /** PATCH /admin/organizations/:id */
    async update(orgId: string, body: EditOrganizationRequest, token?: string): Promise<AdminOrganization> {
      const { data } = await apiClient.patch<AdminOrganization>(`/admin/organizations/${orgId}`, body, { token });
      return data;
    },
    /** POST /admin/organizations/:id/members */
    async addMember(orgId: string, body: AddOrgMemberRequest, token?: string): Promise<AdminOrgMember> {
      const { data } = await apiClient.post<AdminOrgMember>(`/admin/organizations/${orgId}/members`, body, { token });
      return data;
    },
    /** DELETE /admin/organizations/:id/members/:userId */
    async removeMember(orgId: string, userId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/organizations/${orgId}/members/${userId}`, { token });
      return data;
    },
    /** PATCH /admin/organizations/:id/members/:userId/role */
    async changeMemberRole(orgId: string, userId: string, body: ChangeOrgMemberRoleRequest, token?: string): Promise<AdminOrgMember> {
      const { data } = await apiClient.patch<AdminOrgMember>(`/admin/organizations/${orgId}/members/${userId}/role`, body, { token });
      return data;
    },
    /** POST /admin/organizations/:id/transfer-ownership */
    async transferOwnership(orgId: string, body: TransferOrgOwnershipRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/organizations/${orgId}/transfer-ownership`, body, { token });
      return data;
    },
    /** POST /admin/organizations/:id/credits/add */
    async addCredits(orgId: string, body: AddOrgCreditsRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/organizations/${orgId}/credits/add`, body, { token });
      return data;
    },
    /** PATCH /admin/organizations/:id/tier */
    async changeTier(orgId: string, body: ChangeOrgTierRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.patch<MessageResponse>(`/admin/organizations/${orgId}/tier`, body, { token });
      return data;
    },
    /** GET /admin/organizations/:id/audit-log */
    async getAuditLog(orgId: string, params?: { page?: number; page_size?: number }, token?: string): Promise<OrgAuditLogResponse> {
      const { data } = await apiClient.get<OrgAuditLogResponse>(`/admin/organizations/${orgId}/audit-log`, { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/organizations/:id/stats */
    async getStats(orgId: string, token?: string): Promise<OrgStatsResponse> {
      const { data } = await apiClient.get<OrgStatsResponse>(`/admin/organizations/${orgId}/stats`, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Components
  // ---------------------------------------------------------------------------
  components: {
    /** GET /admin/components */
    async list(params?: ComponentFilterParams, token?: string): Promise<ComponentListResponse> {
      const { data } = await apiClient.get<ComponentListResponse>('/admin/components', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/components/:id */
    async get(componentId: string, token?: string): Promise<AdminComponent> {
      const { data } = await apiClient.get<AdminComponent>(`/admin/components/${componentId}`, { token });
      return data;
    },
    /** POST /admin/components */
    async create(body: CreateComponentRequest, token?: string): Promise<AdminComponent> {
      const { data } = await apiClient.post<AdminComponent>('/admin/components', body, { token });
      return data;
    },
    /** PATCH /admin/components/:id */
    async update(componentId: string, body: EditComponentRequest, token?: string): Promise<AdminComponent> {
      const { data } = await apiClient.patch<AdminComponent>(`/admin/components/${componentId}`, body, { token });
      return data;
    },
    /** DELETE /admin/components/:id */
    async delete(componentId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/components/${componentId}`, { token });
      return data;
    },
    /** POST /admin/components/:id/verify */
    async verify(componentId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/components/${componentId}/verify`, undefined, { token });
      return data;
    },
    /** POST /admin/components/:id/feature */
    async feature(componentId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/components/${componentId}/feature`, undefined, { token });
      return data;
    },
    /** POST /admin/components/:id/approve-for-library */
    async approveForLibrary(componentId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/components/${componentId}/approve-for-library`, undefined, { token });
      return data;
    },
    /** GET /admin/components/analytics */
    async getAnalytics(token?: string): Promise<ComponentAnalyticsResponse> {
      const { data } = await apiClient.get<ComponentAnalyticsResponse>('/admin/components/analytics', { token });
      return data;
    },
    /** POST /admin/components/bulk-price-update */
    async bulkPriceUpdate(body: BulkPriceUpdateRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>('/admin/components/bulk-price-update', body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Notifications
  // ---------------------------------------------------------------------------
  notifications: {
    /** GET /admin/notifications */
    async list(params?: NotificationFilterParams, token?: string): Promise<NotificationListResponse> {
      const { data } = await apiClient.get<NotificationListResponse>('/admin/notifications', { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/notifications/announcement */
    async sendAnnouncement(body: CreateAnnouncementRequest, token?: string): Promise<AnnouncementResponse> {
      const { data } = await apiClient.post<AnnouncementResponse>('/admin/notifications/announcement', body, { token });
      return data;
    },
    /** POST /admin/users/:id/send-notification */
    async sendToUser(userId: string, body: { title: string; message: string; url?: string }, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/send-notification`, body, { token });
      return data;
    },
    /** DELETE /admin/notifications/:id */
    async delete(notificationId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/notifications/${notificationId}`, { token });
      return data;
    },
    /** GET /admin/notifications/stats */
    async getStats(token?: string): Promise<NotificationStatsResponse> {
      const { data } = await apiClient.get<NotificationStatsResponse>('/admin/notifications/stats', { token });
      return data;
    },
    /** POST /admin/notifications/targeted */
    async sendTargeted(body: TargetedNotificationRequest, token?: string): Promise<AnnouncementResponse> {
      const { data } = await apiClient.post<AnnouncementResponse>('/admin/notifications/targeted', body, { token });
      return data;
    },
    /** POST /admin/notifications/scheduled */
    async schedule(body: ScheduledNotificationRequest, token?: string): Promise<AnnouncementResponse> {
      const { data } = await apiClient.post<AnnouncementResponse>('/admin/notifications/scheduled', body, { token });
      return data;
    },
    /** GET /admin/notifications/templates */
    async getTemplates(token?: string): Promise<NotificationTemplate[]> {
      const { data } = await apiClient.get<NotificationTemplate[]>('/admin/notifications/templates', { token });
      return data;
    },
    /** POST /admin/notifications/templates */
    async createTemplate(body: CreateNotificationTemplateRequest, token?: string): Promise<NotificationTemplate> {
      const { data } = await apiClient.post<NotificationTemplate>('/admin/notifications/templates', body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Files
  // ---------------------------------------------------------------------------
  files: {
    /** GET /admin/files */
    async list(params?: FileFilterParams, token?: string): Promise<FileListResponse> {
      const { data } = await apiClient.get<FileListResponse>('/admin/files', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/files/:id */
    async get(fileId: string, token?: string): Promise<AdminFileDetail> {
      const { data } = await apiClient.get<AdminFileDetail>(`/admin/files/${fileId}`, { token });
      return data;
    },
    /** DELETE /admin/files/:id */
    async delete(fileId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/files/${fileId}`, { token });
      return data;
    },
    /** GET /admin/files/flagged */
    async getFlagged(params?: { page?: number; page_size?: number }, token?: string): Promise<FlaggedFileListResponse> {
      const { data } = await apiClient.get<FlaggedFileListResponse>('/admin/files/flagged', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/files/failed-uploads */
    async getFailedUploads(params?: { page?: number; page_size?: number }, token?: string): Promise<FailedUploadListResponse> {
      const { data } = await apiClient.get<FailedUploadListResponse>('/admin/files/failed-uploads', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Storage
  // ---------------------------------------------------------------------------
  storage: {
    /** GET /admin/storage/stats */
    async getStats(token?: string): Promise<StorageStats> {
      const { data } = await apiClient.get<StorageStats>('/admin/storage/stats', { token });
      return data;
    },
    /** POST /admin/users/:id/storage-quota */
    async setUserQuota(userId: string, body: StorageQuotaRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/users/${userId}/storage-quota`, body, { token });
      return data;
    },
    /** GET /admin/storage/top-users */
    async getTopUsers(params?: { limit?: number }, token?: string): Promise<TopStorageUsersResponse> {
      const { data } = await apiClient.get<TopStorageUsersResponse>('/admin/storage/top-users', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/storage/analytics */
    async getAnalytics(token?: string): Promise<AdminStorageAnalytics> {
      const { data } = await apiClient.get<AdminStorageAnalytics>('/admin/storage/analytics', { token });
      return data;
    },
    /** POST /admin/storage/garbage-collect */
    async garbageCollect(token?: string): Promise<GarbageCollectResponse> {
      const { data } = await apiClient.post<GarbageCollectResponse>('/admin/storage/garbage-collect', undefined, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Audit Logs
  // ---------------------------------------------------------------------------
  auditLogs: {
    /** GET /admin/audit-logs */
    async list(params?: AuditLogFilterParams, token?: string): Promise<AuditLogListResponse> {
      const { data } = await apiClient.get<AuditLogListResponse>('/admin/audit-logs', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/audit-logs/export */
    async export(params?: AuditLogFilterParams & { format?: string }, token?: string): Promise<Blob> {
      const { data } = await apiClient.get<Blob>('/admin/audit-logs/export', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Security
  // ---------------------------------------------------------------------------
  security: {
    /** GET /admin/security/events */
    async getEvents(params?: SecurityEventFilterParams, token?: string): Promise<SecurityEventListResponse> {
      const { data } = await apiClient.get<SecurityEventListResponse>('/admin/security/events', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/security/failed-logins */
    async getFailedLogins(params?: { page?: number; page_size?: number; hours?: number }, token?: string): Promise<FailedLoginListResponse> {
      const { data } = await apiClient.get<FailedLoginListResponse>('/admin/security/failed-logins', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/security/blocked-ips */
    async getBlockedIPs(token?: string): Promise<BlockedIPEntry[]> {
      const { data } = await apiClient.get<BlockedIPEntry[]>('/admin/security/blocked-ips', { token });
      return data;
    },
    /** POST /admin/security/blocked-ips */
    async blockIP(body: BlockIPRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>('/admin/security/blocked-ips', body, { token });
      return data;
    },
    /** DELETE /admin/security/blocked-ips/:ip */
    async unblockIP(ip: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/security/blocked-ips/${ip}`, { token });
      return data;
    },
    /** GET /admin/security/sessions */
    async getSessions(params?: { page?: number; page_size?: number }, token?: string): Promise<ActiveSessionListResponse> {
      const { data } = await apiClient.get<ActiveSessionListResponse>('/admin/security/sessions', { token, params: toParams(params) });
      return data;
    },
    /** DELETE /admin/security/sessions/:id */
    async terminateSession(sessionId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/security/sessions/${sessionId}`, { token });
      return data;
    },
    /** GET /admin/security/dashboard */
    async getDashboard(token?: string): Promise<SecurityDashboard> {
      const { data } = await apiClient.get<SecurityDashboard>('/admin/security/dashboard', { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // API Keys
  // ---------------------------------------------------------------------------
  apiKeys: {
    /** GET /admin/api-keys */
    async list(params?: APIKeyFilterParams, token?: string): Promise<APIKeyListResponse> {
      const { data } = await apiClient.get<APIKeyListResponse>('/admin/api-keys', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/api-keys/:id */
    async get(keyId: string, token?: string): Promise<AdminAPIKey> {
      const { data } = await apiClient.get<AdminAPIKey>(`/admin/api-keys/${keyId}`, { token });
      return data;
    },
    /** POST /admin/api-keys/:id/revoke */
    async revoke(keyId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/api-keys/${keyId}/revoke`, undefined, { token });
      return data;
    },
    /** GET /admin/api-keys/:id/usage */
    async getUsage(keyId: string, token?: string): Promise<APIKeyUsageResponse> {
      const { data } = await apiClient.get<APIKeyUsageResponse>(`/admin/api-keys/${keyId}/usage`, { token });
      return data;
    },
    /** GET /admin/api-keys/stats */
    async getStats(token?: string): Promise<APIKeyAggregateStats> {
      const { data } = await apiClient.get<APIKeyAggregateStats>('/admin/api-keys/stats', { token });
      return data;
    },
    /** GET /admin/api-keys/rate-limit-violations */
    async getRateLimitViolations(params?: { page?: number; page_size?: number }, token?: string): Promise<RateLimitViolationsResponse> {
      const { data } = await apiClient.get<RateLimitViolationsResponse>('/admin/api-keys/rate-limit-violations', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // System
  // ---------------------------------------------------------------------------
  system: {
    /** GET /admin/system/health */
    async getHealth(token?: string): Promise<SystemHealth> {
      const { data } = await apiClient.get<SystemHealth>('/admin/system/health', { token });
      return data;
    },
    /** GET /admin/system/version */
    async getVersion(token?: string): Promise<SystemVersion> {
      const { data } = await apiClient.get<SystemVersion>('/admin/system/version', { token });
      return data;
    },
    /** GET /admin/system/services/:name */
    async getServiceDetail(serviceName: string, token?: string): Promise<ServiceDetail> {
      const { data } = await apiClient.get<ServiceDetail>(`/admin/system/services/${serviceName}`, { token });
      return data;
    },
    /** GET /admin/system/performance */
    async getPerformance(token?: string): Promise<PerformanceMetrics> {
      const { data } = await apiClient.get<PerformanceMetrics>('/admin/system/performance', { token });
      return data;
    },
    /** GET /admin/system/resources */
    async getResources(token?: string): Promise<ResourceUtilization> {
      const { data } = await apiClient.get<ResourceUtilization>('/admin/system/resources', { token });
      return data;
    },
    /** GET /admin/system/errors */
    async getErrors(params?: { page?: number; page_size?: number; hours?: number }, token?: string): Promise<ErrorLogListResponse> {
      const { data } = await apiClient.get<ErrorLogListResponse>('/admin/system/errors', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/system/ai-providers */
    async getAIProviders(token?: string): Promise<AIProviderListResponse> {
      const { data } = await apiClient.get<AIProviderListResponse>('/admin/system/ai-providers', { token });
      return data;
    },
    /** GET /admin/system/config */
    async getConfig(token?: string): Promise<SystemConfig> {
      const { data } = await apiClient.get<SystemConfig>('/admin/system/config', { token });
      return data;
    },
    /** POST /admin/system/health-check — Trigger a manual health check. */
    async runHealthCheck(token?: string): Promise<ManualHealthCheckResponse> {
      const { data } = await apiClient.post<ManualHealthCheckResponse>('/admin/system/health-check', undefined, { token });
      return data;
    },
    /** GET /admin/system/uptime */
    async getUptime(token?: string): Promise<UptimeResponse> {
      const { data } = await apiClient.get<UptimeResponse>('/admin/system/uptime', { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // CAD v2
  // ---------------------------------------------------------------------------
  cadV2: {
    /** GET /admin/cad-v2/components */
    async listComponents(params?: { category?: string; search?: string }, token?: string): Promise<CADv2ComponentListResponse> {
      const { data } = await apiClient.get<CADv2ComponentListResponse>('/admin/cad-v2/components', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/cad-v2/components/:id */
    async getComponent(componentId: string, token?: string): Promise<AdminCADv2Component> {
      const { data } = await apiClient.get<AdminCADv2Component>(`/admin/cad-v2/components/${componentId}`, { token });
      return data;
    },
    /** POST /admin/cad-v2/sync */
    async syncRegistry(token?: string): Promise<CADv2RegistrySyncResponse> {
      const { data } = await apiClient.post<CADv2RegistrySyncResponse>('/admin/cad-v2/sync', undefined, { token });
      return data;
    },
    /** POST /admin/cad-v2/components/:id/verify */
    async verifyComponent(componentId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/cad-v2/components/${componentId}/verify`, undefined, { token });
      return data;
    },
    /** POST /admin/cad-v2/components/:id/feature */
    async featureComponent(componentId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/cad-v2/components/${componentId}/feature`, undefined, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Starters
  // ---------------------------------------------------------------------------
  starters: {
    /** GET /admin/starters */
    async list(params?: { page?: number; page_size?: number; category?: string }, token?: string): Promise<StarterListResponse> {
      const { data } = await apiClient.get<StarterListResponse>('/admin/starters', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/starters/:id */
    async get(starterId: string, token?: string): Promise<AdminStarter> {
      const { data } = await apiClient.get<AdminStarter>(`/admin/starters/${starterId}`, { token });
      return data;
    },
    /** PATCH /admin/starters/:id */
    async update(starterId: string, body: StarterUpdateRequest, token?: string): Promise<AdminStarter> {
      const { data } = await apiClient.patch<AdminStarter>(`/admin/starters/${starterId}`, body, { token });
      return data;
    },
    /** POST /admin/starters/:id/feature */
    async feature(starterId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/starters/${starterId}/feature`, undefined, { token });
      return data;
    },
    /** POST /admin/starters/:id/unfeature */
    async unfeature(starterId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/starters/${starterId}/unfeature`, undefined, { token });
      return data;
    },
    /** DELETE /admin/starters/:id */
    async delete(starterId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/starters/${starterId}`, { token });
      return data;
    },
    /** POST /admin/starters/reseed */
    async reseed(token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>('/admin/starters/reseed', undefined, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Marketplace
  // ---------------------------------------------------------------------------
  marketplace: {
    /** GET /admin/marketplace/stats */
    async getStats(token?: string): Promise<AdminMarketplaceStats> {
      const { data } = await apiClient.get<AdminMarketplaceStats>('/admin/marketplace/stats', { token });
      return data;
    },
    /** GET /admin/marketplace/featured */
    async getFeatured(token?: string): Promise<AdminStarter[]> {
      const { data } = await apiClient.get<AdminStarter[]>('/admin/marketplace/featured', { token });
      return data;
    },
    /** POST /admin/marketplace/reorder-featured */
    async reorderFeatured(body: { starter_ids: string[] }, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>('/admin/marketplace/reorder-featured', body, { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Content Management (FAQs / Articles)
  // ---------------------------------------------------------------------------
  content: {
    /** GET /admin/content/faqs */
    async listFaqs(params?: { page?: number; page_size?: number; category?: string; status?: string }, token?: string): Promise<ContentItemListResponse> {
      const { data } = await apiClient.get<ContentItemListResponse>('/admin/content/faqs', { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/content/faqs */
    async createFaq(body: ContentItemCreateRequest, token?: string): Promise<ContentItem> {
      const { data } = await apiClient.post<ContentItem>('/admin/content/faqs', body, { token });
      return data;
    },
    /** PATCH /admin/content/faqs/:id */
    async updateFaq(faqId: string, body: ContentItemUpdateRequest, token?: string): Promise<ContentItem> {
      const { data } = await apiClient.patch<ContentItem>(`/admin/content/faqs/${faqId}`, body, { token });
      return data;
    },
    /** DELETE /admin/content/faqs/:id */
    async deleteFaq(faqId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/content/faqs/${faqId}`, { token });
      return data;
    },
    /** POST /admin/content/faqs/:id/publish */
    async publishFaq(faqId: string, token?: string): Promise<ContentItem> {
      const { data } = await apiClient.post<ContentItem>(`/admin/content/faqs/${faqId}/publish`, undefined, { token });
      return data;
    },
    /** GET /admin/content/articles */
    async listArticles(params?: { page?: number; page_size?: number; category?: string; status?: string }, token?: string): Promise<ContentItemListResponse> {
      const { data } = await apiClient.get<ContentItemListResponse>('/admin/content/articles', { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/content/articles */
    async createArticle(body: ContentItemCreateRequest, token?: string): Promise<ContentItem> {
      const { data } = await apiClient.post<ContentItem>('/admin/content/articles', body, { token });
      return data;
    },
    /** PATCH /admin/content/articles/:id */
    async updateArticle(articleId: string, body: ContentItemUpdateRequest, token?: string): Promise<ContentItem> {
      const { data } = await apiClient.patch<ContentItem>(`/admin/content/articles/${articleId}`, body, { token });
      return data;
    },
    /** DELETE /admin/content/articles/:id */
    async deleteArticle(articleId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/content/articles/${articleId}`, { token });
      return data;
    },
    /** POST /admin/content/articles/:id/publish */
    async publishArticle(articleId: string, token?: string): Promise<ContentItem> {
      const { data } = await apiClient.post<ContentItem>(`/admin/content/articles/${articleId}/publish`, undefined, { token });
      return data;
    },
    /** GET /admin/content/categories */
    async listCategories(token?: string): Promise<ContentCategory[]> {
      const { data } = await apiClient.get<ContentCategory[]>('/admin/content/categories', { token });
      return data;
    },
    /** POST /admin/content/categories */
    async createCategory(body: ContentCategoryCreateRequest, token?: string): Promise<ContentCategory> {
      const { data } = await apiClient.post<ContentCategory>('/admin/content/categories', body, { token });
      return data;
    },
    /** PATCH /admin/content/reorder */
    async reorder(body: ContentReorderRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.patch<MessageResponse>('/admin/content/reorder', body, { token });
      return data;
    },
    /** GET /admin/content/analytics */
    async getAnalytics(token?: string): Promise<ContentAnalytics> {
      const { data } = await apiClient.get<ContentAnalytics>('/admin/content/analytics', { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Assemblies
  // ---------------------------------------------------------------------------
  assemblies: {
    /** GET /admin/assemblies */
    async list(params?: AssemblyFilterParams, token?: string): Promise<AdminAssemblyListResponse> {
      const { data } = await apiClient.get<AdminAssemblyListResponse>('/admin/assemblies', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/assemblies/stats */
    async getStats(token?: string): Promise<AssemblyStats> {
      const { data } = await apiClient.get<AssemblyStats>('/admin/assemblies/stats', { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Vendors
  // ---------------------------------------------------------------------------
  vendors: {
    /** GET /admin/vendors */
    async list(params?: { page?: number; page_size?: number }, token?: string): Promise<{ items: AdminVendor[]; total: number }> {
      const { data } = await apiClient.get<{ items: AdminVendor[]; total: number }>('/admin/vendors', { token, params: toParams(params) });
      return data;
    },
    /** POST /admin/vendors */
    async create(body: VendorCreateRequest, token?: string): Promise<AdminVendor> {
      const { data } = await apiClient.post<AdminVendor>('/admin/vendors', body, { token });
      return data;
    },
    /** PATCH /admin/vendors/:id */
    async update(vendorId: string, body: VendorUpdateRequest, token?: string): Promise<AdminVendor> {
      const { data } = await apiClient.patch<AdminVendor>(`/admin/vendors/${vendorId}`, body, { token });
      return data;
    },
    /** DELETE /admin/vendors/:id */
    async delete(vendorId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/vendors/${vendorId}`, { token });
      return data;
    },
    /** GET /admin/vendors/analytics */
    async getAnalytics(token?: string): Promise<VendorAnalytics> {
      const { data } = await apiClient.get<VendorAnalytics>('/admin/vendors/analytics', { token });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // BOM
  // ---------------------------------------------------------------------------
  bom: {
    /** GET /admin/bom/audit-queue */
    async getAuditQueue(params?: { page?: number; page_size?: number }, token?: string): Promise<{ items: BOMAuditItem[]; total: number }> {
      const { data } = await apiClient.get<{ items: BOMAuditItem[]; total: number }>('/admin/bom/audit-queue', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Conversations
  // ---------------------------------------------------------------------------
  conversations: {
    /** GET /admin/conversations/stats */
    async getStats(token?: string): Promise<ConversationStats> {
      const { data } = await apiClient.get<ConversationStats>('/admin/conversations/stats', { token });
      return data;
    },
    /** GET /admin/conversations/flagged */
    async getFlagged(params?: { page?: number; page_size?: number }, token?: string): Promise<FlaggedConversationListResponse> {
      const { data } = await apiClient.get<FlaggedConversationListResponse>('/admin/conversations/flagged', { token, params: toParams(params) });
      return data;
    },
    /** GET /admin/conversations/:id */
    async get(conversationId: string, token?: string): Promise<ConversationDetail> {
      const { data } = await apiClient.get<ConversationDetail>(`/admin/conversations/${conversationId}`, { token });
      return data;
    },
    /** GET /admin/conversations/quality-metrics */
    async getQualityMetrics(token?: string): Promise<ConversationQualityMetrics> {
      const { data } = await apiClient.get<ConversationQualityMetrics>('/admin/conversations/quality-metrics', { token });
      return data;
    },
    /** GET /admin/conversations/export */
    async export(params?: ConversationFilterParams & { format?: string }, token?: string): Promise<Blob> {
      const { data } = await apiClient.get<Blob>('/admin/conversations/export', { token, params: toParams(params) });
      return data;
    },
  },

  // ---------------------------------------------------------------------------
  // Trash
  // ---------------------------------------------------------------------------
  trash: {
    /** GET /admin/trash/stats */
    async getStats(token?: string): Promise<TrashStats> {
      const { data } = await apiClient.get<TrashStats>('/admin/trash/stats', { token });
      return data;
    },
    /** PATCH /admin/trash/retention-policy */
    async updateRetentionPolicy(body: RetentionPolicyUpdateRequest, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.patch<MessageResponse>('/admin/trash/retention-policy', body, { token });
      return data;
    },
    /** DELETE /admin/trash/:type/:id/permanent */
    async permanentDelete(resourceType: TrashResourceType, resourceId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.delete<MessageResponse>(`/admin/trash/${resourceType}/${resourceId}/permanent`, { token });
      return data;
    },
    /** POST /admin/trash/:type/:id/restore */
    async restore(resourceType: TrashResourceType, resourceId: string, token?: string): Promise<MessageResponse> {
      const { data } = await apiClient.post<MessageResponse>(`/admin/trash/${resourceType}/${resourceId}/restore`, undefined, { token });
      return data;
    },
    /** POST /admin/trash/cleanup */
    async cleanup(token?: string): Promise<TrashCleanupResponse> {
      const { data } = await apiClient.post<TrashCleanupResponse>('/admin/trash/cleanup', undefined, { token });
      return data;
    },
    /** GET /admin/trash/reclamation-potential */
    async getReclamationPotential(token?: string): Promise<ReclamationPotential> {
      const { data } = await apiClient.get<ReclamationPotential>('/admin/trash/reclamation-potential', { token });
      return data;
    },
  },
} as const;

export default adminApi;
