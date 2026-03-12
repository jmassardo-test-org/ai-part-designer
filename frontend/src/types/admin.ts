/**
 * Admin Dashboard Types.
 *
 * Type definitions for admin panel functionality including:
 * - Analytics data
 * - User management
 * - Project/Design management
 * - Template management
 * - Job monitoring
 * - Content moderation
 * - Credit & subscription management
 * - Coupon & promotions
 * - Organization management
 * - Component library management
 * - Notification management
 * - File/storage management
 * - Audit logs & security
 * - API key management
 * - System health monitoring
 * - CAD v2 / starters / marketplace
 * - Content management (FAQ/articles)
 * - Assemblies, vendors, BOM
 * - Conversations & AI interactions
 * - Trash & data retention
 */

// =============================================================================
// Generic / Shared Types
// =============================================================================

/** Standard paginated list metadata. */
export interface PaginationParams {
  page?: number;
  page_size?: number;
}

/** Generic message response from the backend. */
export interface MessageResponse {
  message: string;
  [key: string]: unknown;
}

/** Result of a bulk operation. */
export interface BulkActionResult {
  total: number;
  success_count: number;
  failure_count: number;
  errors: Array<Record<string, unknown>>;
}

// =============================================================================
// Analytics Types
// =============================================================================

export interface AnalyticsOverview {
  total_users: number;
  active_users_daily: number;
  active_users_weekly: number;
  active_users_monthly: number;
  new_signups_today: number;
  new_signups_week: number;
  total_projects: number;
  total_designs: number;
  total_generations_today: number;
  total_generations_week: number;
  total_storage_bytes: number;
  storage_used_bytes: number;
  storage_limit_bytes: number;
  total_templates: number;
  total_jobs: number;
  pending_jobs: number;
  failed_jobs_today: number;
}

export interface UserAnalytics {
  period: string;
  total_users: number;
  new_users: number;
  active_users: number;
  churned_users: number;
  users_by_tier: Record<string, number>;
}

export interface GenerationAnalytics {
  period: string;
  total_generations: number;
  ai_generations: number;
  template_generations: number;
  import_count: number;
  success_rate: number;
  avg_generation_time_ms: number | null;
}

export interface JobAnalytics {
  period: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  pending_jobs: number;
  success_rate: number;
  avg_processing_time_ms: number | null;
  jobs_by_type: Record<string, number>;
}

export interface StorageAnalytics {
  total_storage_bytes: number;
  used_storage_bytes: number;
  storage_by_type: Record<string, number>;
  largest_users: Array<Record<string, unknown>>;
}

export interface RevenueAnalytics {
  monthly_recurring_revenue_cents: number;
  total_revenue_cents: number;
  churn_rate: number;
  upgrades_count: number;
  downgrades_count: number;
  subscribers_by_tier: Record<string, number>;
  period: string;
}

export interface TimeSeriesDataPoint {
  date: string;
  value: number;
}

export interface TimeSeriesAnalytics {
  new_users: TimeSeriesDataPoint[];
  active_users: TimeSeriesDataPoint[];
  new_projects: TimeSeriesDataPoint[];
  new_designs: TimeSeriesDataPoint[];
  jobs_completed: TimeSeriesDataPoint[];
}

// =============================================================================
// Moderation Types
// =============================================================================

export interface ModerationItem {
  id: string;
  design_id: string | null;
  user_id: string;
  user_email: string | null;
  content_type: string;
  content_text: string | null;
  decision: string;
  reason: string | null;
  confidence_score: number | null;
  details: Record<string, unknown>;
  is_appealed: boolean;
  created_at: string;
}

export interface ModerationQueueResponse {
  items: ModerationItem[];
  total: number;
  page: number;
  page_size: number;
  pending_count: number;
  escalated_count: number;
}

export interface ModerationStats {
  pending_count: number;
  escalated_count: number;
  approved_today: number;
  rejected_today: number;
  appeals_pending: number;
  avg_review_time_hours: number | null;
}

export interface ModerationDecisionRequest {
  notes?: string;
}

export interface RejectContentRequest {
  reason: string;
  notes?: string;
  warn_user?: boolean;
}

export interface ModerationDecisionResponse {
  id: string;
  decision: string;
  reviewed_by: string;
  reviewed_at: string;
  message: string;
}

// =============================================================================
// User Management Types
// =============================================================================

