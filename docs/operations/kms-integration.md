# Cloud KMS Integration Guide

## Overview

AI Part Designer supports integration with cloud-based Key Management Services (KMS) for enhanced security of encryption keys. Instead of storing encryption keys in environment variables, production deployments can use AWS KMS or GCP Cloud KMS to manage master encryption keys.

## Architecture

The platform uses **envelope encryption** for secure data protection:

```
┌─────────────────────────────────────────────────────────────┐
│                    Envelope Encryption Flow                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Generate Data Encryption Key (DEK)                       │
│     ├── Random 256-bit key                                   │
│     └── Used to encrypt actual data                          │
│                                                               │
│  2. Encrypt data with DEK                                    │
│     └── Fast symmetric encryption (AES-256)                  │
│                                                               │
│  3. Encrypt DEK with KMS Master Key                          │
│     ├── Master key never leaves KMS                          │
│     └── Returns encrypted DEK                                │
│                                                               │
│  4. Store encrypted data + encrypted DEK                     │
│     ├── Data encrypted with DEK                              │
│     └── DEK encrypted with KMS master key                    │
│                                                               │
│  5. On decrypt: KMS decrypts DEK, use DEK to decrypt data   │
│     └── Decrypted DEKs are cached (1 hour TTL)              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Local Development (Default)

For development and testing, use the local KMS provider:

```bash
# .env
KMS_PROVIDER=local
SECRET_KEY=your-secret-key-for-dev
```

The local provider uses PBKDF2 key derivation from `SECRET_KEY`. **Do not use in production.**

### AWS KMS Setup

#### 1. Create KMS Key

```bash
# Create a symmetric encryption key
aws kms create-key \
  --description "AI Part Designer master encryption key" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS \
  --region us-west-2

# Create an alias for easier reference
aws kms create-alias \
  --alias-name alias/ai-part-designer-prod \
  --target-key-id <key-id-from-above>
```

#### 2. Configure IAM Permissions

The application service account needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowEncryptDecrypt",
      "Effect": "Allow",
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey",
        "kms:DescribeKey"
      ],
      "Resource": "arn:aws:kms:us-west-2:123456789012:key/*"
    }
  ]
}
```

**Note:** Use least-privilege access. Consider separate keys for different environments.

#### 3. Configure Application

```bash
# .env for production
KMS_PROVIDER=aws
AWS_KMS_KEY_ID=arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012
AWS_KMS_REGION=us-west-2

# Or use alias
AWS_KMS_KEY_ID=alias/ai-part-designer-prod

# Optional: DEK caching (defaults shown)
KMS_DEK_CACHE_TTL_SECONDS=3600
KMS_DEK_CACHE_MAX_SIZE=100
```

#### 4. Verify Setup

```bash
# Test encryption/decryption
python -c "
from app.core.security import kms_encryption_service
encrypted = kms_encryption_service.encrypt('test')
decrypted = kms_encryption_service.decrypt(encrypted)
assert decrypted == 'test'
print('✅ AWS KMS integration working')
"
```

### GCP Cloud KMS Setup

#### 1. Create KMS Resources

```bash
# Set project
gcloud config set project ai-part-designer-prod

# Create key ring
gcloud kms keyrings create ai-part-designer \
  --location us-east1

# Create crypto key
gcloud kms keys create master-encryption-key \
  --location us-east1 \
  --keyring ai-part-designer \
  --purpose encryption
```

#### 2. Configure IAM Permissions

Grant the service account permissions:

```bash
# Get service account
SERVICE_ACCOUNT=ai-part-designer@ai-part-designer-prod.iam.gserviceaccount.com

# Grant encrypt/decrypt permissions
gcloud kms keys add-iam-policy-binding master-encryption-key \
  --location us-east1 \
  --keyring ai-part-designer \
  --member serviceAccount:$SERVICE_ACCOUNT \
  --role roles/cloudkms.cryptoKeyEncrypterDecrypter
```

Required roles:
- `roles/cloudkms.cryptoKeyEncrypterDecrypter` - Encrypt and decrypt

