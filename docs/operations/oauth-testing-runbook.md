# OAuth Production Testing Runbook

This runbook provides step-by-step procedures for testing OAuth authentication in production and staging environments.

## Purpose

Ensure OAuth authentication (Google and GitHub) functions correctly in production environments before and after deployments.

## When to Use This Runbook

- ✅ Before initial production deployment
- ✅ After OAuth configuration changes
- ✅ After infrastructure changes (domain, SSL, ingress)
- ✅ During incident response for authentication issues
- ✅ As part of regular security audits

---

## Pre-Test Checklist

Before starting OAuth testing, verify:

- [ ] You have access to test accounts for Google and GitHub
- [ ] You can create temporary test users if needed
- [ ] You have access to application logs
- [ ] You have a way to monitor backend metrics
- [ ] You're using an incognito/private browser window
- [ ] HTTPS is properly configured and valid
- [ ] Backend and frontend services are running

---

## Test Scenarios

### Scenario 1: Google OAuth - New User Registration

**Objective**: Verify new users can sign up using Google OAuth.

**Steps**:

1. **Open Application**
   ```
   URL: https://assemblematic.ai/register
   Browser: Incognito/Private window
   ```

2. **Initiate OAuth Flow**
   - [ ] Click "Sign up with Google" button
   - [ ] Verify button is enabled and visible
   - [ ] Note: Page should redirect to Google

3. **Google Authorization**
   - [ ] Verify redirect to `accounts.google.com`
   - [ ] Verify app name is displayed correctly
   - [ ] Verify requested permissions are shown:
     - Read email address
     - View basic profile information
   - [ ] Click "Continue" or "Allow"

4. **Return to Application**
   - [ ] Verify redirect to application
   - [ ] Expected URL pattern: `https://assemblematic.ai/?access_token=...`
   - [ ] User should be logged in automatically
   - [ ] Profile information should be populated

5. **Verify User Creation**
   - [ ] Check user profile page
   - [ ] Verify email matches Google account
   - [ ] Verify display name is populated
   - [ ] Navigate to settings to confirm OAuth connection listed

**Expected Result**: ✅ New user account created and logged in successfully

**Logging Verification**:
```bash
# Check for successful OAuth flow
kubectl logs -n ai-part-designer-prod deployment/backend --tail=100 | grep "oauth"

# Look for:
# - "OAuth callback successful" or similar
# - User creation log entry
# - No error messages
```

---

### Scenario 2: GitHub OAuth - New User Registration

**Objective**: Verify new users can sign up using GitHub OAuth.

**Steps**:

1. **Open Application**
   ```
   URL: https://assemblematic.ai/register
   Browser: New incognito/private window (different from Google test)
   ```

2. **Initiate OAuth Flow**
   - [ ] Click "Sign up with GitHub" button
   - [ ] Verify redirect to GitHub

3. **GitHub Authorization**
   - [ ] Verify redirect to `github.com/login/oauth/authorize`
   - [ ] Verify app name and description
   - [ ] Verify requested permissions:
     - Read user email
     - Read user profile
   - [ ] Click "Authorize [App Name]"

4. **Return to Application**
   - [ ] Verify redirect back to application
   - [ ] User should be logged in
   - [ ] Profile information populated from GitHub

5. **Verify User Creation**
   - [ ] Check user profile
   - [ ] Verify email from GitHub
   - [ ] Verify username/display name
   - [ ] Check OAuth connections in settings

**Expected Result**: ✅ New user account created via GitHub OAuth

---

### Scenario 3: Google OAuth - Existing User Login

**Objective**: Verify existing users can log in with Google OAuth.

**Prerequisites**: User created in Scenario 1

**Steps**:

1. **Logout** (if logged in)
   ```
   URL: https://assemblematic.ai/logout
   ```

2. **Navigate to Login**
   ```
   URL: https://assemblematic.ai/login
   Browser: Same incognito window or new one
   ```

3. **Initiate Login**
   - [ ] Click "Sign in with Google"
   - [ ] Select the same Google account used in Scenario 1