export interface AdminUser {
  id: string;
  email: string;
  display_name: string;
  role: string;
  status: string;
  is_active: boolean;
  is_suspended: boolean;
  storage_used_bytes: number;
  warning_count: number;
  suspension_reason: string | null;
  suspended_until: string | null;
  email_verified_at: string | null;
  last_login_at: string | null;
  created_at: string;
  project_count: number;
  design_count: number;
  subscription_tier: string | null;
}

export interface AdminUserDetails extends AdminUser {
  projects: AdminProject[];
  recent_designs: AdminDesign[];
  warnings: UserWarning[];
  login_history: LoginHistoryEntry[];
}

export interface UserWarning {
  id: string;
  user_id: string;
  category: string;
  severity: string;
  message: string;
  acknowledged: boolean;
  created_at: string;
  expires_at: string | null;
}

export interface UserWarningRequest {
  category: string;
  severity?: string;
  message: string;
  expires_in_days?: number;
}

export interface UserBanRequest {
  reason: string;
  is_permanent?: boolean;
  duration_days?: number;
}

export interface UserBanResponse {
  id: string;
  user_id: string;
  reason: string;
  is_permanent: boolean;
  expires_at: string | null;
  created_at: string;
}

export interface PasswordResetResponse {
  message: string;
  email_sent: boolean;
}

export interface LoginHistoryEntry {
  timestamp: string;
  ip_address: string | null;
  user_agent: string | null;
  success: boolean;
}