#### 3. Configure Application

```bash
# .env for production
KMS_PROVIDER=gcp
GCP_KMS_PROJECT_ID=ai-part-designer-prod
GCP_KMS_LOCATION=us-east1
GCP_KMS_KEY_RING=ai-part-designer
GCP_KMS_KEY_NAME=master-encryption-key

# Optional: DEK caching (defaults shown)
KMS_DEK_CACHE_TTL_SECONDS=3600
KMS_DEK_CACHE_MAX_SIZE=100
```

#### 4. Authentication

Ensure Application Default Credentials are configured:

```bash
# For local development
gcloud auth application-default login

# In production (GKE)
# Service account credentials are automatically available
```

#### 5. Verify Setup

```bash
# Test encryption/decryption
python -c "
from app.core.security import kms_encryption_service
encrypted = kms_encryption_service.encrypt('test')
decrypted = kms_encryption_service.decrypt(encrypted)
assert decrypted == 'test'
print('✅ GCP Cloud KMS integration working')
"
```

## Usage

### Encrypting Data

```python
from app.core.security import kms_encryption_service

# Encrypt string
encrypted = kms_encryption_service.encrypt("sensitive data")
# Returns: {
#   "ciphertext": "base64_encrypted_data",
#   "encrypted_dek": {
#     "ciphertext": "base64_encrypted_key",
#     "key_id": "arn:aws:kms:...",
#     "algorithm": "AWS_KMS"
#   }
# }

# Encrypt dictionary
encrypted = kms_encryption_service.encrypt_dict({
    "api_key": "sk-...",
    "secret": "..."
})

# Encrypt bytes
encrypted = kms_encryption_service.encrypt_bytes(b"binary data")
```

### Decrypting Data

```python
from app.core.security import kms_encryption_service

# Decrypt string
plaintext = kms_encryption_service.decrypt(encrypted)

# Decrypt dictionary
data = kms_encryption_service.decrypt_dict(encrypted)

# Decrypt bytes
binary = kms_encryption_service.decrypt_bytes(encrypted)
```

### Storage Format

Store the entire encrypted structure in your database as JSON:

```python
import json
from sqlalchemy import Column, Text
from app.models import Base

class SensitiveData(Base):
    __tablename__ = "sensitive_data"
    
    # Store encrypted data as JSON
    encrypted_content = Column(Text, nullable=False)
    
    @property
    def content(self):
        """Decrypt on access."""
        from app.core.security import kms_encryption_service
        encrypted = json.loads(self.encrypted_content)
        return kms_encryption_service.decrypt(encrypted)
    
    @content.setter
    def content(self, value):
        """Encrypt on set."""
        from app.core.security import kms_encryption_service
        encrypted = kms_encryption_service.encrypt(value)
        self.encrypted_content = json.dumps(encrypted)
```

## Performance Optimization

### DEK Caching

Decrypted Data Encryption Keys (DEKs) are cached in memory to reduce KMS API calls:

- **Default TTL:** 1 hour (3600 seconds)
- **Default Max Size:** 100 DEKs
- **Cache Key:** SHA-256 hash of encrypted DEK

Configure caching:

```bash
# .env
KMS_DEK_CACHE_TTL_SECONDS=3600  # 1 hour
KMS_DEK_CACHE_MAX_SIZE=100
```

**Note:** Longer TTL = better performance but slower key rotation.

### Cost Optimization

AWS KMS pricing (as of 2024):
- **$1.00** per month per key
- **$0.03** per 10,000 requests

With DEK caching:
- **Without cache:** 10,000 decrypts = $0.03
- **With cache (1hr TTL):** ~100 KMS calls = $0.0003

**Recommendation:** Use default 1-hour cache TTL for production.

## Security Considerations

### Master Key Security

✅ **DO:**
- Use separate KMS keys for dev/staging/prod
- Enable key rotation (AWS: automatic, GCP: manual)
- Use IAM policies with least privilege
- Enable CloudTrail/Cloud Audit Logs
- Set up key usage alarms