4. **Verify Login**
   - [ ] Should be logged in immediately (no new registration)
   - [ ] Profile data should match existing account
   - [ ] Check last login timestamp is updated

**Expected Result**: ✅ Existing user logged in successfully

**Database Verification**:
```sql
-- Check OAuth connection
SELECT 
    user_id, 
    provider, 
    provider_email,
    last_used_at,
    created_at
FROM oauth_connections
WHERE provider = 'google'
ORDER BY last_used_at DESC
LIMIT 5;
```

---

### Scenario 4: Account Linking - Add OAuth to Existing Account

**Objective**: Verify users with email/password can link OAuth accounts.

**Prerequisites**: 
- User account created with email/password
- User is logged in

**Steps**:

1. **Navigate to Settings**
   ```
   URL: https://assemblematic.ai/settings/account
   ```

2. **Find Connected Accounts Section**
   - [ ] Verify "Connected Accounts" or "Linked Accounts" section exists
   - [ ] Verify Google and GitHub are listed as options

3. **Link Google Account**
   - [ ] Click "Connect Google" or "Link Google"
   - [ ] Complete Google OAuth flow
   - [ ] Verify redirect back to settings
   - [ ] Confirm Google account shown as connected

4. **Link GitHub Account**
   - [ ] Click "Connect GitHub" or "Link GitHub"
   - [ ] Complete GitHub OAuth flow
   - [ ] Verify GitHub shown as connected

5. **Test Login with Linked Account**
   - [ ] Logout
   - [ ] Login with Google OAuth
   - [ ] Verify it logs into the same account (not creating new user)

**Expected Result**: ✅ OAuth providers successfully linked to existing account

**Error Check**:
- [ ] Verify cannot link an OAuth account already used by another user

---

### Scenario 5: Account Unlinking

**Objective**: Verify users can unlink OAuth accounts (with safeguards).

**Prerequisites**: 
- User has multiple authentication methods (password + OAuth)
- User is logged in

**Steps**:

1. **Navigate to Settings**
   ```
   URL: https://assemblematic.ai/settings/account
   ```

2. **Unlink OAuth Account**
   - [ ] Locate connected OAuth account (Google or GitHub)
   - [ ] Click "Disconnect" or "Unlink"
   - [ ] Confirm action in modal/dialog
   - [ ] Verify account removed from connected accounts list

3. **Verify Cannot Unlink Last Auth Method**
   - [ ] If only one auth method remains, attempt to unlink it
   - [ ] Should show error: "Cannot unlink last authentication method"
   - [ ] User should be prevented from removing last login method

**Expected Result**: ✅ Can unlink OAuth when other methods exist; prevented when it's the last method

---

### Scenario 6: OAuth Error Handling

**Objective**: Verify graceful error handling for OAuth failures.

#### Test 6a: User Denies Authorization

**Steps**:
1. [ ] Click "Sign in with Google"
2. [ ] On Google authorization page, click "Cancel" or "Deny"
3. [ ] Verify redirect to login page with error message
4. [ ] Error message should be user-friendly

**Expected Result**: ✅ User-friendly error displayed, not logged in

#### Test 6b: Invalid Configuration (Staging/Dev Only)

**Steps**:
1. [ ] Temporarily misconfigure `OAUTH_REDIRECT_BASE` (dev/staging only)
2. [ ] Attempt OAuth login
3. [ ] Verify error is caught and logged
4. [ ] Restore correct configuration

**Expected Result**: ✅ Error logged, graceful failure

#### Test 6c: Duplicate Email from Different Provider

**Steps**:
1. [ ] Create account with Google using email `test@example.com`
2. [ ] Logout
3. [ ] Attempt to register with GitHub using same email `test@example.com`
4. [ ] Verify behavior: Should link to existing account OR show appropriate message

**Expected Result**: ✅ Handles duplicate email appropriately

---

### Scenario 7: Redirect URI Validation

**Objective**: Verify redirect URIs are correctly configured.

**Steps**:

