# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records for the AI Part Designer project.

## What are ADRs?

Architecture Decision Records capture important architectural decisions along with their context and consequences. They provide a historical record of why the system was built the way it was.

## ADR Index

| ADR | Title | Status | Summary |
|-----|-------|--------|---------|
| [ADR-000](adr-000-template.md) | ADR Template | Accepted | Standard template for new ADRs |
| [ADR-001](adr-001-frontend-framework.md) | Frontend Framework | Proposed | React 18 + TypeScript + Vite |
| [ADR-002](adr-002-backend-framework.md) | Backend Framework | Proposed | Python + FastAPI |
| [ADR-003](adr-003-database-technology.md) | Database Technology | Proposed | PostgreSQL 15+ |
| [ADR-004](adr-004-queue-system.md) | Queue System | Proposed | Celery + Redis |
| [ADR-005](adr-005-cad-processing-library.md) | CAD Processing | Proposed | CadQuery + OpenCASCADE |
| [ADR-006](adr-006-ai-ml-integration.md) | AI/ML Integration | Proposed | OpenAI GPT-4 + LangChain |
| [ADR-007](adr-007-authentication-strategy.md) | Authentication | Proposed | Custom JWT |
| [ADR-008](adr-008-file-storage.md) | File Storage | Proposed | AWS S3 + CloudFront |
| [ADR-009](adr-009-deployment-platform.md) | Deployment Platform | Proposed | AWS ECS Fargate |
| [ADR-010](adr-010-api-versioning.md) | API Versioning | Proposed | URL Path Versioning |
| [ADR-011](adr-011-monitoring-observability.md) | Monitoring | Proposed | OpenTelemetry + Prometheus + Grafana |
| [ADR-012](adr-012-content-moderation.md) | Content Moderation | Proposed | Multi-layer ML + Human Review |
| [ADR-013](adr-013-cloud-agnostic-architecture.md) | Cloud-Agnostic Architecture | Accepted | Kubernetes + abstraction layers |

## Technology Stack Summary

Based on the proposed ADRs, our technology stack is:

### Frontend
- **Framework**: React 18 with TypeScript
- **Build**: Vite
- **State**: Zustand
- **3D Visualization**: Three.js + React Three Fiber
- **UI Components**: shadcn/ui + Tailwind CSS

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.0 (async)
- **Validation**: Pydantic v2

### Data
- **Database**: PostgreSQL 15+ (RDS/Cloud SQL/Azure DB/self-hosted)
- **Cache/Queue**: Redis (managed or self-hosted)
- **File Storage**: S3/GCS/Azure Blob/MinIO (via abstraction layer)

### AI/ML
- **LLM**: OpenAI GPT-4 (via LangChain)
- **CAD Engine**: CadQuery + OpenCASCADE

### Infrastructure (Cloud-Agnostic per ADR-013)
- **Orchestration**: Kubernetes (EKS/GKE/AKS/k3s)
- **CDN**: CloudFront/Cloud CDN/Azure CDN/Cloudflare
- **Secrets**: AWS Secrets Manager/GCP Secret Manager/Vault
- **IaC**: Terraform with provider abstraction

### Observability (Cloud-Agnostic per ADR-013)
- **Collection**: OpenTelemetry (vendor-neutral)
- **Metrics**: Prometheus
- **Dashboards**: Grafana
- **Tracing**: Jaeger or Tempo
- **Logging**: Loki or ELK
- **Errors**: Sentry (SaaS or self-hosted)

## ADR Lifecycle

1. **Proposed**: Initial draft, open for discussion
2. **Accepted**: Approved and ready for implementation
3. **Deprecated**: No longer relevant, kept for history
4. **Superseded**: Replaced by a newer ADR

## Creating a New ADR

1. Copy `adr-000-template.md` to `adr-XXX-title.md`
2. Fill in all sections
3. Set status to "Proposed"
4. Submit for review
5. Update status to "Accepted" after approval
6. Update this index

## Review Process

- All ADRs require review before acceptance
- Technical leads approve architecture decisions
- Team discussion encouraged for significant changes
- Consider impact on existing decisions
