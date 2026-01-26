# Security Checklist

This document provides a comprehensive security checklist for deploying and operating the AI Part Designer platform.

## Pre-Deployment Checklist

### Secrets & Keys

- [ ] **SECRET_KEY**: Generate a strong random key (minimum 64 characters)
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(64))"
  ```
- [ ] **Database passwords**: Use strong, unique passwords
- [ ] **Redis password**: Enable authentication in production
- [ ] **Storage credentials**: Use IAM roles where possible, rotate keys regularly
- [ ] **OpenAI API key**: Use scoped keys with minimal permissions
- [ ] **All secrets stored in environment variables or secrets manager**
- [ ] **No secrets in version control** (check .gitignore, scan history)

### TLS/HTTPS

- [ ] TLS 1.3 enabled on all endpoints
- [ ] Valid SSL certificates installed
- [ ] HSTS enabled with preload
- [ ] Certificate pinning for mobile clients
- [ ] Internal service communication encrypted

### Database Security

- [ ] Database accessible only from application servers
- [ ] Strong password for database user
- [ ] Minimal privileges for application database user
- [ ] Separate read-only user for analytics
- [ ] Connection encryption enabled (SSL mode required)
- [ ] Database backups encrypted
- [ ] Point-in-time recovery configured

### Network Security

- [ ] Firewall rules configured (allow only necessary ports)
- [ ] API behind reverse proxy (nginx, CloudFlare, etc.)
- [ ] Internal services not publicly accessible
- [ ] DDoS protection enabled
- [ ] VPC/private networking for backend services

## Application Security Configuration

### Authentication

- [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` ≤ 15
- [ ] `REFRESH_TOKEN_EXPIRE_DAYS` ≤ 7 for standard users
- [ ] bcrypt cost factor ≥ 12
- [ ] Password strength requirements enforced
- [ ] Account lockout after failed attempts
- [ ] Email verification required
- [ ] Rate limiting on auth endpoints

### Authorization

- [ ] RBAC properly configured
- [ ] All endpoints have authentication checks
- [ ] Resource ownership verified before access
- [ ] Admin endpoints require admin role
- [ ] Sharing permissions validated

### Rate Limiting

- [ ] Global rate limiting enabled
- [ ] Per-endpoint limits configured
- [ ] User-based limits for authenticated requests
- [ ] Rate limit headers returned
- [ ] Rate limit exceeded events logged

### CORS

- [ ] Specific origins listed (no wildcards in production)
- [ ] Credentials allowed only for trusted origins
- [ ] Methods restricted to needed HTTP verbs
- [ ] Headers explicitly listed

### Security Headers

| Header | Required Value |
|--------|---------------|
| X-Frame-Options | DENY |
| X-Content-Type-Options | nosniff |
| X-XSS-Protection | 1; mode=block |
| Strict-Transport-Security | max-age=31536000; includeSubDomains |
| Content-Security-Policy | Configured per application |
| Referrer-Policy | strict-origin-when-cross-origin |
| Permissions-Policy | Disable unnecessary features |

## Data Protection

### Encryption at Rest

- [ ] Database encryption enabled (TDE or disk encryption)
- [ ] Object storage encryption enabled
- [ ] Sensitive fields encrypted at application level
- [ ] Encryption keys properly managed
- [ ] Backup encryption verified

### Encryption in Transit

- [ ] All external connections use TLS
- [ ] Database connections use SSL
- [ ] Redis connections encrypted (TLS or stunnel)
- [ ] Internal API calls encrypted

### Data Classification

| Data Type | Classification | Protection |
|-----------|---------------|------------|
| Passwords | Critical | bcrypt hashing |
| API keys | Critical | SHA-256 hashing |
| User email | PII | Encrypted at rest |
| Designs | Confidential | Access control, encryption |
| Audit logs | Internal | Integrity protection |

## Monitoring & Alerting

### Security Logging

- [ ] Authentication events logged
- [ ] Authorization failures logged
- [ ] Rate limit violations logged
- [ ] Suspicious patterns logged
- [ ] Admin actions logged
- [ ] Log retention policy configured
- [ ] Logs protected from tampering