1. **Inspect OAuth Initiation**
   ```bash
   # Get the authorization URL
   curl -s https://assemblematic.ai/api/v1/auth/oauth/google/login | jq -r '.authorization_url'
   ```

2. **Verify Redirect URI Parameter**
   - [ ] Check `redirect_uri` parameter in URL
   - [ ] Should exactly match: `https://assemblematic.ai/api/v1/auth/oauth/google/callback`
   - [ ] No trailing slashes
   - [ ] HTTPS (not HTTP)
   - [ ] Correct domain

3. **Repeat for GitHub**
   ```bash
   curl -s https://assemblematic.ai/api/v1/auth/oauth/github/login | jq -r '.authorization_url'
   ```

4. **Cross-Reference with Provider Settings**
   - [ ] Login to Google Cloud Console
   - [ ] Verify redirect URI is registered exactly as used
   - [ ] Repeat for GitHub

**Expected Result**: ✅ Redirect URIs match exactly between code and provider settings

---

### Scenario 8: Token Refresh and Session Persistence

**Objective**: Verify OAuth tokens are properly managed and refreshed.

**Steps**:

1. **Login with OAuth**
   - [ ] Sign in using Google or GitHub OAuth

2. **Wait for Access Token Expiry**
   - [ ] Wait 15-20 minutes (access token expires in 15 min by default)
   - [ ] Perform an authenticated action (e.g., view profile)

3. **Verify Automatic Token Refresh**
   - [ ] Action should succeed (not require re-login)
   - [ ] Check logs for token refresh event

4. **Verify Long-Term Session**
   - [ ] Close browser completely
   - [ ] Reopen and navigate to application
   - [ ] Should still be logged in (refresh token valid for 7 days)

**Expected Result**: ✅ Tokens automatically refreshed, session persists

---

## Performance Testing

### Load Test OAuth Endpoints

**Objective**: Verify OAuth endpoints can handle production load.

**Tool**: Apache Bench or similar

```bash
# Test OAuth login endpoint
ab -n 100 -c 10 https://assemblematic.ai/api/v1/auth/oauth/google/login

# Expected: 
# - No errors
# - Average response time < 500ms
# - No rate limiting false positives
```

**Metrics to Monitor**:
- Response time (p50, p95, p99)
- Error rate
- Database connection pool usage
- Memory usage

---

## Security Validation

### Security Checklist

- [ ] **HTTPS Only**: All OAuth redirects use HTTPS
- [ ] **State Parameter**: CSRF token properly generated and validated
- [ ] **Secure Cookies**: Session cookies have Secure and HttpOnly flags
- [ ] **No Token Exposure**: Access tokens not logged or exposed in URLs
- [ ] **Rate Limiting**: OAuth endpoints have rate limiting enabled
- [ ] **Token Encryption**: Tokens encrypted at rest in database

### Manual Security Tests

1. **Test State Parameter Tampering**
   ```bash
   # Attempt callback with invalid state
   curl "https://assemblematic.ai/api/v1/auth/oauth/google/callback?code=test&state=invalid"
   # Should fail with error
   ```

2. **Test Callback Without Code**
   ```bash
   curl "https://assemblematic.ai/api/v1/auth/oauth/google/callback"
   # Should return error (422 or 400)
   ```

3. **Verify Tokens Not in Logs**
   ```bash
   kubectl logs -n ai-part-designer-prod deployment/backend | grep -i "access_token"
   # Should not find access tokens in logs
   ```

---

## Monitoring and Alerts

### Key Metrics to Monitor

Set up monitoring for:

1. **OAuth Success Rate**
   ```
   Metric: oauth_auth_success_rate
   Alert: < 95%
   ```

2. **OAuth Latency**
   ```
   Metric: oauth_auth_duration_seconds
   Alert: p95 > 3s
   ```

3. **Failed OAuth Attempts**
   ```
   Metric: oauth_auth_failures_total
   Alert: Rate > 10/min
   ```

4. **Database Connection Errors**
   ```
   Metric: db_connection_errors during oauth flow
   Alert: Any occurrence
   ```

### Log Queries

