# OAuth Production Setup Guide

This guide provides step-by-step instructions for configuring OAuth authentication (Google and GitHub) for the AI Part Designer in production environments.

## Overview

The AI Part Designer supports OAuth 2.0 authentication with:
- **Google OAuth** - For Google account sign-in
- **GitHub OAuth** - For GitHub account sign-in

OAuth provides users with a secure, passwordless authentication option and simplifies onboarding.

## Prerequisites

- Production domain configured (e.g., `assemblematic.ai`)
- HTTPS enabled with valid SSL certificate
- Access to Google Cloud Console (for Google OAuth)
- Access to GitHub Developer Settings (for GitHub OAuth)

---

## Google OAuth Configuration

### Step 1: Create Google Cloud Project

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note the Project ID for reference

### Step 2: Enable Google OAuth API

1. In the Google Cloud Console, navigate to **APIs & Services** > **Library**
2. Search for "Google+ API" or "Google Identity"
3. Click **Enable** to activate the API

### Step 3: Configure OAuth Consent Screen

1. Navigate to **APIs & Services** > **OAuth consent screen**
2. Choose **External** user type (unless using Google Workspace)
3. Fill in the required information:
   - **App name**: `AI Part Designer` (or your app name)
   - **User support email**: Your support email
   - **Developer contact email**: Your technical contact email
   - **App logo**: Upload your app logo (optional)
4. Add scopes:
   - `openid`
   - `email`
   - `profile`
5. Add test users if still in testing phase
6. Click **Save and Continue**

### Step 4: Create OAuth Credentials

1. Navigate to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Select **Application type**: **Web application**
4. Configure the OAuth client:
   - **Name**: `AI Part Designer Production`
   - **Authorized JavaScript origins**:
     - `https://assemblematic.ai`
     - `https://www.assemblematic.ai` (if applicable)
   - **Authorized redirect URIs**:
     - `https://assemblematic.ai/api/v1/auth/oauth/google/callback`
     - `https://www.assemblematic.ai/api/v1/auth/oauth/google/callback` (if applicable)
5. Click **Create**
6. **Save the Client ID and Client Secret** - you'll need these for configuration

### Step 5: Publish the App (When Ready)

1. Return to **OAuth consent screen**
2. Click **Publish App** when ready for production
3. Submit for verification if requesting sensitive scopes

---

## GitHub OAuth Configuration

### Step 1: Register OAuth Application

1. Navigate to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **OAuth Apps** > **New OAuth App**
3. Fill in the application details:
   - **Application name**: `AI Part Designer`
   - **Homepage URL**: `https://assemblematic.ai`
   - **Application description**: Brief description of your app
   - **Authorization callback URL**: `https://assemblematic.ai/api/v1/auth/oauth/github/callback`
4. Click **Register application**

### Step 2: Generate Client Secret

1. After registering, you'll see your **Client ID**
2. Click **Generate a new client secret**
3. **Save the Client ID and Client Secret** immediately - the secret is only shown once

### Step 3: Configure Additional Settings (Optional)

1. **Enable Device Flow**: Leave disabled unless needed
2. **Webhook URL**: Can be configured later if needed
3. **Permissions**: The default `user:email` and `read:user` scopes are sufficient

---

## Backend Configuration

### Production Environment Variables

Add the following environment variables to your production backend configuration:

```bash
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth Configuration
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# OAuth Redirect Base URL (CRITICAL - must match your production domain)
OAUTH_REDIRECT_BASE=https://assemblematic.ai

# Frontend URL for post-authentication redirects
FRONTEND_URL=https://assemblematic.ai
```

### Kubernetes/Helm Configuration

If deploying with Kubernetes/Helm, add OAuth credentials to your secrets:

```bash
# Create OAuth secrets
kubectl create secret generic oauth-secrets \
  --namespace=ai-part-designer-prod \
  --from-literal=google-client-id="your-google-client-id" \
  --from-literal=google-client-secret="your-google-client-secret" \
  --from-literal=github-client-id="your-github-client-id" \
  --from-literal=github-client-secret="your-github-client-secret"
```

Update your `values-production.yaml`:

```yaml
backend:
  env:
    OAUTH_REDIRECT_BASE: "https://assemblematic.ai"
    FRONTEND_URL: "https://assemblematic.ai"
  
  envFrom:
    - secretRef:
        name: oauth-secrets
```

### Docker Compose Configuration

For Docker deployments, update your `.env` file:

```bash
# OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
OAUTH_REDIRECT_BASE=https://assemblematic.ai
FRONTEND_URL=https://assemblematic.ai
```

---

## Testing OAuth Configuration

### Pre-Production Testing Checklist

Before deploying to production, verify OAuth configuration in a staging environment:

- [ ] **Staging Environment Setup**
  - [ ] Configure staging OAuth apps in Google/GitHub
  - [ ] Use staging domain (e.g., `https://staging.assemblematic.ai`)
  - [ ] Test with staging credentials

- [ ] **Redirect URI Validation**
  - [ ] Verify redirect URIs match exactly in provider settings
  - [ ] Test with and without `www` subdomain if applicable
  - [ ] Ensure HTTPS is enforced (no HTTP redirects)

- [ ] **Google OAuth Testing**
  - [ ] Click "Sign in with Google" button
  - [ ] Verify redirect to Google authorization page
  - [ ] Complete authorization
  - [ ] Verify redirect back to application
  - [ ] Confirm user is logged in
  - [ ] Check user profile information is populated

- [ ] **GitHub OAuth Testing**
  - [ ] Click "Sign in with GitHub" button
  - [ ] Verify redirect to GitHub authorization page
  - [ ] Complete authorization
  - [ ] Verify redirect back to application
  - [ ] Confirm user is logged in
  - [ ] Check user profile information is populated

- [ ] **Account Linking**
  - [ ] Create account with email/password
  - [ ] Link Google account from settings
  - [ ] Unlink Google account
  - [ ] Link GitHub account
  - [ ] Test login with GitHub after linking

- [ ] **Error Handling**
  - [ ] Test "Cancel" on OAuth provider page
  - [ ] Test with misconfigured redirect URI
  - [ ] Test account already linked to another user
  - [ ] Verify error messages are user-friendly

### Production Testing Procedure

After deploying to production:

1. **Initial Smoke Test**
   ```bash
   # Test OAuth login endpoints are accessible
   curl -I https://assemblematic.ai/api/v1/auth/oauth/google/login
   curl -I https://assemblematic.ai/api/v1/auth/oauth/github/login
   ```

2. **Manual End-to-End Test**
   - Open incognito/private browser window
   - Navigate to `https://assemblematic.ai/login`
   - Click "Sign in with Google"
   - Complete authentication
   - Verify successful login
   - Repeat for GitHub

3. **Monitor for Errors**
   ```bash
   # Check application logs for OAuth errors
   kubectl logs -n ai-part-designer-prod deployment/backend | grep -i oauth
   ```

4. **Verify Database Connections**
   - Check that OAuth connections are being created
   - Verify user records are properly populated
   - Confirm tokens are being stored securely

---

## Security Considerations

### Redirect URI Security

**CRITICAL**: The redirect URI configuration is crucial for security.

- ✅ **DO**: Use exact URLs with HTTPS
- ✅ **DO**: List all valid production domains
- ❌ **DON'T**: Use wildcards in redirect URIs
- ❌ **DON'T**: Include HTTP URLs in production
- ❌ **DON'T**: Use localhost URLs in production

Example correct configuration:
```
https://assemblematic.ai/api/v1/auth/oauth/google/callback
```

Example incorrect configuration:
```
http://assemblematic.ai/api/v1/auth/oauth/google/callback  ❌ (HTTP)
https://*.assemblematic.ai/api/v1/auth/oauth/google/callback  ❌ (Wildcard)
```

### Client Secret Management

- **Store secrets securely**: Use Kubernetes secrets, AWS Secrets Manager, or similar
- **Never commit secrets** to version control
- **Rotate secrets regularly**: At least annually, or immediately if compromised
- **Limit access**: Only authorized personnel should have access to OAuth credentials
- **Use separate credentials** for each environment (dev, staging, production)

### State Parameter (CSRF Protection)

The application automatically generates and validates a state parameter for CSRF protection. Ensure:
- Sessions are properly configured with secure cookies
- State validation is not disabled in production code

