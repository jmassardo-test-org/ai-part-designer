# ADR-013: Cloud-Agnostic Architecture

**Status:** Accepted  
**Date:** 2026-01-24  
**Deciders:** Architecture Team  
**Supersedes:** Partial aspects of ADR-008, ADR-009, ADR-011  

## Context

The initial architecture decisions (ADR-008, ADR-009, ADR-011) specified AWS-specific services:
- AWS S3 for file storage
- AWS ECS Fargate for container orchestration
- AWS CloudFront for CDN
- AWS X-Ray for tracing

This creates vendor lock-in and limits deployment options for:
- Customers requiring specific cloud providers (compliance, existing contracts)
- Self-hosted/on-premise deployments
- Multi-cloud disaster recovery strategies
- Cost optimization through cloud arbitrage

## Decision

We will adopt a **cloud-agnostic architecture** using abstraction layers and portable technologies:

### 1. Container Orchestration
**Use Kubernetes (K8s) instead of ECS Fargate**

| Aspect | Approach |
|--------|----------|
| Orchestrator | Kubernetes (managed or self-hosted) |
| AWS | Amazon EKS |
| GCP | Google GKE |
| Azure | Azure AKS |
| Self-hosted | k3s, Rancher, vanilla K8s |
| Helm Charts | Standardized deployment across clouds |

### 2. Object Storage
**Abstract behind unified interface**

```python
# storage/interface.py
from abc import ABC, abstractmethod

class ObjectStorage(ABC):
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str) -> str: ...
    
    @abstractmethod
    async def download(self, key: str) -> bytes: ...
    
    @abstractmethod
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str: ...
    
    @abstractmethod
    async def delete(self, key: str) -> None: ...

# Implementations
class S3Storage(ObjectStorage): ...      # AWS S3
class GCSStorage(ObjectStorage): ...     # Google Cloud Storage
class AzureBlobStorage(ObjectStorage): ... # Azure Blob
class MinIOStorage(ObjectStorage): ...   # Self-hosted (S3-compatible)
```

| Provider | Service | Notes |
|----------|---------|-------|
| AWS | S3 | Native SDK |
| GCP | Cloud Storage | S3-compatible API available |
| Azure | Blob Storage | Native SDK |
| Self-hosted | MinIO | S3-compatible, production-ready |

### 3. Database
**PostgreSQL remains cloud-agnostic** ✅

| Provider | Service |
|----------|---------|
| AWS | RDS PostgreSQL / Aurora |
| GCP | Cloud SQL PostgreSQL |
| Azure | Azure Database for PostgreSQL |
| Self-hosted | PostgreSQL on VMs or K8s |

### 4. Cache/Queue
**Redis remains cloud-agnostic** ✅

| Provider | Service |
|----------|---------|
| AWS | ElastiCache Redis |
| GCP | Memorystore Redis |
| Azure | Azure Cache for Redis |
| Self-hosted | Redis on VMs or K8s |

### 5. CDN
**Use cloud-native CDN with abstracted origin configuration**

| Provider | Service |
|----------|---------|
| AWS | CloudFront |
| GCP | Cloud CDN |
| Azure | Azure CDN |
| Multi-cloud | Cloudflare, Fastly |

CDN configuration managed via Terraform modules with provider-specific implementations.

### 6. Secrets Management
**Abstract secrets access**

```python
# secrets/interface.py
class SecretsManager(ABC):
    @abstractmethod
    async def get_secret(self, name: str) -> str: ...

# Implementations
class AWSSecretsManager(SecretsManager): ...
class GCPSecretManager(SecretsManager): ...
class AzureKeyVault(SecretsManager): ...
class HashiCorpVault(SecretsManager): ...  # Multi-cloud / self-hosted
class EnvVarSecrets(SecretsManager): ...   # Development / simple deployments
```

### 7. Monitoring & Observability
**Use open standards and portable tools**

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Metrics | Prometheus + Grafana | Open-source, runs anywhere |
| Logging | OpenTelemetry → Loki/ELK | Vendor-neutral collection |
| Tracing | OpenTelemetry → Jaeger/Tempo | Open standard, not X-Ray |
| Error Tracking | Sentry | SaaS or self-hosted |
| APM | OpenTelemetry exporters | Export to any backend |

### 8. Infrastructure as Code
**Terraform with provider abstraction**

