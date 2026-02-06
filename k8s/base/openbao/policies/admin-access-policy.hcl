# AI Part Designer Admin Policy
# Full administrative access for operations team and emergency procedures

# Complete access to all ai-part-designer secrets
path "secret/data/ai-part-designer/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/ai-part-designer/*" {
  capabilities = ["list", "read", "delete"]
}

# Access to manage policies
path "sys/policies/acl/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

# Access to authentication methods
path "auth/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

# Audit log access for compliance
path "sys/audit" {
  capabilities = ["read", "list"]
}

path "sys/audit/*" {
  capabilities = ["create", "read", "update", "delete", "list", "sudo"]
}

# Health and metrics
path "sys/health" {
  capabilities = ["read"]
}

path "sys/metrics" {
  capabilities = ["read"]
}

# Seal/unseal operations (emergency only)
path "sys/seal" {
  capabilities = ["update", "sudo"]
}

path "sys/unseal" {
  capabilities = ["update", "sudo"]
}

# Lease management
path "sys/leases/lookup/*" {
  capabilities = ["read", "list"]
}

path "sys/leases/revoke/*" {
  capabilities = ["update", "sudo"]
}