### Alerts

Configure alerts for:
- [ ] Multiple failed login attempts (> 5 in 15 min)
- [ ] Privilege escalation attempts
- [ ] Rate limit exceeded (repeated)
- [ ] New admin user created
- [ ] API key created/revoked
- [ ] Unusual data access patterns
- [ ] Error rate spikes

### Monitoring Dashboard

- [ ] Failed authentication attempts
- [ ] Active sessions count
- [ ] Rate limit hit rate
- [ ] Error rates by endpoint
- [ ] Response times
- [ ] Database connection pool

## Incident Response

### Preparation

- [ ] Incident response plan documented
- [ ] Contact list for security incidents
- [ ] Access to revoke all sessions quickly
- [ ] Database backup restoration tested
- [ ] Log access during incidents

### Response Procedures

1. **Token Compromise**
   - Blacklist affected tokens
   - Force password reset
   - Review access logs

2. **API Key Compromise**
   - Revoke affected key immediately
   - Issue new key
   - Review API key usage

3. **Database Breach**
   - Rotate all secrets
   - Force all password resets
   - Notify affected users
   - Review audit logs

## Regular Security Tasks

### Daily

- [ ] Review security alert dashboard
- [ ] Check failed authentication trends
- [ ] Monitor rate limit violations

### Weekly

- [ ] Review admin activity logs
- [ ] Check for new vulnerabilities (CVEs)
- [ ] Verify backup integrity

### Monthly

- [ ] Rotate API keys where applicable
- [ ] Review user access levels
- [ ] Update dependencies
- [ ] Review security configurations

### Quarterly

- [ ] Security assessment
- [ ] Penetration testing
- [ ] Review and update security policies
- [ ] Incident response drill

## Compliance

### GDPR

- [ ] User data export functionality
- [ ] User data deletion capability
- [ ] Consent tracking
- [ ] Privacy policy updated
- [ ] DPA with processors

### SOC 2

- [ ] Access controls documented
- [ ] Change management process
- [ ] Incident response procedures
- [ ] Employee security training
- [ ] Vendor security review

## Development Security

### Code Security

- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (ORM usage)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection enabled
- [ ] Secure random number generation
- [ ] No sensitive data in logs

### CI/CD Security

- [ ] Dependency scanning (Snyk, Dependabot)
- [ ] SAST scanning (Semgrep, Bandit)
- [ ] Container image scanning
- [ ] Secrets scanning in commits
- [ ] Code review required for merges

### Container Security

- [ ] Non-root container user
- [ ] Minimal base images
- [ ] No secrets in images
- [ ] Image signing enabled
- [ ] Registry access controlled

## Production Environment

### Infrastructure

```
┌─────────────────────────────────────────────────────────┐
│                     Load Balancer                        │
│                   (TLS termination)                      │
└─────────────────────────┬───────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
    ┌─────────────────┐     ┌─────────────────┐
    │   API Server    │     │   API Server    │
    │   (internal)    │     │   (internal)    │
    └────────┬────────┘     └────────┬────────┘
             │                       │
    ┌────────┴───────────────────────┴────────┐
    │                Private Network           │
    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ │
    │  │PostgreSQL│ │  Redis   │ │  MinIO   │ │
    │  └──────────┘ └──────────┘ └──────────┘ │
    └─────────────────────────────────────────┘
```

### Environment Variables (Production)

```bash
# Security - REQUIRED
SECRET_KEY=<64+ char random string>
ENVIRONMENT=production
FORCE_HTTPS=true

# Database - REQUIRED
POSTGRES_HOST=<internal-hostname>
POSTGRES_PASSWORD=<strong-password>

# Redis - REQUIRED
REDIS_HOST=<internal-hostname>
REDIS_PASSWORD=<strong-password>

# Optional but recommended
SENTRY_DSN=<sentry-project-dsn>
OTEL_EXPORTER_ENDPOINT=<otel-collector-endpoint>
```

## Security Contacts

| Role | Contact |
|------|---------|
| Security Lead | TBD |
| On-call Engineer | TBD |
| Legal/Compliance | TBD |

---

Last Updated: 2024-01-15