export interface LoginHistoryResponse {
  entries: LoginHistoryEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface ActivityEntry {
  type: string;
  resource_id: string;
  resource_name: string | null;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface ActivityFeedResponse {
  activities: ActivityEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserUpdateRequest {
  display_name?: string;
  role?: string;
  status?: string;
}

export interface UserListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

export interface SuspendUserRequest {
  reason: string;
  duration_days?: number;
}

export interface ImpersonateResponse {
  access_token: string;
  user_id: string;
  user_email: string;
  expires_at: string;
  audit_id: string;
}

export interface ForceEmailVerifyResponse {
  id: string;
  email: string;
  email_verified_at: string;
  message: string;
}

export interface BulkUserActionRequest {
  action: 'suspend' | 'unsuspend' | 'delete';
  user_ids: string[];
  reason?: string;
}

export interface UserFilterParams extends PaginationParams {
  search?: string;
  role?: string;
  is_active?: boolean;
  is_suspended?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// =============================================================================
// Project Management Types
// =============================================================================

export interface AdminProject {
  id: string;
  name: string;
  description: string | null;
  user_id: string;
  user_email: string | null;
  owner_email: string | null;
  is_public: boolean;
  storage_used_bytes: number;
  design_count: number;
  status: string;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectListResponse {
  projects: AdminProject[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProjectFilterParams extends PaginationParams {
  search?: string;
  owner_id?: string;
  is_public?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface SuspendProjectRequest {
  reason: string;
}

export interface TransferOwnershipRequest {
  new_owner_id: string;
  reason?: string;
}

export interface BulkProjectActionRequest {
  action: string;
  project_ids: string[];
  reason?: string;
}

// =============================================================================
// Design Management Types
// =============================================================================

export interface AdminDesign {
  id: string;
  name: string;
  description: string | null;
  source_type: string;
  status: string;
  project_id: string;
  project_name: string | null;
  user_id: string | null;
  user_email: string | null;
  owner_email: string | null;
  template_id: string | null;
  is_public: boolean;
  is_deleted: boolean;
  file_format: string | null;
  file_size_bytes: number;
  created_at: string;
  updated_at: string | null;
}

export interface DesignListResponse {
  designs: AdminDesign[];
  total: number;
  page: number;
  page_size: number;
}

export interface DesignFilterParams extends PaginationParams {
  search?: string;
  owner_id?: string;
  project_id?: string;
  is_public?: boolean;
  is_deleted?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface VisibilityChangeRequest {
  is_public: boolean;
}

export interface DesignVersionResponse {
  id: string;
  design_id: string;
  version_number: number;
  created_at: string;
  created_by: string | null;
  file_size_bytes: number;
  notes: string | null;
}

export interface DesignVersionListResponse {
  versions: DesignVersionResponse[];
  total: number;
}

export interface BulkDesignActionRequest {
  action: string;
  design_ids: string[];
  reason?: string;
}

export interface TransferDesignRequest {
  new_owner_id: string;
  reason?: string;
}

// =============================================================================
// Template Management Types
// =============================================================================

export interface AdminTemplate {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  category: string;
  is_active: boolean;
  is_featured: boolean;
  min_tier: string;
  use_count: number;
  creator_email: string | null;
  parameter_schema: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
  preview_url: string | null;
}

export interface TemplateListResponse {
  templates: AdminTemplate[];
  total: number;
  page: number;
  page_size: number;
}

export interface TemplateCreateRequest {
  name: string;
  slug: string;
  description?: string;
  category: string;
  subcategory?: string;
  parameters: Record<string, unknown>;
  default_values: Record<string, unknown>;
  cadquery_script: string;
  min_tier?: string;
  is_active?: boolean;
  is_featured?: boolean;
}

export interface TemplateUpdateRequest {
  name?: string;
  description?: string;
  category?: string;
  subcategory?: string;
  parameters?: Record<string, unknown>;
  default_values?: Record<string, unknown>;
  cadquery_script?: string;
  min_tier?: string;
  is_active?: boolean;
  is_featured?: boolean;
}

export interface TemplateFilterParams extends PaginationParams {
  search?: string;
  category?: string;
  is_enabled?: boolean;
  is_featured?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ReorderTemplatesRequest {
  template_ids: string[];
}

export interface TemplateAnalyticsResponse {
  total_templates: number;
  active_templates: number;
  featured_templates: number;
  most_used: Array<Record<string, unknown>>;
  by_category: Record<string, number>;
}

// =============================================================================
// Job Management Types
// =============================================================================

export type AdminJobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
export type AdminJobType = 'cad_generation' | 'export' | 'ai_processing' | 'file_conversion';

export interface AdminJob {
  id: string;
  job_type: string;
  status: AdminJobStatus;
  user_id: string;
  user_email: string | null;
  design_id: string | null;
  progress: number;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  processing_time_ms: number | null;
}

export interface JobListResponse {
  jobs: AdminJob[];
  total: number;
  page: number;
  page_size: number;
}

export interface JobFilterParams extends PaginationParams {
  status?: AdminJobStatus;
  type?: AdminJobType;
  user_id?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface JobPriorityRequest {
  priority: number;
}

export interface JobStatsResponse {
  total_jobs: number;
  pending_jobs: number;
  processing_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  avg_processing_time_ms: number | null;
  jobs_by_type: Record<string, number>;
}

export interface QueueStatusResponse {
  queue_length: number;
  active_workers: number;
  pending_tasks: number;
  scheduled_tasks: number;
  reserved_tasks: number;
}

export interface PurgeJobsResponse {
  purged_count: number;
  message: string;
}

export interface WorkerInfo {
  name: string;
  status: string;
  active_tasks: number;
  completed_tasks: number;
  [key: string]: unknown;
}

// =============================================================================
// Subscription Management Types
// =============================================================================

export interface AdminSubscription {
  id: string;
  user_id: string;
  user_email: string | null;
  tier_slug: string;
  tier_name: string;
  status: string;
  stripe_subscription_id: string | null;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
}

export interface SubscriptionListResponse {
  items: AdminSubscription[];
  total: number;
  page: number;
  page_size: number;
}

export interface SubscriptionFilterParams extends PaginationParams {
  status_filter?: string;
  tier_filter?: string;
}

export interface ChangeTierRequest {
  tier: string;
}

export interface ExtendSubscriptionRequest {
  days: number;
}

// =============================================================================
// Credit Management Types
// =============================================================================

export interface UserCredits {
  user_id: string;
  balance: number;
  lifetime_earned: number;
  lifetime_spent: number;
}

export interface CreditHistoryEntry {
  id: string;
  amount: number;
  transaction_type: string;
  description: string;
  balance_before: number;
  balance_after: number;
  created_at: string;
  admin_email: string | null;
}

export interface CreditHistoryResponse {
  items: CreditHistoryEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface QuotaResponse {
  user_id: string;
  storage_used_bytes: number;
  storage_limit_gb: number;
  projects_count: number;
  projects_limit: number;
  designs_count: number;
  designs_limit: number;
  jobs_today: number;
  jobs_limit: number;
}

export interface QuotaOverrideRequest {
  storage_limit_gb?: number;
  projects_limit?: number;
  designs_limit?: number;
  jobs_limit?: number;
  expires_at?: string;
}

export interface CreditDistributionResponse {
  total_credits_issued: number;
  total_credits_used: number;
  avg_balance: number;
  total_users_with_balance: number;
  distribution_by_tier: Array<{
    tier: string;
    total_balance: number;
    avg_balance: number;
    user_count: number;
  }>;
}

export interface LowBalanceUserEntry {
  user_id: string;
  email: string;
  balance: number;
  tier: string | null;
}

export interface LowBalanceUsersResponse {
  items: LowBalanceUserEntry[];
  total: number;
  page: number;
  page_size: number;
  threshold: number;
}

// =============================================================================
// Billing Types
// =============================================================================

export interface FailedPaymentEntry {
  user_id: string;
  user_email: string | null;
  amount_cents: number;
  error: string | null;
  date: string;
  retry_count: number;
}

export interface FailedPaymentsResponse {
  items: FailedPaymentEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface BillingRevenueResponse {
  total_revenue_cents: number;
  revenue_by_tier: Record<string, number>;
  revenue_by_period: Array<Record<string, unknown>>;
  period: string;
}

export interface TierDefinitionResponse {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  monthly_credits: number;
  max_concurrent_jobs: number;
  max_storage_gb: number;
  max_projects: number;
  max_designs_per_project: number;
  max_file_size_mb: number;
  features: Record<string, unknown>;
  price_monthly_cents: number;
  price_yearly_cents: number;
  display_order: number;
  is_active: boolean;
}

export interface UpdateTierRequest {
  name?: string;
  description?: string;
  monthly_credits?: number;
  max_concurrent_jobs?: number;
  max_storage_gb?: number;
  max_projects?: number;
  max_designs_per_project?: number;
  max_file_size_mb?: number;
  features?: Record<string, unknown>;
  price_monthly_cents?: number;
  price_yearly_cents?: number;
}

// =============================================================================
// Coupon & Promotion Types
// =============================================================================

export interface AdminCoupon {
  id: string;
  code: string;
  description: string | null;
  coupon_type: string;
  discount_percent: number | null;
  discount_amount: number | null;
  free_credits: number | null;
  upgrade_tier: string | null;
  valid_from: string | null;
  valid_until: string | null;
  is_active: boolean;
  max_uses: number | null;
  max_uses_per_user: number;
  current_uses: number;
  restricted_to_tiers: string[] | null;
  new_users_only: boolean;
  created_at: string;
  created_by: string | null;
}

export interface CouponListResponse {
  items: AdminCoupon[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreateCouponRequest {
  code: string;
  description?: string;
  coupon_type: string;
  discount_percent?: number;
  discount_amount?: number;
  free_credits?: number;
  upgrade_tier?: string;
  valid_from?: string;
  valid_until?: string;
  max_uses?: number;
  max_uses_per_user?: number;
  restricted_to_tiers?: string[];
  new_users_only?: boolean;
}

export interface UpdateCouponRequest {
  description?: string;
  valid_from?: string;
  valid_until?: string;
  max_uses?: number;
  max_uses_per_user?: number;
  is_active?: boolean;
  restricted_to_tiers?: string[];
  new_users_only?: boolean;
}

export interface CouponRedemption {
  id: string;
  coupon_id: string;
  user_id: string;
  user_email: string | null;
  redeemed_at: string;
}

export interface CouponUsageResponse {
  items: CouponRedemption[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApplyCouponRequest {
  coupon_code: string;
}

export interface GrantTrialRequest {
  tier: string;
  duration_days: number;
}

export interface ExtendTrialRequest {
  additional_days: number;
}

export interface BulkApplyCouponRequest {
  coupon_code: string;
  target: string;
  target_value?: string;
}

export interface PromotionAnalyticsResponse {
  total_coupons: number;
  active_coupons: number;
  total_redemptions: number;
  most_used_coupons: Array<Record<string, unknown>>;
}

export interface CouponFilterParams extends PaginationParams {
  status?: string;
  type?: string;
  search?: string;
}

// =============================================================================
// Organization Management Types
// =============================================================================

export interface AdminOrganization {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  member_count: number;
  owner_id: string | null;
  owner_email: string | null;
  tier_slug: string | null;
  created_at: string;
}

export interface OrganizationListResponse {
  items: AdminOrganization[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminOrgMember {
  id: string;
  user_id: string;
  user_email: string | null;
  role: string;
  joined_at: string;
}

export interface OrganizationFilterParams extends PaginationParams {
  search?: string;
}

export interface EditOrganizationRequest {
  name?: string;
  settings?: Record<string, unknown>;
}

export interface AddOrgMemberRequest {
  user_id: string;
  role?: string;
}

export interface ChangeOrgMemberRoleRequest {
  role: string;
}

export interface TransferOrgOwnershipRequest {
  new_owner_id: string;
}

export interface AddOrgCreditsRequest {
  amount: number;
  reason: string;
}

export interface ChangeOrgTierRequest {
  tier: string;
}

export interface OrgAuditLogEntry {
  id: string;
  user_id: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface OrgAuditLogResponse {
  items: OrgAuditLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface OrgStatsResponse {
  org_id: string;
  member_count: number;
  project_count: number;
  design_count: number;
  storage_used_bytes: number;
  credits_balance: number;
  credits_used: number;
}

// =============================================================================
// Component Library Management Types
// =============================================================================

export interface AdminComponent {
  id: string;
  name: string;
  part_number: string | null;
  manufacturer: string | null;
  category: string | null;
  user_id: string | null;
  user_email: string | null;
  is_library: boolean;
  is_verified: boolean;
  is_featured: boolean;
  created_at: string;
}

export interface ComponentListResponse {
  items: AdminComponent[];
  total: number;
  page: number;
  page_size: number;
}

export interface ComponentFilterParams extends PaginationParams {
  search?: string;
  library_only?: boolean;
}

export interface CreateComponentRequest {
  name: string;
  part_number?: string;
  manufacturer?: string;
  category?: string;
  description?: string;
  is_library?: boolean;
}

export interface EditComponentRequest {
  name?: string;
  part_number?: string;
  manufacturer?: string;
  category?: string;
  description?: string;
  is_library?: boolean;
  is_verified?: boolean;
  is_featured?: boolean;
}

export interface ComponentAnalyticsResponse {
  total_components: number;
  library_components: number;
  verified_components: number;
  featured_components: number;
  by_category: Record<string, number>;
  most_used: Array<Record<string, unknown>>;
}

// =============================================================================
// Notification Management Types
// =============================================================================

export interface AdminNotification {
  id: string;
  user_id: string;
  user_email: string | null;
  notification_type: string;
  title: string;
  message: string | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: AdminNotification[];
  total: number;
  page: number;
  page_size: number;
}

export interface NotificationFilterParams extends PaginationParams {
  notification_type?: string;
}

export type RecipientType = 'all' | 'tier' | 'organization' | 'users';

export interface CreateAnnouncementRequest {
  title: string;
  message: string;
  recipient_type?: RecipientType;
  target_tier?: string;
  target_organization_id?: string;
  target_user_ids?: string[];
  scheduled_at?: string;
  expires_at?: string;
}

export interface AnnouncementResponse {
  message: string;
  sent_count?: number;
  recipient_type?: string;
  scheduled?: boolean;
  scheduled_at?: string;
}

export interface NotificationStatsResponse {
  total: number;
  unread: number;
  read: number;
  read_rate_percent: number;
  sent_today: number;
  sent_this_week: number;
  expired: number;
}

export interface TargetedNotificationRequest {
  title: string;
  message: string;
  target_type: 'tier' | 'role' | 'org';
  target_value: string;
  url?: string;
}

export interface ScheduledNotificationRequest {
  title: string;
  message: string;
  scheduled_at: string;
  recipient_type?: string;
  recipients?: string[];
}

export interface NotificationTemplate {
  id: string;
  name: string;
  subject: string;
  body_template: string;
  variables: string[];
}

export interface CreateNotificationTemplateRequest {
  name: string;
  subject: string;
  body_template: string;
  variables?: string[];
}

// =============================================================================
// File/Storage Management Types
// =============================================================================

export interface AdminFile {
  id: string;
  user_id: string;
  user_email: string | null;
  filename: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  storage_bucket: string;
  created_at: string;
}

export interface FileListResponse {
  items: AdminFile[];
  total: number;
  page: number;
  page_size: number;
}

export interface FileFilterParams extends PaginationParams {
  user_id?: string;
  mime_type?: string;
}

export interface AdminFileDetail {
  id: string;
  user_id: string;
  user_email: string | null;
  user_display_name: string | null;
  filename: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  file_type: string;
  cad_format: string | null;
  storage_bucket: string;
  storage_path: string;
  status: string;
  scan_status: string | null;
  checksum_sha256: string | null;
  download_url: string;
  thumbnail_url: string | null;
  preview_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface FlaggedFile {
  id: string;
  file_id: string | null;
  filename: string | null;
  user_id: string | null;
  user_email: string | null;
  content_type: string;
  reason: string | null;
  decision: string;
  reviewer_id: string | null;
  created_at: string;
}

export interface FlaggedFileListResponse {
  items: FlaggedFile[];
  total: number;
  page: number;
  page_size: number;
}

export interface StorageQuotaRequest {
  storage_limit_bytes: number;
}

export interface TopStorageUserEntry {
  user_id: string;
  email: string | null;
  display_name: string | null;
  file_count: number;
  total_size_bytes: number;
  total_size_mb: number;
}

export interface TopStorageUsersResponse {
  users: TopStorageUserEntry[];
}

export interface StorageStats {
  total_files: number;
  total_size_bytes: number;
  total_size_gb: number;
  files_by_type: Record<string, number>;
  top_users: Array<Record<string, unknown>>;
}

export interface AdminStorageAnalytics {
  total_files: number;
  total_size_bytes: number;
  total_size_gb: number;
  files_by_type: Record<string, number>;
  files_by_status: Record<string, number>;
  uploads_per_day: Array<Record<string, unknown>>;
}

export interface GarbageCollectResponse {
  files_cleaned: number;
  space_reclaimed_bytes: number;
  space_reclaimed_mb: number;
  message: string;
}

export interface FailedUpload {
  id: string;
  user_id: string;
  user_email: string | null;
  filename: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  status: string;
  created_at: string;
}

export interface FailedUploadListResponse {
  items: FailedUpload[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// Audit Log Types
// =============================================================================

export interface AdminAuditLog {
  id: string;
  user_id: string | null;
  user_email: string | null;
  actor_type: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AdminAuditLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface AuditLogFilterParams extends PaginationParams {
  user_id?: string;
  action?: string;
  resource_type?: string;
  start_date?: string;
  end_date?: string;
}

// =============================================================================
// Security Types
// =============================================================================

export interface SecurityEvent {
  id: string;
  event_type: string;
  severity: string | null;
  user_id: string | null;
  user_email: string | null;
  resource_type: string | null;
  ip_address: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SecurityEventListResponse {
  items: SecurityEvent[];
  total: number;
  page: number;
  page_size: number;
}

export interface SecurityEventFilterParams extends PaginationParams {
  event_type?: string;
  severity?: string;
  start_date?: string;
  end_date?: string;
}

export interface FailedLoginEntry {
  user_email: string | null;
  user_id: string | null;
  ip_address: string | null;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface FailedLoginListResponse {
  items: FailedLoginEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface BlockedIPEntry {
  ip_address: string;
  reason: string | null;
  blocked_at: string;
  blocked_by: string | null;
}

export interface BlockIPRequest {
  ip_address: string;
  reason: string;
}

export interface ActiveSession {
  session_id: string;
  user_id: string | null;
  user_email: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string | null;
  last_activity: string | null;
}

export interface ActiveSessionListResponse {
  items: ActiveSession[];
  total: number;
  page: number;
  page_size: number;
}

export interface SecurityDashboard {
  failed_logins_24h: number;
  blocked_ips_count: number;
  active_sessions: number;
  security_events_24h: number;
  threat_level: string;
}

// =============================================================================
// API Key Management Types
// =============================================================================

export interface AdminAPIKey {
  id: string;
  user_id: string;
  user_email: string | null;
  name: string;
  key_prefix: string;
  scopes: string[];
  is_active: boolean;
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export interface APIKeyListResponse {
  items: AdminAPIKey[];
  total: number;
  page: number;
  page_size: number;
}

export interface APIKeyFilterParams extends PaginationParams {
  user_id?: string;
}

export interface APIKeyUsageResponse {
  key_id: string;
  total_requests: number;
  last_used_at: string | null;
  last_used_ip: string | null;
  requests_by_endpoint: Record<string, number>;
  requests_by_day: Array<Record<string, unknown>>;
}

export interface APIKeyAggregateStats {
  total_keys: number;
  active_keys: number;
  revoked_keys: number;
  expired_keys: number;
  total_requests_24h: number;
}

export interface RateLimitViolationEntry {
  user_id: string | null;
  user_email: string | null;
  key_prefix: string | null;
  endpoint: string | null;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface RateLimitViolationsResponse {
  items: RateLimitViolationEntry[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// System Health Types
// =============================================================================

export interface ServiceStatus {
  name: string;
  status: 'healthy' | 'degraded' | 'unhealthy';
  latency_ms: number | null;
  message: string | null;
}

export interface SystemHealth {
  overall_status: 'healthy' | 'degraded' | 'unhealthy';
  services: ServiceStatus[];
  version: string;
  uptime_seconds: number;
  last_check: string;
}

export interface SystemVersion {
  version: string;
  api_version: string;
  python_version: string;
  environment: string;
}

export interface ServiceDetail {
  name: string;
  status: string;
  latency_ms: number | null;
  message: string | null;
  details: Record<string, unknown>;
}

export interface PerformanceMetrics {
  avg_response_time_ms: number;
  p95_response_time_ms: number;
  p99_response_time_ms: number;
  error_rate_percent: number;
  requests_per_minute: number;
}

export interface ResourceUtilization {
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
  note: string | null;
}

export interface ErrorLogEntry {
  id: string;
  timestamp: string;
  message: string | null;
  stack_trace: string | null;
  endpoint: string | null;
  user_id: string | null;
  user_email: string | null;
}

export interface ErrorLogListResponse {
  items: ErrorLogEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface AIProviderStatus {
  name: string;
  status: string;
  quota_remaining: number | null;
  quota_total: number | null;
  avg_response_time_ms: number | null;
  last_checked: string;
}

export interface AIProviderListResponse {
  providers: AIProviderStatus[];
}

export interface SystemConfig {
  environment: string;
  debug: boolean;
  api_version: string;
  allowed_origins: string[];
  max_upload_size_mb: number;
  storage_backend: string;
  database_pool_size: number | null;
  redis_configured: boolean;
  ai_service_configured: boolean;
  features: Record<string, boolean>;
}

export interface ManualHealthCheckResponse {
  overall_status: string;
  services: ServiceStatus[];
  checked_at: string;
  duration_ms: number;
}

export interface UptimeResponse {
  uptime_seconds: number;
  uptime_formatted: string;
  start_time: string;
  uptime_percentage_30d: number;
  note: string | null;
}

// =============================================================================
// CAD v2 / Starters / Marketplace Types
// =============================================================================

export interface AdminCADv2Component {
  id: string;
  name: string;
  category: string;
  description: string | null;
  dimensions_mm: [number, number, number];
  aliases: string[];
  mounting_hole_count: number;
  port_count: number;
  is_in_database: boolean;
  database_id: string | null;
  is_verified: boolean;
  is_featured: boolean;
}

export interface CADv2ComponentListResponse {
  items: AdminCADv2Component[];
  total: number;
  categories: Record<string, number>;
}

export interface CADv2RegistrySyncResponse {
  created: number;
  updated: number;
  total_in_registry: number;
  message: string;
}

export interface AdminStarter {
  id: string;
  name: string;
  description: string | null;
  category: string | null;
  tags: string[];
  is_starter: boolean;
  is_public: boolean;
  is_featured: boolean;
  remix_count: number;
  view_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface StarterListResponse {
  items: AdminStarter[];
  total: number;
  page: number;
  page_size: number;
  categories: string[];
}

export interface StarterUpdateRequest {
  name?: string;
  description?: string;
  category?: string;
  tags?: string[];
  is_featured?: boolean;
  is_public?: boolean;
}

export interface AdminMarketplaceStats {
  total_starters: number;
  total_public_designs: number;
  total_remixes_today: number;
  total_remixes_week: number;
  most_remixed: Array<Record<string, unknown>>;
  starters_by_category: Record<string, number>;
}

// =============================================================================
// Content Management Types (FAQ / Articles / Categories)
// =============================================================================

export interface ContentItem {
  id: string;
  content_type: string;
  title: string;
  slug: string;
  body: string;
  category: string | null;
  tags: Record<string, unknown> | null;
  status: string;
  display_order: number;
  is_featured: boolean;
  view_count: number;
  helpful_count: number;
  not_helpful_count: number;
  published_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ContentItemListResponse {
  items: ContentItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface ContentItemCreateRequest {
  title: string;
  body?: string;
  category?: string;
  tags?: Record<string, unknown>;
  status?: string;
  display_order?: number;
  is_featured?: boolean;
}

export interface ContentItemUpdateRequest {
  title?: string;
  body?: string;
  category?: string;
  tags?: Record<string, unknown>;
  status?: string;
  display_order?: number;
  is_featured?: boolean;
}

export interface ContentCategory {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  display_order: number;
  parent_id: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface ContentCategoryCreateRequest {
  name: string;
  slug: string;
  description?: string;
  display_order?: number;
  parent_id?: string;
}

export interface ContentReorderRequest {
  item_orders: Array<{ id: string; display_order: number }>;
}

export interface ContentAnalytics {
  total_faqs: number;
  total_articles: number;
  published_faqs: number;
  published_articles: number;
  total_views: number;
  total_helpful: number;
  total_not_helpful: number;
  popular_items: Array<Record<string, unknown>>;
  categories_breakdown: Array<Record<string, unknown>>;
}

// =============================================================================
// Assembly & BOM Types
// =============================================================================

export interface AdminAssembly {
  id: string;
  name: string;
  description: string | null;
  status: string;
  user_id: string;
  user_email: string | null;
  project_id: string;
  component_count: number;
  version: number;
  created_at: string;
  updated_at: string | null;
}

export interface AdminAssemblyListResponse {
  items: AdminAssembly[];
  total: number;
  page: number;
  page_size: number;
}

export interface AssemblyFilterParams extends PaginationParams {
  user_id?: string;
  search?: string;
  status?: string;
}

export interface AssemblyStats {
  total_assemblies: number;
  avg_components_per_assembly: number;
  assemblies_by_status: Record<string, number>;
  top_categories: Array<Record<string, unknown>>;
  assemblies_created_today: number;
  assemblies_created_this_week: number;
}

export interface AdminVendor {
  id: string;
  name: string;
  display_name: string;
  website: string | null;
  logo_url: string | null;
  api_type: string | null;
  categories: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
}

export interface VendorCreateRequest {
  name: string;
  display_name: string;
  website?: string;
  logo_url?: string;
  api_type?: string;
  categories?: string[];
}

export interface VendorUpdateRequest {
  name?: string;
  display_name?: string;
  website?: string;
  logo_url?: string;
  api_type?: string;
  categories?: string[];
  is_active?: boolean;
}

export interface VendorAnalytics {
  total_vendors: number;
  active_vendors: number;
  most_used_vendors: Array<Record<string, unknown>>;
  part_counts_per_vendor: Array<Record<string, unknown>>;
}

export interface BulkPriceUpdateItem {
  component_id: string;
  new_price: number;
}

export interface BulkPriceUpdateRequest {
  updates: BulkPriceUpdateItem[];
}

export interface BOMAuditItem {
  id: string;
  assembly_id: string;
  component_id: string;
  part_number: string | null;
  description: string;
  category: string;
  unit_cost: number | null;
  vendor_id: string | null;
  reason: string;
}

// =============================================================================
// Conversation & AI Interaction Types
// =============================================================================

export interface ConversationStats {
  total_conversations: number;
  avg_messages_per_conversation: number;
  conversations_by_status: Record<string, number>;
  active_today: number;
  active_this_week: number;
  total_messages: number;
}

export interface FlaggedConversation {
  id: string;
  user_id: string;
  user_email: string | null;
  title: string | null;
  status: string;
  message_count: number;
  flag_reason: string;
  created_at: string;
}

export interface FlaggedConversationListResponse {
  items: FlaggedConversation[];
  total: number;
  page: number;
  page_size: number;
}

export interface ConversationDetail {
  id: string;
  user_id: string;
  user_email: string | null;
  title: string | null;
  status: string;
  design_id: string | null;
  intent_data: Record<string, unknown> | null;
  build_plan_data: Record<string, unknown> | null;
  result_data: Record<string, unknown> | null;
  messages: Array<Record<string, unknown>>;
  created_at: string;
  updated_at: string | null;
}

export interface ConversationQualityMetrics {
  total_conversations: number;
  completed_conversations: number;
  failed_conversations: number;
  completion_rate: number;
  avg_messages_to_completion: number;
  conversations_by_status: Record<string, number>;
}

export interface ConversationFilterParams extends PaginationParams {
  status?: string;
  start_date?: string;
  end_date?: string;
}

// =============================================================================
// Trash & Data Retention Types
// =============================================================================

export type TrashResourceType = 'design' | 'project' | 'assembly' | 'file';

export interface TrashStats {
  deleted_designs: number;
  deleted_projects: number;
  deleted_assemblies: number;
  deleted_files: number;
  total_deleted: number;
  oldest_deleted_at: string | null;
}

export interface RetentionPolicyUpdateRequest {
  retention_days: number;
}

export interface ReclamationPotential {
  reclaimable_files: number;
  reclaimable_bytes: number;
  reclaimable_human: string;
  by_type: Record<string, number>;
}

export interface TrashCleanupResponse {
  message: string;
  retention_days: number;
  cleaned: Record<string, number>;
  total_cleaned: number;
}
