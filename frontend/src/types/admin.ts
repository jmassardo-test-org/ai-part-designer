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
 */

// =============================================================================
// Analytics Types
// =============================================================================

export interface AnalyticsOverview {
  total_users: number;
  active_users_today: number;
  active_users_week: number;
  active_users_month: number;
  total_projects: number;
  total_designs: number;
  total_templates: number;
  total_jobs: number;
  pending_jobs: number;
  failed_jobs: number;
  storage_used_bytes: number;
  storage_limit_bytes: number;
}

export interface UserAnalytics {
  period: string;
  new_users: number;
  active_users: number;
  churned_users: number;
  total_users: number;
}

export interface GenerationAnalytics {
  period: string;
  total_generations: number;
  successful_generations: number;
  failed_generations: number;
  avg_generation_time_seconds: number;
}

export interface JobAnalytics {
  period: string;
  total_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
  avg_queue_time_seconds: number;
  avg_processing_time_seconds: number;
}

export interface StorageAnalytics {
  total_storage_bytes: number;
  used_storage_bytes: number;
  storage_by_type: Record<string, number>;
  top_users: Array<{
    user_id: string;
    email: string;
    storage_used_bytes: number;
  }>;
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
// User Management Types
// =============================================================================

export interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  role: 'user' | 'admin' | 'super_admin';
  is_active: boolean;
  is_suspended: boolean;
  suspension_reason: string | null;
  suspended_until: string | null;
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
  storage_used_bytes: number;
  project_count: number;
  design_count: number;
  warning_count: number;
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
  reason: string;
  severity: 'low' | 'medium' | 'high';
  issued_by: string;
  issued_at: string;
  expires_at: string | null;
}

export interface LoginHistoryEntry {
  timestamp: string;
  ip_address: string;
  user_agent: string;
  success: boolean;
}

export interface UserUpdateRequest {
  full_name?: string;
  role?: 'user' | 'admin' | 'super_admin';
  is_active?: boolean;
  email_verified?: boolean;
}

export interface UserListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// Project Management Types
// =============================================================================

export interface AdminProject {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  owner_email: string;
  is_public: boolean;
  design_count: number;
  storage_used_bytes: number;
  status: 'active' | 'suspended';
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  projects: AdminProject[];
  total: number;
  page: number;
  page_size: number;
}

// =============================================================================
// Design Management Types
// =============================================================================

export interface AdminDesign {
  id: string;
  name: string;
  description: string | null;
  project_id: string;
  project_name: string | null;
  owner_id: string;
  owner_email: string;
  source_type: 'ai_generated' | 'template' | 'uploaded' | 'manual';
  is_public: boolean;
  is_deleted: boolean;
  deleted_at: string | null;
  file_size_bytes: number;
  file_format: string | null;
  created_at: string;
  updated_at: string;
  moderation_status: string | null;
}

export interface DesignListResponse {
  designs: AdminDesign[];
  total: number;
  page: number;
  page_size: number;
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
  min_tier: 'free' | 'starter' | 'professional' | 'enterprise';
  /** @deprecated Use min_tier instead */
  tier?: string;
  created_by: string;
  creator_email: string | null;
  is_enabled: boolean;
  is_active: boolean;
  is_featured: boolean;
  use_count: number;
  parameter_schema: Record<string, unknown>;
  created_at: string;
  updated_at: string;
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
  min_tier?: string;
  parameters: Record<string, unknown>;
  default_values: Record<string, unknown>;
  cadquery_script: string;
  is_active?: boolean;
  is_featured?: boolean;
}

export interface TemplateUpdateRequest {
  name?: string;
  description?: string;
  category?: string;
  min_tier?: string;
  parameter_schema?: Record<string, unknown>;
  cad_script?: string;
  is_active?: boolean;
  is_featured?: boolean;
}

// =============================================================================
// Job Management Types
// =============================================================================

export type AdminJobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
export type AdminJobType = 'cad_generation' | 'export' | 'ai_processing' | 'file_conversion';

export interface AdminJob {
  id: string;
  type: AdminJobType;
  status: AdminJobStatus;
  user_id: string;
  user_email: string | null;
  design_id: string | null;
  priority: number;
  progress: number;
  error_message: string | null;
  retry_count: number;
  max_retries: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  metadata: Record<string, unknown>;
}

export interface JobListResponse {
  jobs: AdminJob[];
  total: number;
  page: number;
  page_size: number;
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

export interface ModerationStats {
  pending_count: number;
  escalated_count: number;
  approved_today: number;
  rejected_today: number;
  appeals_pending: number;
  avg_review_time_hours: number | null;
}

export interface ModerationQueueResponse {
  items: ModerationItem[];
  total: number;
}

// =============================================================================
// Pagination & Filtering Types
// =============================================================================

export interface PaginationParams {
  page?: number;
  page_size?: number;
}

export interface UserFilterParams extends PaginationParams {
  search?: string;
  role?: string;
  is_active?: boolean;
  is_suspended?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface ProjectFilterParams extends PaginationParams {
  search?: string;
  owner_id?: string;
  is_public?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
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

export interface TemplateFilterParams extends PaginationParams {
  search?: string;
  category?: string;
  is_enabled?: boolean;
  is_featured?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface JobFilterParams extends PaginationParams {
  status?: AdminJobStatus;
  type?: AdminJobType;
  user_id?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
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

export interface UserCredits {
  user_id: string;
  balance: number;
  lifetime_earned: number;
  lifetime_spent: number;
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

export interface StorageStats {
  total_files: number;
  total_size_bytes: number;
  total_size_gb: number;
  files_by_type: Record<string, number>;
  top_users: Array<{
    user_id: string;
    email: string | null;
    file_count: number;
    total_size_bytes: number;
  }>;
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