```bash
# Successful OAuth logins (last hour)
kubectl logs -n ai-part-designer-prod deployment/backend --since=1h | \
  grep "oauth.*success" | wc -l

# OAuth errors (last hour)
kubectl logs -n ai-part-designer-prod deployment/backend --since=1h | \
  grep "oauth.*error"

# OAuth provider distribution
kubectl logs -n ai-part-designer-prod deployment/backend --since=24h | \
  grep "oauth_provider" | awk '{print $NF}' | sort | uniq -c
```

---

## Troubleshooting Guide

### Issue: "Redirect URI Mismatch"

**Symptoms**: User sees error from Google/GitHub about redirect URI

**Diagnosis**:
```bash
# Check configured redirect base
kubectl get deployment backend -n ai-part-designer-prod -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="OAUTH_REDIRECT_BASE")].value}'

# Should output: https://assemblematic.ai
```

**Resolution**:
1. Verify `OAUTH_REDIRECT_BASE` environment variable
2. Check provider settings match exactly
3. Update and redeploy if needed

### Issue: OAuth Buttons Not Visible

**Symptoms**: OAuth buttons missing on login page

**Diagnosis**:
```bash
# Check if OAuth providers are configured
curl -s https://assemblematic.ai/api/v1/auth/oauth/google/login
# Should return authorization URL or 503 if not configured
```

**Resolution**:
1. Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
2. Check backend logs for configuration warnings
3. Restart backend if credentials were just added

### Issue: "Account Already Exists"

**Symptoms**: Cannot sign up with OAuth using existing email

**Expected Behavior**: Should link to existing account if email matches

**Diagnosis**:
1. Check if user exists with that email
2. Verify OAuth linking logic is working

**Resolution**: This may be expected behavior for security; user should login with existing method first, then link OAuth.

---

## Post-Test Actions

After completing tests:

1. **Document Results**
   - [ ] Record test date and time
   - [ ] Note any failures or issues
   - [ ] Update this runbook if procedures changed

2. **Clean Up Test Data**
   - [ ] Remove test user accounts if needed
   - [ ] Clean up OAuth connections from tests

3. **Update Monitoring**
   - [ ] Ensure alerts are configured for all scenarios
   - [ ] Verify dashboards show OAuth metrics

4. **Communicate Results**
   - [ ] Inform team of test results
   - [ ] Document any action items

---

## Test Frequency

- **Before Production Deployment**: Full test suite
- **Weekly**: Scenario 1, 2, 3 (basic smoke tests)
- **Monthly**: Full test suite
- **After Configuration Changes**: Full test suite
- **After Provider Changes**: Relevant provider tests

---

## Appendix: Quick Reference

### OAuth Endpoints

```
Google Login:    GET /api/v1/auth/oauth/google/login
Google Callback: GET /api/v1/auth/oauth/google/callback

GitHub Login:    GET /api/v1/auth/oauth/github/login  
GitHub Callback: GET /api/v1/auth/oauth/github/callback

Connections:     GET /api/v1/auth/oauth/connections (authenticated)
Unlink:          DELETE /api/v1/auth/oauth/connections/{provider} (authenticated)
```

### Expected HTTP Status Codes

| Endpoint | Success | Error |
|----------|---------|-------|
| /oauth/{provider}/login | 200 | 503 (not configured) |
| /oauth/{provider}/callback | 307 (redirect) | 400, 401, 500 |
| /oauth/connections | 200 | 401 (not authenticated) |
| /oauth/connections/{provider} DELETE | 200 | 400, 404 |

### Environment Variables

```bash
OAUTH_REDIRECT_BASE=https://assemblematic.ai
FRONTEND_URL=https://assemblematic.ai
GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
GITHUB_CLIENT_ID=Iv1.xxxxxxxx
GITHUB_CLIENT_SECRET=xxxxxxxxxx
```

---

## Contact

For issues or questions about OAuth configuration:
- **Backend Team**: [your-team-contact]
- **DevOps/Platform**: [devops-contact]
- **Security Team**: [security-contact]

Last Updated: 2026-02-07
Version: 1.0
