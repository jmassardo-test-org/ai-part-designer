/**
 * Type definitions for authentication and user management.
 */

/** User roles in the system */
export type UserRole = 'user' | 'pro' | 'admin';

/** User account status */
export type UserStatus = 'pending_verification' | 'active' | 'suspended';

/** User subscription tier */
export type SubscriptionTier = 'free' | 'pro' | 'enterprise';

/** User profile data */
export interface User {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  status: UserStatus;
  subscription_tier: SubscriptionTier;
  created_at: string;
  email_verified_at: string | null;
  /** Computed: true if user has admin role */
  is_admin?: boolean;
  /** Alias for subscription_tier for backwards compatibility */
  tier?: SubscriptionTier;
}

/** Registration request payload */
export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
  accepted_terms: boolean;
}

/** Login request payload */
export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

/** Token response from login/refresh */
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/** User response from registration and /me endpoint */
export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  role: UserRole;
  status: UserStatus;
  subscription_tier: SubscriptionTier;
  created_at: string;
  email_verified_at: string | null;
}

/** Password reset request */
export interface ForgotPasswordRequest {
  email: string;
}

/** Password reset confirmation */
export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

/** Email verification request */
export interface VerifyEmailRequest {
  token: string;
}

/** Generic message response */
export interface MessageResponse {
  message: string;
}

/** API error response */
export interface ApiError {
  detail: string | { msg: string; type: string }[];
}