```
infrastructure/
├── modules/                    # Reusable, provider-agnostic where possible
│   ├── kubernetes/            # K8s resources (provider-agnostic)
│   ├── database/              # PostgreSQL (provider-specific implementations)
│   ├── cache/                 # Redis (provider-specific implementations)
│   ├── storage/               # Object storage (provider-specific)
│   └── monitoring/            # Prometheus/Grafana stack
├── providers/
│   ├── aws/                   # AWS-specific provider config
│   ├── gcp/                   # GCP-specific provider config
│   ├── azure/                 # Azure-specific provider config
│   └── self-hosted/           # Bare metal / VM provider config
└── environments/
    ├── production-aws/
    ├── production-gcp/
    ├── staging/
    └── development/
```

### 9. Container Registry
**Support multiple registries**

| Provider | Registry |
|----------|----------|
| AWS | ECR |
| GCP | Artifact Registry |
| Azure | ACR |
| Multi-cloud | Docker Hub, GitHub Container Registry |
| Self-hosted | Harbor |

## Configuration Strategy

Use environment-based configuration to select providers:

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Cloud provider selection
    CLOUD_PROVIDER: str = "aws"  # aws | gcp | azure | self-hosted
    
    # Storage
    STORAGE_BACKEND: str = "s3"  # s3 | gcs | azure | minio
    STORAGE_BUCKET: str
    STORAGE_ENDPOINT: str | None = None  # For MinIO/self-hosted
    
    # Secrets
    SECRETS_BACKEND: str = "env"  # aws | gcp | azure | vault | env
    
    # Feature flags for cloud-specific features
    USE_MANAGED_REDIS: bool = True
    USE_MANAGED_POSTGRES: bool = True
```

```python
# storage/factory.py
def get_storage(settings: Settings) -> ObjectStorage:
    match settings.STORAGE_BACKEND:
        case "s3":
            return S3Storage(bucket=settings.STORAGE_BUCKET)
        case "gcs":
            return GCSStorage(bucket=settings.STORAGE_BUCKET)
        case "azure":
            return AzureBlobStorage(container=settings.STORAGE_BUCKET)
        case "minio":
            return MinIOStorage(
                bucket=settings.STORAGE_BUCKET,
                endpoint=settings.STORAGE_ENDPOINT,
            )
        case _:
            raise ValueError(f"Unknown storage backend: {settings.STORAGE_BACKEND}")
```

## Deployment Matrix

| Component | AWS | GCP | Azure | Self-Hosted |
|-----------|-----|-----|-------|-------------|
| Orchestration | EKS | GKE | AKS | k3s/Rancher |
| Database | RDS | Cloud SQL | Azure DB | PostgreSQL |
| Cache | ElastiCache | Memorystore | Azure Cache | Redis |
| Storage | S3 | GCS | Blob | MinIO |
| CDN | CloudFront | Cloud CDN | Azure CDN | Cloudflare |
| Secrets | Secrets Manager | Secret Manager | Key Vault | Vault |
| Registry | ECR | Artifact Registry | ACR | Harbor |
| Monitoring | Managed Prometheus | Managed Prometheus | Monitor | Self-hosted |

## Consequences

### Positive
- **Flexibility**: Deploy to any major cloud or on-premise
- **Negotiating power**: Not locked to single vendor pricing
- **Disaster recovery**: Multi-cloud failover possible
- **Enterprise sales**: Meet customer cloud requirements
- **Cost optimization**: Choose best price/performance per service

### Negative
- **Increased complexity**: Abstraction layers add code
- **Testing burden**: Must test on multiple providers
- **Feature limitations**: Can't use cloud-specific optimizations easily
- **Initial velocity**: Slower than single-cloud approach
- **Expertise required**: Team must know multiple clouds

### Mitigations
- Start with AWS primary, validate GCP/Azure quarterly
- Use MinIO for local development (S3-compatible)
- Kubernetes abstracts most orchestration differences
- OpenTelemetry provides unified observability
- Terraform modules encapsulate provider differences

## Implementation Priority

1. **Phase 1 (MVP)**: AWS primary with abstraction interfaces
2. **Phase 2**: Add MinIO support for self-hosted development
3. **Phase 3**: GCP support for first enterprise customer
4. **Phase 4**: Azure support based on demand

## Related ADRs

- ADR-008: File Storage → Updated to use abstraction layer
- ADR-009: Deployment → Updated to Kubernetes
- ADR-011: Monitoring → Updated to OpenTelemetry

---

*End of ADR*
