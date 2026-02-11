# Security Notes

This document tracks known security issues and their mitigation status.

## Fixed Issues

### 1. CI/CD Security Checks (FIXED - 2026-02-11)
**Issue**: CI/CD pipeline had `continue-on-error: true` for security checks, allowing vulnerable code to be merged.

**Impact**: High - Security vulnerabilities could bypass CI/CD checks.

**Fix**: Removed `continue-on-error: true` from:
- Bandit security linter step
- pip-audit dependency vulnerability scanner

**Result**: CI/CD now fails on security issues, preventing vulnerable code from being merged.

### 2. MD5 Hash Warnings (FIXED - 2026-02-11)
**Issue**: Bandit reported 3 high-severity warnings for MD5 hash usage.

**Analysis**: All MD5 uses were for non-security purposes:
- Cache key generation (`app/core/cache.py`)
- Rate limiting request IDs (`app/core/redis_rate_limit.py`)
- File checksum calculation (`app/core/storage.py`)

**Fix**: Added `usedforsecurity=False` parameter to all `hashlib.md5()` calls to explicitly indicate non-security usage.

**Result**: High-severity warnings eliminated (0 high-severity issues remaining).

## Known Issues (Not Fixed)

### 1. protobuf CVE-2026-0994
**Issue**: protobuf 4.25.8 has a known vulnerability (CVE-2026-0994).

**Why Not Fixed**: Cannot upgrade to protobuf 5.x due to dependency conflicts:
- `google-cloud-kms>=2.19.0` requires `protobuf<5.0.0`
- `opentelemetry-exporter-jaeger>=1.21.0` requires `protobuf<5.0.0`

**Mitigation**: 
- Vulnerability is ignored in pip-audit with `--ignore-vuln CVE-2026-0994`
- Documented in CI/CD workflow
- Monitor for updated versions of dependencies that support protobuf 5.x

**Action Required**: Update dependencies when compatible versions are available.

### 2. ecdsa CVE-2024-23342
**Issue**: ecdsa 0.19.1 has a known vulnerability (CVE-2024-23342).

**Why Not Fixed**: No fix version available yet.

**Mitigation**: 
- Vulnerability is ignored in pip-audit with `--ignore-vuln CVE-2024-23342`
- Documented in CI/CD workflow
- Monitor for security updates

**Action Required**: Update ecdsa when a fix is released.

### 3. exec() Usage (3 instances - Medium Severity)
**Issue**: Bandit warns about use of `exec()` in:
- `app/ai/codegen.py:407` - Dynamic code generation for CAD
- `app/ai/direct_generation.py:317` - Direct CAD code execution
- `app/enclosure/service.py:422` - Enclosure generation code execution

**Analysis**: These are intentional uses for dynamic code generation in the AI/CAD pipeline.

**Risk**: Medium - Code is executed in controlled namespaces with restricted globals.

**Mitigation**: 
- Code is validated before execution
- Execution happens in isolated namespaces
- Input is from AI models, not directly from users

**Recommendation**: Consider sandboxing or additional validation layers.

### 4. Hardcoded /tmp Directories (4 instances - Medium Severity)
**Issue**: Hardcoded `/tmp` paths in:
- `app/core/backup.py:36`
- `app/core/backup.py:287`
- `app/services/backup.py:139`
- `app/services/backup.py:274`

**Risk**: Low-Medium - Potential for directory traversal or race conditions.

**Mitigation**: Most uses have fallbacks to config values (e.g., `BACKUP_DIR`, `FILE_STORAGE_PATH`).

**Recommendation**: Remove hardcoded defaults and require explicit configuration.

## Security Best Practices

1. **Keep dependencies updated**: Regularly run `pip-audit` and update packages
2. **Monitor CVE databases**: Watch for fixes to ignored vulnerabilities
3. **Code review**: All security-sensitive code requires review
4. **Test security**: Run Bandit and pip-audit before commits
5. **Document exceptions**: Always document why security issues are ignored

## Running Security Checks Locally

```bash
# Backend security checks
cd backend
uv run bandit -r app -ll -ii  # Show medium/high issues
pip-audit -r requirements.txt --ignore-vuln CVE-2026-0994 --ignore-vuln CVE-2024-23342
```

## Last Updated

2026-02-11 - Initial security audit and fixes
