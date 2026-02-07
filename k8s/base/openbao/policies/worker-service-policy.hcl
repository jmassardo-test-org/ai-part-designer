# AI Part Designer Worker Service Policy
# Grants access to secrets needed by Celery worker processes

# Database credentials - read-only access for workers
path "secret/data/ai-part-designer/database" {
  capabilities = ["read"]
}

# Redis queue credentials
path "secret/data/ai-part-designer/redis" {
  capabilities = ["read"]
}

# AI service API keys for CAD generation
path "secret/data/ai-part-designer/ai-services/openai" {
  capabilities = ["read"]
}

path "secret/data/ai-part-designer/ai-services/anthropic" {
  capabilities = ["read"]
}

# Storage credentials for CAD file uploads
path "secret/data/ai-part-designer/storage/s3-credentials" {
  capabilities = ["read"]
}

path "secret/data/ai-part-designer/storage/minio-credentials" {
  capabilities = ["read"]
}

path "secret/data/ai-part-designer/storage/minio-app-credentials" {
  capabilities = ["read"]
}

# Email service for notifications from workers
path "secret/data/ai-part-designer/email/smtp-config" {
  capabilities = ["read"]
}

# Monitoring for worker telemetry
path "secret/data/ai-part-designer/monitoring/sentry-dsn" {
  capabilities = ["read"]
}

# Worker-specific encryption keys
path "secret/data/ai-part-designer/encryption/worker-keys" {
  capabilities = ["read"]
}
