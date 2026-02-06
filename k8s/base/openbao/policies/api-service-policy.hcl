# AI Part Designer API Service Policy
# Grants access to application secrets needed by the FastAPI backend

# Database credentials - read-only access
path "secret/data/ai-part-designer/database" {
  capabilities = ["read"]
}

# Redis cache credentials
path "secret/data/ai-part-designer/redis" {
  capabilities = ["read"]
}

# JWT and session secrets
path "secret/data/ai-part-designer/auth/jwt-keys" {
  capabilities = ["read"]
}

path "secret/data/ai-part-designer/auth/session-secrets" {
  capabilities = ["read"]
}

# AI service API keys (OpenAI, Anthropic)
path "secret/data/ai-part-designer/ai-services/*" {
  capabilities = ["read"]
}

# Storage credentials (S3/MinIO)
path "secret/data/ai-part-designer/storage/s3-credentials" {
  capabilities = ["read"]
}

# Email service credentials (SMTP)
path "secret/data/ai-part-designer/email/smtp-config" {
  capabilities = ["read"]
}

# Payment processing (Stripe)
path "secret/data/ai-part-designer/payments/stripe-keys" {
  capabilities = ["read"]
}

# OAuth provider credentials
path "secret/data/ai-part-designer/oauth/google" {
  capabilities = ["read"]
}

path "secret/data/ai-part-designer/oauth/github" {
  capabilities = ["read"]
}

# Monitoring and observability
path "secret/data/ai-part-designer/monitoring/sentry-dsn" {
  capabilities = ["read"]
}

# Encryption keys for sensitive data
path "secret/data/ai-part-designer/encryption/data-keys" {
  capabilities = ["read"]
}
