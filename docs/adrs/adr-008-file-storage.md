# ADR-008: File Storage Solution

## Status
Proposed

## Context
We need a file storage solution for:
- User-uploaded STEP/STL files (up to 100MB)
- Generated design files (multiple formats)
- Design thumbnails and previews
- Version history files
- Temporary processing files

Requirements:
- Scalable to millions of files
- High durability (no data loss)
- Fast read access for previews
- Cost-effective for large files
- CDN integration for global access
- Signed URLs for secure access

## Decision
We will use **AWS S3** as our primary file storage solution.

Supporting technology choices:
- **Storage**: AWS S3 Standard (active files), S3 Intelligent-Tiering (older files)
- **CDN**: CloudFront for global distribution
- **Access Control**: Pre-signed URLs with expiration
- **Processing**: S3 event triggers for post-upload processing
- **Client Library**: boto3 with aioboto3 for async

## Consequences

### Positive
- **Durability**: 99.999999999% (11 nines) durability
- **Scalability**: Unlimited storage capacity
- **Performance**: High throughput, low latency with CloudFront
- **Cost tiers**: Automatic tiering for cost optimization
- **Ecosystem**: Rich integration with AWS services
- **Signed URLs**: Secure, temporary access without exposing credentials

### Negative
- **Vendor lock-in**: Tied to AWS (mitigated by S3-compatible abstraction)
- **Egress costs**: Data transfer costs can add up
- **Complexity**: IAM policies can be complex

### Neutral
- Need to implement S3-compatible interface for portability
- Consider multi-region replication for DR

## Options Considered

| Option | Pros | Cons | Score |
|--------|------|------|-------|
| **AWS S3** | Durability, scale, ecosystem | Vendor lock, egress costs | ⭐⭐⭐⭐⭐ |
| Google Cloud Storage | Good integration, competitive pricing | Smaller ecosystem | ⭐⭐⭐⭐ |
| Azure Blob Storage | Good for Azure shops | Less S3-compatible | ⭐⭐⭐ |
| MinIO | Self-hosted, S3-compatible | Operational overhead | ⭐⭐⭐ |
| Cloudflare R2 | No egress fees | Newer, less features | ⭐⭐⭐⭐ |

## Technical Details

### Bucket Structure
```
ai-part-designer-storage/
├── users/
│   └── {user_id}/
│       ├── designs/
│       │   └── {design_id}/
│       │       ├── original.step
│       │       ├── v1.step
│       │       ├── v2.step
│       │       └── thumbnail.webp
│       └── uploads/
│           └── {upload_id}.step
├── templates/
│   └── {template_name}/
│       ├── preview.webp
│       └── thumbnail.webp
├── temp/
│   └── {job_id}/
│       └── processing files...
└── exports/
    └── {export_id}.zip
```

### Storage Service
```python
# app/services/storage/s3.py
import aioboto3
from botocore.config import Config
from datetime import timedelta

class S3StorageService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.bucket = settings.S3_BUCKET
        self.config = Config(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )
    
    async def upload_file(
        self,
        file_data: bytes,
        key: str,
        content_type: str = "application/octet-stream",
        metadata: dict = None
    ) -> str:
        """Upload file to S3."""
        async with self.session.client('s3', config=self.config) as s3:
            await s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_data,
                ContentType=content_type,
                Metadata=metadata or {}
            )
        return f"s3://{self.bucket}/{key}"
    
    async def upload_from_path(
        self,
        local_path: str,
        key: str,
        content_type: str = None
    ) -> str:
        """Upload file from local path."""
        async with self.session.client('s3', config=self.config) as s3:
            with open(local_path, 'rb') as f:
                await s3.upload_fileobj(
                    f, 
                    self.bucket, 
                    key,
                    ExtraArgs={'ContentType': content_type} if content_type else None
                )
        return f"s3://{self.bucket}/{key}"
    
    async def download_file(self, key: str) -> bytes:
        """Download file from S3."""
        async with self.session.client('s3', config=self.config) as s3:
            response = await s3.get_object(Bucket=self.bucket, Key=key)
            return await response['Body'].read()
    
    async def generate_presigned_url(
        self,
        key: str,
        expires_in: timedelta = timedelta(hours=1),
        method: str = "get_object"
    ) -> str:
        """Generate pre-signed URL for secure access."""
        async with self.session.client('s3', config=self.config) as s3:
            url = await s3.generate_presigned_url(
                method,
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=int(expires_in.total_seconds())
            )
        return url
    
    async def generate_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: timedelta = timedelta(minutes=15)
    ) -> dict:
        """Generate pre-signed URL for direct upload."""
        async with self.session.client('s3', config=self.config) as s3:
            response = await s3.generate_presigned_post(
                self.bucket,
                key,
                Fields={'Content-Type': content_type},
                Conditions=[
                    {'Content-Type': content_type},
                    ['content-length-range', 1, 100 * 1024 * 1024]  # 100MB max
                ],
                ExpiresIn=int(expires_in.total_seconds())
            )
        return response
    
    async def delete_file(self, key: str) -> None:
        """Delete file from S3."""
        async with self.session.client('s3', config=self.config) as s3:
            await s3.delete_object(Bucket=self.bucket, Key=key)
    
    async def copy_file(self, source_key: str, dest_key: str) -> str:
        """Copy file within S3."""
        async with self.session.client('s3', config=self.config) as s3:
            await s3.copy_object(
                Bucket=self.bucket,
                Key=dest_key,
                CopySource={'Bucket': self.bucket, 'Key': source_key}
            )
        return f"s3://{self.bucket}/{dest_key}"
    
    async def list_versions(self, prefix: str) -> list:
        """List all versions of objects with prefix."""
        async with self.session.client('s3', config=self.config) as s3:
            paginator = s3.get_paginator('list_object_versions')
            versions = []
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                versions.extend(page.get('Versions', []))
            return versions
```