❌ **DON'T:**
- Share keys across environments
- Grant wildcard KMS permissions
- Disable audit logging
- Use root/admin credentials

### Key Rotation

#### AWS KMS Automatic Rotation

```bash
# Enable automatic rotation (yearly)
aws kms enable-key-rotation --key-id <key-id>

# Check rotation status
aws kms get-key-rotation-status --key-id <key-id>
```

AWS handles rotation automatically - old key versions remain accessible.

#### GCP Cloud KMS Manual Rotation

```bash
# Create new key version
gcloud kms keys versions create \
  --location us-east1 \
  --keyring ai-part-designer \
  --key master-encryption-key

# Set new version as primary
gcloud kms keys set-primary-version master-encryption-key \
  --location us-east1 \
  --keyring ai-part-designer \
  --version <new-version>
```

**Note:** Data encrypted with old DEKs remains accessible (envelope encryption).

### Audit Logging

#### AWS CloudTrail

Monitor KMS usage:

```bash
# Query CloudTrail logs
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::KMS::Key \
  --max-results 100
```

#### GCP Cloud Audit Logs

Monitor KMS usage:

```bash
# Query audit logs
gcloud logging read "resource.type=cloudkms_cryptokey" \
  --limit 50 \
  --format json
```

## Troubleshooting

### AWS KMS Issues

**Error: "AccessDeniedException"**

```bash
# Check IAM permissions
aws iam simulate-principal-policy \
  --policy-source-arn <role-arn> \
  --action-names kms:Encrypt kms:Decrypt \
  --resource-arns <key-arn>
```

**Error: "KeyUnavailableException"**

Key may be disabled or pending deletion:

```bash
# Check key state
aws kms describe-key --key-id <key-id>
```

### GCP Cloud KMS Issues

**Error: "Permission denied"**

```bash
# Check service account permissions
gcloud kms keys get-iam-policy master-encryption-key \
  --location us-east1 \
  --keyring ai-part-designer
```

**Error: "Key not found"**

```bash
# Verify key exists
gcloud kms keys describe master-encryption-key \
  --location us-east1 \
  --keyring ai-part-designer
```

### General Issues

**High KMS API Costs**

Increase DEK cache TTL:

```bash
KMS_DEK_CACHE_TTL_SECONDS=7200  # 2 hours
```

**Slow Decryption**

Check cache effectiveness:

```python
from app.core.kms import get_dek_cache

cache = get_dek_cache()
# Monitor cache hit rate in application logs
```

## Migration from SECRET_KEY

To migrate existing SECRET_KEY encrypted data to KMS:

1. **Deploy with KMS enabled** but keep SECRET_KEY
2. **Decrypt existing data** with old EncryptionService
3. **Re-encrypt with KMS** using kms_encryption_service
4. **Update database** with new encrypted format
5. **Remove SECRET_KEY** dependency

Example migration script:

```python
from app.core.security import encryption_service, kms_encryption_service
from app.models import EncryptedModel

async def migrate_to_kms(db):
    """Migrate existing encrypted data to KMS."""
    records = await db.execute(select(EncryptedModel))
    
    for record in records.scalars():
        # Decrypt with old method
        plaintext = encryption_service.decrypt(record.encrypted_field)
        
        # Re-encrypt with KMS
        kms_encrypted = kms_encryption_service.encrypt(plaintext)
        record.encrypted_field = json.dumps(kms_encrypted)
    
    await db.commit()
    print(f"Migrated {len(records)} records to KMS encryption")
```

## References

- [AWS KMS Documentation](https://docs.aws.amazon.com/kms/latest/developerguide/overview.html)
- [GCP Cloud KMS Documentation](https://cloud.google.com/kms/docs)
- [Envelope Encryption Best Practices](https://cloud.google.com/kms/docs/envelope-encryption)
- [ADR-015: Security Architecture](../adrs/adr-015-security-architecture.md)

## Support

For KMS-related issues:
- Check application logs for detailed error messages
- Review IAM/permissions for service account
- Verify KMS key state and configuration
- Contact DevOps team for production key issues