### Token Storage

OAuth access and refresh tokens are stored in the database:
- Tokens are encrypted at rest (database encryption)
- Tokens are only transmitted over HTTPS
- Refresh tokens are rotated on use when possible

---

## Troubleshooting

### Common Issues

#### Issue: "Redirect URI mismatch" error

**Cause**: The redirect URI in your code doesn't match the URI registered with the provider.

**Solution**:
1. Check `OAUTH_REDIRECT_BASE` environment variable
2. Verify it matches exactly what's registered in Google/GitHub
3. Ensure no trailing slashes or typos
4. Check for HTTP vs HTTPS mismatch

#### Issue: OAuth button doesn't work / no redirect

**Cause**: OAuth provider credentials not configured or invalid.

**Solution**:
1. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
2. Check application logs for configuration errors
3. Ensure OAuth provider app is not disabled

#### Issue: "This app has not been verified" warning (Google)

**Cause**: Google OAuth app is still in testing mode or not verified.

**Solution**:
1. For internal use: Add users to test users list
2. For public use: Submit app for verification
3. Or click "Advanced" > "Go to [App Name] (unsafe)" during testing

#### Issue: User gets "Access Denied" after authorization

**Cause**: User denied permissions, or required scopes not granted.

**Solution**:
1. Ensure user accepts all requested permissions
2. Verify scopes are correctly configured
3. Check if user's account has restrictions

#### Issue: Tokens not being saved / user not created

**Cause**: Database connection issue or validation error.

**Solution**:
1. Check application logs for database errors
2. Verify user email format is valid
3. Check database constraints (unique email, etc.)

### Debug Logging

Enable debug logging for OAuth:

```bash
# Set environment variable
LOG_LEVEL=DEBUG

# Watch logs
kubectl logs -f -n ai-part-designer-prod deployment/backend | grep -i oauth
```

### Testing Redirect URIs

Use this script to test redirect URI configuration:

```bash
#!/bin/bash
# test-oauth-config.sh

DOMAIN="https://assemblematic.ai"
ENDPOINTS=(
  "/api/v1/auth/oauth/google/login"
  "/api/v1/auth/oauth/github/login"
)

echo "Testing OAuth endpoints on $DOMAIN"
echo "======================================"

for endpoint in "${ENDPOINTS[@]}"; do
  echo ""
  echo "Testing: $endpoint"
  response=$(curl -s -w "\n%{http_code}" "$DOMAIN$endpoint")
  status=$(echo "$response" | tail -n1)
  
  if [ "$status" = "200" ] || [ "$status" = "302" ]; then
    echo "✅ PASS - Status: $status"
  else
    echo "❌ FAIL - Status: $status"
  fi
done
```

---

## Maintenance

### Regular Tasks

- **Review OAuth logs**: Monitor for suspicious activity or errors
- **Update test users**: Keep test user list current for staging
- **Rotate secrets**: Rotate client secrets annually
- **Review permissions**: Ensure requested scopes are still necessary
- **Update documentation**: Keep this guide current with any changes

### Monitoring

Set up monitoring for:
- OAuth authentication success/failure rates
- Token refresh failures
- Unusual geographic login patterns
- Failed authorization attempts

Example alert:
```yaml
alert: OAuthFailureRateHigh
expr: rate(oauth_auth_failures[5m]) > 0.1
annotations:
  summary: "High OAuth authentication failure rate"
```

---

## References

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

---

## Support

If you encounter issues not covered in this guide:

1. Check application logs for detailed error messages
2. Review the [OAuth API endpoints documentation](../api/oauth-api.md)
3. Consult the backend team for configuration assistance
4. For provider-specific issues, refer to Google/GitHub support

## Appendix: Environment-Specific Configuration

### Development
```bash
OAUTH_REDIRECT_BASE=http://localhost:5173
FRONTEND_URL=http://localhost:5173
```

### Staging
```bash
OAUTH_REDIRECT_BASE=https://staging.assemblematic.ai
FRONTEND_URL=https://staging.assemblematic.ai
```

### Production
```bash
OAUTH_REDIRECT_BASE=https://assemblematic.ai
FRONTEND_URL=https://assemblematic.ai
```