### File Path Helpers
```python
# app/services/storage/paths.py

def get_design_path(user_id: str, design_id: str, filename: str) -> str:
    """Get S3 key for design file."""
    return f"users/{user_id}/designs/{design_id}/{filename}"

def get_upload_path(user_id: str, upload_id: str, extension: str) -> str:
    """Get S3 key for uploaded file."""
    return f"users/{user_id}/uploads/{upload_id}.{extension}"

def get_temp_path(job_id: str, filename: str) -> str:
    """Get S3 key for temporary processing file."""
    return f"temp/{job_id}/{filename}"

def get_thumbnail_path(user_id: str, design_id: str) -> str:
    """Get S3 key for design thumbnail."""
    return f"users/{user_id}/designs/{design_id}/thumbnail.webp"
```

### Direct Upload Flow
```python
# app/api/v1/uploads.py
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/uploads/presign")
async def get_upload_url(
    request: UploadRequest,
    current_user: User = Depends(get_current_user),
    storage: S3StorageService = Depends(get_storage)
):
    """Get pre-signed URL for direct S3 upload."""
    # Validate file type and size
    if request.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "Invalid file type")
    
    if request.file_size > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max: {MAX_FILE_SIZE}")
    
    # Generate upload ID and key
    upload_id = str(uuid.uuid4())
    extension = get_extension(request.filename)
    key = get_upload_path(current_user.id, upload_id, extension)
    
    # Create upload record
    upload = await create_upload_record(current_user.id, upload_id, request)
    
    # Generate pre-signed URL
    presigned = await storage.generate_upload_url(
        key,
        request.content_type,
        expires_in=timedelta(minutes=15)
    )
    
    return {
        "upload_id": upload_id,
        "url": presigned["url"],
        "fields": presigned["fields"]
    }

@router.post("/uploads/{upload_id}/complete")
async def complete_upload(
    upload_id: str,
    current_user: User = Depends(get_current_user),
):
    """Mark upload as complete and trigger processing."""
    upload = await get_upload(upload_id, current_user.id)
    
    # Trigger processing job
    process_upload.delay(upload_id)
    
    return {"status": "processing", "upload_id": upload_id}
```

### CloudFront Configuration
```python
# CDN URL generation
CLOUDFRONT_DOMAIN = "cdn.aipartdesigner.com"
CLOUDFRONT_KEY_PAIR_ID = "APKA..."

def get_cdn_url(s3_key: str, expires_in: timedelta = timedelta(hours=1)) -> str:
    """Generate CloudFront signed URL."""
    from botocore.signers import CloudFrontSigner
    
    url = f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"
    expire_date = datetime.utcnow() + expires_in
    
    signer = CloudFrontSigner(CLOUDFRONT_KEY_PAIR_ID, rsa_signer)
    signed_url = signer.generate_presigned_url(url, date_less_than=expire_date)
    
    return signed_url
```

### Lifecycle Policies
```yaml
# S3 Lifecycle Configuration
Rules:
  - ID: TempFileCleanup
    Prefix: temp/
    Status: Enabled
    Expiration:
      Days: 1
  
  - ID: ExportCleanup  
    Prefix: exports/
    Status: Enabled
    Expiration:
      Days: 7
  
  - ID: IntelligentTiering
    Prefix: users/
    Status: Enabled
    Transitions:
      - Days: 30
        StorageClass: INTELLIGENT_TIERING
```

### Cost Estimation
| Storage Class | Size | Monthly Cost |
|---------------|------|--------------|
| S3 Standard | 1 TB | ~$23 |
| S3 Intelligent-Tiering | 1 TB | ~$23 + small monitoring fee |
| CloudFront (100GB transfer) | - | ~$8.50 |
| PUT/GET requests | 1M | ~$5 |

## References
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [aioboto3](https://aioboto3.readthedocs.io/)
- [S3 Security Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
