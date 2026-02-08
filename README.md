# AssemblematicAI

**AI-powered 3D part generation for makers, engineers, and educators**

[![Status](https://img.shields.io/badge/status-planning-yellow)]()
[![License](https://img.shields.io/badge/license-TBD-lightgrey)]()

---

## Overview

AssemblematicAI is a web-based SaaS platform that enables users to design and generate 3D printable parts through:
- **Natural language descriptions** - Describe what you need, AI generates the CAD model
- **Pre-built templates** - Start from common part types and customize parameters
- **AI-assisted modifications** - Upload existing STEP/STL files and modify with natural language

### Key Features (Planned)
- 🎯 **Natural Language to CAD** - "Create a box 100mm x 50mm with rounded corners and a lid"
- 📦 **Template Library** - Project boxes, brackets, gears, enclosures, and more
- 🔧 **Parameter Customization** - Real-time 3D preview as you adjust dimensions
- 📤 **Multi-format Export** - STL, STEP, OBJ, 3MF
- ⚡ **Priority Processing** - Faster generation for Pro subscribers
- 🛡️ **Content Moderation** - AI-powered abuse and intent detection

---

## Project Status

**Current Phase:** Planning & Documentation

### Completed
- [x] Business Requirements Document (BRD)
- [x] Functional Requirements Document (FRD)
- [x] Detailed User Stories (31 stories with acceptance criteria)
- [x] Gap Analysis
- [x] Requirements Traceability Matrix
- [x] Architecture Decision Records (12 ADRs)
- [x] Product Roadmap with RICE scoring

### Next Steps
- [ ] Finalize and accept ADRs
- [ ] CAD Library Proof of Concept (CadQuery)
- [ ] AI-to-CAD Pipeline Proof of Concept
- [ ] Set up repository structure from [Project Structure](docs/project-structure.md)
- [ ] Configure CI/CD pipelines

---

## Quick Start

### With Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-org/ai-part-designer.git
cd ai-part-designer

# Start all services with Docker Compose
make dev
```

### Local Development with Ollama (FREE AI)

Run AI generation locally without any API costs using [Ollama](https://ollama.ai):

```bash
# 1. Install Ollama from https://ollama.ai
# 2. Pull the model
ollama pull llama3.2

# 3. Start Ollama (if not already running)
ollama serve

# 4. Start infrastructure + setup database
make dev-local

# 5. Start the backend
make dev-backend-local
```

The `.env` file is pre-configured for Ollama. To use OpenAI instead:
```bash
# Edit .env and set:
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key
```

**Access Points:**
| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

**Test Credentials (seeded):**
| Email | Password | Tier |
|-------|----------|------|
| demo@example.com | demo123 | Free |
| pro@example.com | pro123 | Pro |
| admin@assemblematicai.com | admin123! | Admin |

### OAuth Configuration (Google & GitHub Login)

OAuth provides secure, passwordless authentication for your users.

> **📘 For Production Deployment:**
> See the comprehensive [OAuth Production Setup Guide](docs/operations/oauth-production-setup.md) for detailed configuration and the [OAuth Testing Runbook](docs/operations/oauth-testing-runbook.md) for validation procedures.

#### Quick Setup (Development)

To enable "Login with Google" and "Login with GitHub" in local development:

#### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select an existing one
3. Go to "APIs & Services" → "Credentials"
4. Click "Create Credentials" → "OAuth Client ID"
5. Select "Web application" as application type
6. Configure:
   - **Name**: AssemblematicAI (Development)
   - **Authorized JavaScript origins**: 
     - `http://localhost:5173`
     - `http://localhost:8000`
   - **Authorized redirect URIs**:
     - `http://localhost:8000/api/v1/auth/oauth/google/callback`
     - `http://localhost:5173/auth/callback/google`
7. Copy the Client ID and Client Secret

#### GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Configure:
   - **Application name**: AssemblematicAI (Development)
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:8000/api/v1/auth/oauth/github/callback`
4. Register the application
5. Generate a new client secret
6. Copy the Client ID and Client Secret

#### Configure Environment Variables

Add these to your `.env` file in the `backend/` directory:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# GitHub OAuth
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# OAuth redirect base (must match your frontend URL)
OAUTH_REDIRECT_BASE=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

#### Troubleshooting OAuth

| Issue | Solution |
|-------|----------|
| "redirect_uri_mismatch" | Ensure callback URLs in provider match exactly with `OAUTH_REDIRECT_BASE` |
| "OAuth not configured" | Check that both `CLIENT_ID` and `CLIENT_SECRET` are set |
| Infinite redirect loop | Clear browser cookies and check `FRONTEND_URL` setting |
| "Invalid state" error | Session cookies may be blocked; try incognito mode |

> **Production Note**: For production, update the callback URLs to use `https://assemblematic.ai` and set `OAUTH_REDIRECT_BASE=https://api.assemblematic.ai`

For detailed setup instructions, see the [Development Setup Guide](docs/development-setup-guide.md).

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18 + TypeScript + Vite + Three.js |
| **Backend** | Python 3.11 + FastAPI |
| **Database** | PostgreSQL 15 (RDS/Cloud SQL/Azure DB/self-hosted) |
| **Queue** | Celery + Redis |
| **CAD Engine** | Build123d + OpenCASCADE (STEP export) |
| **AI/ML** | Claude (Anthropic) + Declarative Schema Pipeline |
| **Storage** | S3/GCS/Azure Blob/MinIO (abstracted) |
| **Infrastructure** | Kubernetes (EKS/GKE/AKS/k3s) + Terraform |
| **Monitoring** | OpenTelemetry + Prometheus + Grafana |

> **Cloud-Agnostic**: See [ADR-013](docs/adrs/adr-013-cloud-agnostic-architecture.md) for our multi-cloud strategy.

### CAD v2 Architecture

The CAD generation system uses a **declarative schema** approach:

1. **AI Intent Extraction** - Claude extracts design requirements from natural language
2. **Schema Generation** - AI outputs validated JSON conforming to Pydantic schemas
3. **Schema Validation** - Pydantic validates before CAD execution
4. **Deterministic Compilation** - Schema compiles to Build123d geometry
5. **Export** - STEP/STL files for manufacturing and 3D printing

See [ADR-016: Declarative CAD Schema](docs/adrs/adr-016-declarative-cad-schema.md) for details.

---

## Documentation

### 📋 Business Analysis
- [Business Requirements Document](docs/business-requirements-document.md)
- [Functional Requirements Document](docs/functional-requirements-document.md)
- [User Stories (Detailed)](docs/user-stories-detailed.md)
- [Gap Analysis](docs/gap-analysis.md)
- [Requirements Traceability Matrix](docs/requirements-traceability-matrix.md)

### 📦 Product
- [Product Roadmap](docs/product-roadmap.md)
- [Original Roadmap](ROADMAP.md)
- [Milestones](milestones.md)
- [User Stories (Summary)](user-stories.md)

### 📋 Project Management
- [Work Breakdown Structure](docs/work-breakdown-structure.md) ⭐ **NEW**
- [Sprint Backlog](docs/sprint-backlog.md) ⭐ **NEW**

### 🏗️ Architecture
- [System Architecture](docs/system-architecture.md) ⭐
- [ADR Index](docs/adrs/README.md)
- [ADR-001: Frontend Framework](docs/adrs/adr-001-frontend-framework.md)
- [ADR-002: Backend Framework](docs/adrs/adr-002-backend-framework.md)
- [ADR-003: Database](docs/adrs/adr-003-database-technology.md)
- [ADR-004: Queue System](docs/adrs/adr-004-queue-system.md)
- [ADR-005: CAD Library](docs/adrs/adr-005-cad-processing-library.md)
- [ADR-006: AI/ML Integration](docs/adrs/adr-006-ai-ml-integration.md)
- [ADR-007: Authentication](docs/adrs/adr-007-authentication-strategy.md)
- [ADR-008: File Storage](docs/adrs/adr-008-file-storage.md)
- [ADR-009: Deployment](docs/adrs/adr-009-deployment-platform.md)
- [ADR-010: API Versioning](docs/adrs/adr-010-api-versioning.md)
- [ADR-011: Monitoring](docs/adrs/adr-011-monitoring-observability.md)
- [ADR-012: Content Moderation](docs/adrs/adr-012-content-moderation.md)
- [ADR-015: Security Architecture](docs/adrs/adr-015-security-architecture.md)
- [ADR-016: Declarative CAD Schema](docs/adrs/adr-016-declarative-cad-schema.md) ⭐ **NEW**

### 🔧 CAD v2 System
- [Sprint Plan: CAD v2 Refactor](docs/sprint-planning-cad-v2-refactor.md) ⭐ **NEW**
- [Component Library Scope](docs/cad-v2-component-library-scope.md) ⭐ **NEW**

### 🔐 Security
- [Security Checklist](docs/security-checklist.md) ⭐ **NEW**

### 🛠️ Technical Specifications
- [API Specification (OpenAPI)](docs/api-specification.yaml) ⭐
- [Database Schema](docs/database-schema.md) ⭐
- [Project Structure](docs/project-structure.md) ⭐

### 👨‍💻 Development
- [Development Setup Guide](docs/development-setup-guide.md) ⭐
- [Coding Standards](docs/coding-standards.md) ⭐
- [CI/CD Pipeline](docs/ci-cd-pipeline.md) ⭐

---

## Timeline

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 0: Foundation** | Weeks 1-3 | POCs, infrastructure setup |
| **Phase 1: Core MVP** | Weeks 4-12 | Auth, templates, generation, files |
| **Phase 2: Monetization** | Weeks 13-17 | Subscriptions, priority queue, moderation |
| **Phase 3: Launch** | Weeks 18-20 | Testing, documentation, production |

**Estimated MVP Launch:** ~20 weeks from start

---

## Contributing

This project is currently in the planning phase. Contribution guidelines will be established once development begins.

---

## License

TBD

---

## Contact

- Repository: [jmassardo/ai-part-designer](https://github.com/jmassardo/ai-part-designer)