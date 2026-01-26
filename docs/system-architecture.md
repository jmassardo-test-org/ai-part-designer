# System Architecture Documentation
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  
**Author:** Systems Architecture Team  

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [C4 Model Diagrams](#2-c4-model-diagrams)
3. [Component Architecture](#3-component-architecture)
4. [Data Flow Architecture](#4-data-flow-architecture)
5. [Integration Architecture](#5-integration-architecture)
6. [Security Architecture](#6-security-architecture)
7. [Deployment Architecture](#7-deployment-architecture)

---

## 1. Architecture Overview

### 1.1 Architectural Style
AI Part Designer follows a **layered microservices architecture** with:
- **Presentation Layer**: React SPA with 3D visualization
- **API Layer**: FastAPI RESTful services
- **Business Logic Layer**: Domain services for CAD, AI, and queue processing
- **Data Layer**: PostgreSQL + Redis + S3

### 1.2 Key Architectural Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Architecture Style | Modular Monolith → Microservices | Start simple, split when needed |
| API Design | REST with OpenAPI | Simplicity, tooling support |
| Async Processing | Celery + Redis | Python-native, battle-tested |
| 3D Processing | Server-side CadQuery | Complex geometry, consistent output |
| AI Integration | External API (OpenAI) | Leverage SOTA models, reduce ML ops |

### 1.3 Quality Attributes
| Attribute | Target | Strategy |
|-----------|--------|----------|
| **Performance** | < 60s generation | Async queue, worker scaling |
| **Scalability** | 1000 concurrent users | Horizontal scaling, stateless API |
| **Availability** | 99.9% uptime | Multi-AZ, health checks, auto-recovery |
| **Security** | SOC 2 ready | JWT auth, encryption, moderation |
| **Maintainability** | < 1 day to deploy fix | CI/CD, feature flags, rollback |

---

## 2. C4 Model Diagrams

### 2.1 Level 1: System Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM CONTEXT                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────┐
                    │         End Users           │
                    │  (Makers, Engineers,        │
                    │   Educators)                │
                    └──────────────┬──────────────┘
                                   │ Uses
                                   ▼
                    ┌─────────────────────────────┐
                    │                             │
                    │    AI PART DESIGNER         │
                    │    [Software System]        │
                    │                             │
                    │  AI-powered 3D part         │
                    │  generation platform        │
                    │                             │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   OpenAI API    │    │  Stripe API     │    │  Email Service  │
│ [External Sys]  │    │ [External Sys]  │    │ [External Sys]  │
│                 │    │                 │    │                 │
│ NL understanding│    │ Payment         │    │ Transactional   │
│ & generation    │    │ processing      │    │ emails          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2.2 Level 2: Container Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CONTAINER DIAGRAM                               │
│                            AI Part Designer System                           │
└─────────────────────────────────────────────────────────────────────────────┘

     ┌─────────────────────────────────────────────────────────────────┐
     │                         End Users                                │
     └───────────────────────────────┬─────────────────────────────────┘
                                     │ HTTPS
                                     ▼
     ┌───────────────────────────────────────────────────────────────────┐
     │                     CDN / Load Balancer                           │
     │        (CloudFront/Cloud CDN/Cloudflare + Ingress)               │
     └────────────────┬─────────────────────────────┬────────────────────┘
                      │                             │
          Static Assets                        API Requests
                      │                             │
                      ▼                             ▼
┌─────────────────────────────┐      ┌─────────────────────────────────────┐
│      WEB APPLICATION        │      │           API APPLICATION           │
│      [Container: React]     │      │      [Container: Python/FastAPI]    │
│                             │      │                                     │
│  - Single Page Application  │      │  - RESTful API endpoints            │
│  - 3D Viewer (Three.js)     │      │  - Authentication/Authorization     │
│  - Template customization   │      │  - Request validation               │
│  - Design management        │      │  - Business logic orchestration     │
│                             │      │                                     │
└─────────────────────────────┘      └──────────────────┬──────────────────┘
                                                        │
                        ┌───────────────────────────────┼───────────────────┐
                        │                               │                   │
                        ▼                               ▼                   ▼
         ┌─────────────────────────┐    ┌─────────────────────┐   ┌─────────────────┐
         │      DATABASE           │    │    CACHE / QUEUE    │   │   FILE STORAGE  │
         │  [Container: PostgreSQL]│    │ [Container: Redis]  │   │ [S3/GCS/MinIO]  │
         │                         │    │                     │   │                 │
         │  - User accounts        │    │  - Session cache    │   │  - Design files │
         │  - Designs & versions   │    │  - Job queue        │   │  - Thumbnails   │
         │  - Jobs & history       │    │  - Rate limiting    │   │  - Exports      │
         │  - Subscriptions        │    │  - Real-time state  │   │  - Uploads      │
         └─────────────────────────┘    └──────────┬──────────┘   └─────────────────┘
                                                   │
                                                   │ Consumes jobs
                                                   ▼
                                    ┌─────────────────────────────────────┐
                                    │         WORKER APPLICATION          │
                                    │       [Container: Celery/Python]    │
                                    │                                     │
                                    │  - CAD generation (CadQuery)        │
                                    │  - AI processing (OpenAI)           │
                                    │  - File conversion                  │
                                    │  - Thumbnail generation             │
                                    │                                     │
                                    └─────────────────────────────────────┘
                                                   │
                        ┌──────────────────────────┼──────────────────────┐
                        ▼                          ▼                      ▼
              ┌─────────────────┐      ┌─────────────────┐     ┌─────────────────┐
              │   OpenAI API    │      │   Stripe API    │     │  SendGrid API   │
              └─────────────────┘      └─────────────────┘     └─────────────────┘
```

### 2.3 Level 3: Component Diagram (API Application)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     API APPLICATION COMPONENTS                               │
│                        [FastAPI Backend]                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                         │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │  Auth API    │ │ Designs API  │ │Templates API │ │  Jobs API    │       │
│  │  /api/v1/    │ │  /api/v1/    │ │  /api/v1/    │ │  /api/v1/    │       │
│  │  auth/*      │ │  designs/*   │ │  templates/* │ │  jobs/*      │       │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘       │
│         │                │                │                │                │
│  ┌──────┴────────────────┴────────────────┴────────────────┴───────┐       │
│  │                     MIDDLEWARE LAYER                             │       │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │       │
│  │  │ Auth       │ │ Rate       │ │ Request    │ │ Error      │    │       │
│  │  │ Middleware │ │ Limiter    │ │ Logging    │ │ Handler    │    │       │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘    │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SERVICE LAYER                                       │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ Auth         │ │ Design       │ │ Template     │ │ Job          │       │
│  │ Service      │ │ Service      │ │ Service      │ │ Service      │       │
│  │              │ │              │ │              │ │              │       │
│  │ - Login      │ │ - Create     │ │ - List       │ │ - Submit     │       │
│  │ - Register   │ │ - Modify     │ │ - Get params │ │ - Status     │       │
│  │ - Verify     │ │ - Export     │ │ - Generate   │ │ - Cancel     │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ Storage      │ │ AI           │ │ Moderation   │ │ Notification │       │
│  │ Service      │ │ Service      │ │ Service      │ │ Service      │       │
│  │              │ │              │ │              │ │              │       │
│  │ - Upload     │ │ - Parse desc │ │ - Check input│ │ - Email      │       │
│  │ - Download   │ │ - Optimize   │ │ - Review     │ │ - In-app     │       │
│  │ - Presign    │ │ - Suggest    │ │ - Flag       │ │ - WebSocket  │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DATA ACCESS LAYER                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ User         │ │ Design       │ │ Job          │ │ Template     │       │
│  │ Repository   │ │ Repository   │ │ Repository   │ │ Repository   │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                    │                                         │
│  ┌─────────────────────────────────┴───────────────────────────────┐       │
│  │                    SQLAlchemy ORM / Async Session                │       │
│  └──────────────────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Level 3: Component Diagram (Worker Application)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     WORKER APPLICATION COMPONENTS                            │
│                          [Celery Workers]                                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           TASK LAYER                                         │
│  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐            │
│  │ generate_design  │ │ modify_design    │ │ convert_file     │            │
│  │ [Celery Task]    │ │ [Celery Task]    │ │ [Celery Task]    │            │
│  └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘            │
│           │                    │                    │                       │
│  ┌────────┴────────────────────┴────────────────────┴────────┐             │
│  │                     TASK ORCHESTRATOR                      │             │
│  │  - Progress tracking                                       │             │
│  │  - Error handling & retry                                  │             │
│  │  - Result storage                                          │             │
│  └────────────────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ENGINE LAYER                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        CAD ENGINE                                    │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │   │
│  │  │ Template     │ │ Generation   │ │ Validation   │                 │   │
│  │  │ Engine       │ │ Engine       │ │ Engine       │                 │   │
│  │  │              │ │              │ │              │                 │   │
│  │  │ - Load tmpl  │ │ - Parse ops  │ │ - Manifold   │                 │   │
│  │  │ - Apply params│ │ - Execute    │ │ - Printable  │                 │   │
│  │  │ - Render     │ │ - Boolean ops│ │ - Dimensions │                 │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                 │   │
│  │                              │                                       │   │
│  │                    ┌─────────┴─────────┐                            │   │
│  │                    │    CadQuery +     │                            │   │
│  │                    │   OpenCASCADE     │                            │   │
│  │                    └───────────────────┘                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         AI ENGINE                                    │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │   │
│  │  │ Description  │ │ Optimization │ │ Content      │                 │   │
│  │  │ Parser       │ │ Analyzer     │ │ Moderator    │                 │   │
│  │  │              │ │              │ │              │                 │   │
│  │  │ - NL → Ops   │ │ - Printability│ │ - Intent     │                 │   │
│  │  │ - Params     │ │ - Structural │ │ - Keywords   │                 │   │
│  │  │ - Templates  │ │ - Suggestions│ │ - ML classify│                 │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                 │   │
│  │                              │                                       │   │
│  │                    ┌─────────┴─────────┐                            │   │
│  │                    │  OpenAI GPT-4 +   │                            │   │
│  │                    │    LangChain      │                            │   │
│  │                    └───────────────────┘                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        EXPORT ENGINE                                 │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │   │
│  │  │ STEP         │ │ STL          │ │ Thumbnail    │                 │   │
│  │  │ Exporter     │ │ Exporter     │ │ Renderer     │                 │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Architecture

### 3.1 Domain Model

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DOMAIN MODEL                                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│    User     │ 1    n  │   Project   │ 1    n  │   Design    │
├─────────────┤─────────├─────────────┤─────────├─────────────┤
│ id          │         │ id          │         │ id          │
│ email       │         │ userId      │         │ projectId   │
│ password    │         │ name        │         │ name        │
│ displayName │         │ createdAt   │         │ description │
│ role        │         │ updatedAt   │         │ sourceType  │
│ tier        │         └─────────────┘         │ status      │
│ status      │                                 │ fileUrl     │
│ createdAt   │                                 │ metadata    │
└──────┬──────┘                                 └──────┬──────┘
       │                                               │
       │ 1                                          1  │ n
       │ n                                             │
┌──────┴──────┐                                 ┌──────┴──────┐
│ Subscription│                                 │   Version   │
├─────────────┤                                 ├─────────────┤
│ id          │                                 │ id          │
│ userId      │                                 │ designId    │
│ tier        │                                 │ versionNum  │
│ status      │                                 │ fileUrl     │
│ stripeId    │                                 │ changeDesc  │
│ expiresAt   │                                 │ createdAt   │
└─────────────┘                                 └─────────────┘

┌─────────────┐                                 ┌─────────────┐
│    User     │ 1                            n  │    Job      │
├─────────────┤─────────────────────────────────├─────────────┤
│             │                                 │ id          │
│             │                                 │ userId      │
│             │                                 │ designId    │
└─────────────┘                                 │ type        │
                                                │ status      │
┌─────────────┐                                 │ priority    │
│  Template   │                                 │ input       │
├─────────────┤                                 │ output      │
│ id          │                                 │ progress    │
│ name        │                                 │ error       │
│ category    │                                 │ createdAt   │
│ description │                                 │ startedAt   │
│ parameters  │                                 │ completedAt │
│ tier        │                                 └─────────────┘
│ previewUrl  │
└─────────────┘
```

### 3.2 Service Boundaries

| Service | Responsibility | Dependencies |
|---------|----------------|--------------|
| **AuthService** | Authentication, authorization, sessions | UserRepository, Redis |
| **UserService** | User CRUD, profile management | UserRepository, AuthService |
| **DesignService** | Design CRUD, versioning | DesignRepository, StorageService |
| **TemplateService** | Template catalog, parameter validation | TemplateRepository |
| **JobService** | Job submission, status, queue management | JobRepository, Redis, Celery |
| **CADService** | Geometry generation, validation, export | CadQuery, StorageService |
| **AIService** | NL parsing, optimization suggestions | OpenAI, LangChain |
| **ModerationService** | Content filtering, intent detection | OpenAI, Repository |
| **StorageService** | File upload/download, presigned URLs | S3 |
| **NotificationService** | Email, in-app notifications | SendGrid, WebSocket |
| **SubscriptionService** | Tier management, billing | Stripe, UserRepository |

---

## 4. Data Flow Architecture

### 4.1 Design Generation Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                     DESIGN GENERATION SEQUENCE                                │
└──────────────────────────────────────────────────────────────────────────────┘

 User        Frontend       API           Moderation    Queue        Worker       Storage
  │             │            │                │           │            │            │
  │  Submit     │            │                │           │            │            │
  │  description│            │                │           │            │            │
  │────────────>│            │                │           │            │            │
  │             │  POST      │                │           │            │            │
  │             │  /designs  │                │           │            │            │
  │             │───────────>│                │           │            │            │
  │             │            │  Check content │           │            │            │
  │             │            │───────────────>│           │            │            │
  │             │            │                │           │            │            │
  │             │            │  OK / BLOCK    │           │            │            │
  │             │            │<───────────────│           │            │            │
  │             │            │                │           │            │            │
  │             │            │  Create Job    │           │            │            │
  │             │            │───────────────────────────>│            │            │
  │             │            │                │           │            │            │
  │             │  202       │                │           │            │            │
  │             │  Accepted  │                │           │            │            │
  │             │  job_id    │                │           │            │            │
  │             │<───────────│                │           │            │            │
  │  Show       │            │                │           │            │            │
  │  progress   │            │                │           │            │            │
  │<────────────│            │                │           │            │            │
  │             │            │                │           │            │            │
  │             │            │                │  Dequeue  │            │            │
  │             │            │                │  job      │            │            │
  │             │            │                │───────────────────────>│            │
  │             │            │                │           │            │            │
  │             │            │                │           │  Parse     │            │
  │             │            │                │           │  with AI   │            │
  │             │            │                │           │───────────>│ (OpenAI)   │
  │             │            │                │           │<───────────│            │
  │             │            │                │           │            │            │
  │             │            │                │           │  Generate  │            │
  │             │            │                │           │  CAD       │            │
  │             │            │                │           │───────────>│ (CadQuery) │
  │             │            │                │           │<───────────│            │
  │             │            │                │           │            │            │
  │             │            │                │           │  Upload    │            │
  │             │            │                │           │  files     │            │
  │             │            │                │           │────────────────────────>│
  │             │            │                │           │            │            │
  │             │            │                │           │  Update    │            │
  │             │            │                │           │  job status│            │
  │             │            │                │           │───────────>│            │
  │             │            │                │           │            │            │
  │             │  WebSocket │                │           │            │            │
  │             │  job       │                │           │            │            │
  │             │  complete  │                │           │            │            │
  │             │<═══════════════════════════════════════════════════ │            │
  │  Show       │            │                │           │            │            │
  │  result     │            │                │           │            │            │
  │<────────────│            │                │           │            │            │
```

### 4.2 Authentication Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                       AUTHENTICATION SEQUENCE                                 │
└──────────────────────────────────────────────────────────────────────────────┘

 User        Frontend       API           AuthService    Database      Redis
  │             │            │                │             │            │
  │  Login      │            │                │             │            │
  │  email/pass │            │                │             │            │
  │────────────>│            │                │             │            │
  │             │  POST      │                │             │            │
  │             │  /auth/    │                │             │            │
  │             │  login     │                │             │            │
  │             │───────────>│                │             │            │
  │             │            │  Validate      │             │            │
  │             │            │───────────────>│             │            │
  │             │            │                │  Get user   │            │
  │             │            │                │────────────>│            │
  │             │            │                │  User data  │            │
  │             │            │                │<────────────│            │
  │             │            │                │             │            │
  │             │            │                │  Verify pwd │            │
  │             │            │                │  (bcrypt)   │            │
  │             │            │                │             │            │
  │             │            │                │  Generate   │            │
  │             │            │                │  tokens     │            │
  │             │            │                │             │            │
  │             │            │                │  Store      │            │
  │             │            │                │  refresh    │            │
  │             │            │                │─────────────────────────>│
  │             │            │                │             │            │
  │             │            │  Tokens        │             │            │
  │             │            │<───────────────│             │            │
  │             │  200 OK    │                │             │            │
  │             │  access +  │                │             │            │
  │             │  refresh   │                │             │            │
  │             │<───────────│                │             │            │
  │  Store      │            │                │             │            │
  │  tokens     │            │                │             │            │
  │<────────────│            │                │             │            │
  │             │            │                │             │            │
  │             │            │                │             │            │
  │  Later...   │            │                │             │            │
  │  API call   │            │                │             │            │
  │────────────>│            │                │             │            │
  │             │  GET       │                │             │            │
  │             │  /designs  │                │             │            │
  │             │  + Bearer  │                │             │            │
  │             │  token     │                │             │            │
  │             │───────────>│                │             │            │
  │             │            │  Validate JWT  │             │            │
  │             │            │───────────────>│             │            │
  │             │            │  User context  │             │            │
  │             │            │<───────────────│             │            │
  │             │            │                │             │            │
  │             │  200 OK    │                │             │            │
  │             │  designs   │                │             │            │
  │             │<───────────│                │             │            │
```

---

## 5. Integration Architecture

### 5.1 External Service Integrations

| Service | Purpose | Integration Pattern | Fallback |
|---------|---------|---------------------|----------|
| **OpenAI** | NL parsing, moderation | REST API, async | Claude API |
| **Stripe** | Payments, subscriptions | Webhooks + API | Manual billing |
| **SendGrid** | Transactional email | REST API | AWS SES |
| **AWS S3** | File storage | SDK, presigned URLs | Azure Blob |
| **Sentry** | Error tracking | SDK | CloudWatch |

### 5.2 API Gateway Pattern

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API GATEWAY PATTERN                                  │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   CDN + WAF     │
                              │ (CloudFront/    │
                              │  Cloudflare)    │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │ K8s Ingress /   │
                              │ Load Balancer   │
                              └────────┬────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
        ▼                              ▼                              ▼
┌───────────────┐            ┌───────────────┐            ┌───────────────┐
│   /api/v1/*   │            │  /static/*    │            │   /ws/*       │
│   (FastAPI)   │            │   (S3/CDN)    │            │  (WebSocket)  │
└───────────────┘            └───────────────┘            └───────────────┘
```

### 5.3 Event-Driven Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EVENT-DRIVEN ARCHITECTURE                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
│    API Server   │          │      Redis      │          │     Workers     │
│                 │          │   (Pub/Sub +    │          │                 │
│ - Job submitted ├─────────>│    Queue)       ├─────────>│ - Process job   │
│ - Design saved  │          │                 │          │ - Publish result│
│ - User action   │          │ Channels:       │          │                 │
└─────────────────┘          │ - jobs:status   │          └────────┬────────┘
                             │ - user:{id}     │                   │
┌─────────────────┐          │ - design:{id}   │                   │
│   WebSocket     │          │                 │                   │
│   Server        │<─────────┤                 │<──────────────────┘
│                 │          │                 │
│ - Push to client│          └─────────────────┘
└─────────────────┘
```

---

## 6. Security Architecture

### 6.1 Security Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SECURITY ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                           PERIMETER SECURITY                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CloudFront + AWS WAF                                                │   │
│  │  - DDoS protection                                                   │   │
│  │  - SQL injection filtering                                           │   │
│  │  - Rate limiting (IP-based)                                          │   │
│  │  - Geo-blocking (if needed)                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         APPLICATION SECURITY                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  API Layer                                                           │   │
│  │  - JWT validation                                                    │   │
│  │  - RBAC enforcement                                                  │   │
│  │  - Input validation (Pydantic)                                       │   │
│  │  - Rate limiting (per-user)                                          │   │
│  │  - CORS configuration                                                │   │
│  │  - CSRF protection                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Content Security                                                    │   │
│  │  - Input moderation                                                  │   │
│  │  - Output validation                                                 │   │
│  │  - File type validation                                              │   │
│  │  - Virus scanning                                                    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            DATA SECURITY                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Encryption                                                          │   │
│  │  - TLS 1.3 in transit                                               │   │
│  │  - AES-256 at rest (S3, RDS)                                        │   │
│  │  - bcrypt password hashing                                           │   │
│  │  - Secrets in Vault/Cloud Secrets Manager                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Access Control                                                      │   │
│  │  - VPC isolation                                                     │   │
│  │  - Security groups                                                   │   │
│  │  - IAM roles (least privilege)                                       │   │
│  │  - Database access via private subnet                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Authentication & Authorization Matrix

| Endpoint | Auth Required | Roles Allowed | Rate Limit |
|----------|---------------|---------------|------------|
| `POST /auth/register` | No | Public | 3/hour/IP |
| `POST /auth/login` | No | Public | 5/min/IP |
| `GET /templates` | No | Public | 100/min |
| `POST /designs` | Yes | user, admin | 30/min (Free), 100/min (Pro) |
| `GET /designs` | Yes | owner, admin | 100/min |
| `GET /admin/*` | Yes | admin | 60/min |

---

## 7. Deployment Architecture

> **Note:** This architecture is cloud-agnostic per [ADR-013](adrs/adr-013-cloud-agnostic-architecture.md). 
> Examples show AWS, but the same patterns apply to GCP, Azure, or self-hosted Kubernetes.

### 7.1 Kubernetes Deployment (Cloud-Agnostic)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CLOUD-AGNOSTIC DEPLOYMENT ARCHITECTURE                    │
│           (AWS EKS / GCP GKE / Azure AKS / Self-hosted k3s)                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE LAYER                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐       │
│  │   DNS           │     │   CDN           │     │   WAF           │       │
│  │ (Route53/Cloud  │────>│ (CloudFront/    │────>│ (Cloud WAF/     │       │
│  │  DNS/Cloudflare)│     │  Cloudflare)    │     │  Cloudflare)    │       │
│  └─────────────────┘     └─────────────────┘     └─────────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KUBERNETES CLUSTER                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    INGRESS CONTROLLER                                  │ │
│  │                    (nginx-ingress / Traefik)                          │ │
│  │  - TLS termination                                                     │ │
│  │  - Path-based routing                                                  │ │
│  │  - Rate limiting                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    NAMESPACE: ai-part-designer                         │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────┐     ┌─────────────────────────┐         │ │
│  │  │  DEPLOYMENT: api        │     │  DEPLOYMENT: worker     │         │ │
│  │  │  replicas: 2-20         │     │  replicas: 2-20         │         │ │
│  │  │  ┌─────────────────┐    │     │  ┌─────────────────┐    │         │ │
│  │  │  │ Pod: api        │    │     │  │ Pod: worker     │    │         │ │
│  │  │  │ - FastAPI       │    │     │  │ - Celery        │    │         │ │
│  │  │  │ - Port: 8000    │    │     │  │ - CadQuery      │    │         │ │
│  │  │  └─────────────────┘    │     │  └─────────────────┘    │         │ │
│  │  │  HPA: CPU 70%           │     │  KEDA: Queue depth      │         │ │
│  │  └─────────────────────────┘     └─────────────────────────┘         │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────┐     ┌─────────────────────────┐         │ │
│  │  │  SERVICE: api-svc       │     │  SERVICE: worker-svc    │         │ │
│  │  │  type: ClusterIP        │     │  type: ClusterIP        │         │ │
│  │  └─────────────────────────┘     └─────────────────────────┘         │ │
│  │                                                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────┐     │ │
│  │  │  CONFIGMAP & SECRETS                                         │     │ │
│  │  │  - External Secrets Operator (syncs from Vault/Cloud SM)     │     │ │
│  │  │  - ConfigMaps for non-sensitive config                       │     │ │
│  │  └─────────────────────────────────────────────────────────────┘     │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    NAMESPACE: monitoring                               │ │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐        │ │
│  │  │ Prometheus │ │ Grafana    │ │ Loki       │ │ Jaeger     │        │ │
│  │  │ (metrics)  │ │ (dashboards)│ │ (logs)     │ │ (traces)   │        │ │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        MANAGED SERVICES (External to K8s)                    │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                  │
│  │      DATABASE           │  │      CACHE              │                  │
│  │  PostgreSQL             │  │  Redis                  │                  │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │                  │
│  │  │ AWS: RDS          │  │  │  │ AWS: ElastiCache  │  │                  │
│  │  │ GCP: Cloud SQL    │  │  │  │ GCP: Memorystore  │  │                  │
│  │  │ Azure: Azure DB   │  │  │  │ Azure: Azure Cache│  │                  │
│  │  │ Self: PostgreSQL  │  │  │  │ Self: Redis       │  │                  │
│  │  └───────────────────┘  │  │  └───────────────────┘  │                  │
│  └─────────────────────────┘  └─────────────────────────┘                  │
│                                                                              │
│  ┌─────────────────────────┐  ┌─────────────────────────┐                  │
│  │      OBJECT STORAGE     │  │      SECRETS            │                  │
│  │  ┌───────────────────┐  │  │  ┌───────────────────┐  │                  │
│  │  │ AWS: S3           │  │  │  │ AWS: Secrets Mgr  │  │                  │
│  │  │ GCP: GCS          │  │  │  │ GCP: Secret Mgr   │  │                  │
│  │  │ Azure: Blob       │  │  │  │ Azure: Key Vault  │  │                  │
│  │  │ Self: MinIO       │  │  │  │ Self: Vault       │  │                  │
│  │  └───────────────────┘  │  │  └───────────────────┘  │                  │
│  └─────────────────────────┘  └─────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Provider Deployment Matrix

| Component | AWS | GCP | Azure | Self-Hosted |
|-----------|-----|-----|-------|-------------|
| **Kubernetes** | EKS | GKE | AKS | k3s / Rancher |
| **Database** | RDS PostgreSQL | Cloud SQL | Azure DB | PostgreSQL on VMs |
| **Cache** | ElastiCache | Memorystore | Azure Cache | Redis on K8s |
| **Storage** | S3 | GCS | Blob Storage | MinIO |
| **CDN** | CloudFront | Cloud CDN | Azure CDN | Cloudflare |
| **DNS** | Route 53 | Cloud DNS | Azure DNS | Cloudflare |
| **Secrets** | Secrets Manager | Secret Manager | Key Vault | HashiCorp Vault |
| **Registry** | ECR | Artifact Registry | ACR | Harbor |

### 7.3 Helm Chart Structure

```
helm/
├── ai-part-designer/
│   ├── Chart.yaml
│   ├── values.yaml                 # Default values
│   ├── values-aws.yaml             # AWS-specific overrides
│   ├── values-gcp.yaml             # GCP-specific overrides
│   ├── values-azure.yaml           # Azure-specific overrides
│   ├── values-selfhosted.yaml      # Self-hosted overrides
│   └── templates/
│       ├── deployment-api.yaml
│       ├── deployment-worker.yaml
│       ├── service-api.yaml
│       ├── ingress.yaml
│       ├── hpa-api.yaml
│       ├── keda-worker.yaml
│       ├── configmap.yaml
│       ├── external-secret.yaml
│       └── _helpers.tpl
```

### 7.4 Container Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        KUBERNETES SERVICE ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  DEPLOYMENT: api                                                             │
│                                                                              │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐               │
│  │ Pod: api        │ │ Pod: api        │ │ Pod: api        │  ...          │
│  │ CPU: 500m       │ │ CPU: 500m       │ │ CPU: 500m       │               │
│  │ Memory: 1Gi     │ │ Memory: 1Gi     │ │ Memory: 1Gi     │               │
│  │ Port: 8000      │ │ Port: 8000      │ │ Port: 8000      │               │
│  │                 │ │                 │ │                 │               │
│  │ Probes:         │ │ Probes:         │ │ Probes:         │               │
│  │ - liveness      │ │ - liveness      │ │ - liveness      │               │
│  │ - readiness     │ │ - readiness     │ │ - readiness     │               │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘               │
│                                                                              │
│  HorizontalPodAutoscaler:                                                    │
│  - minReplicas: 2                                                            │
│  - maxReplicas: 20                                                           │
│  - targetCPUUtilization: 70%                                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  DEPLOYMENT: worker-cad                                                      │
│                                                                              │
│  ┌─────────────────┐ ┌─────────────────┐                                    │
│  │ Pod: worker     │ │ Pod: worker     │                        ...          │
│  │ CPU: 1000m      │ │ CPU: 1000m      │                                    │
│  │ Memory: 2Gi     │ │ Memory: 2Gi     │                                    │
│  │ Queues:         │ │ Queues:         │                                    │
│  │ - priority      │ │ - priority      │                                    │
│  │ - standard      │ │ - standard      │                                    │
│  └─────────────────┘ └─────────────────┘                                    │
│                                                                              │
│  KEDA ScaledObject:                                                          │
│  - minReplicas: 2                                                            │
│  - maxReplicas: 20                                                           │
│  - trigger: redis-list (queue depth > 10)                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Appendix A: Technology Matrix

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| Frontend | React | 18.x | UI framework |
| Frontend | TypeScript | 5.x | Type safety |
| Frontend | Vite | 5.x | Build tool |
| Frontend | Three.js | 0.158+ | 3D rendering |
| Frontend | Tailwind CSS | 3.x | Styling |
| Backend | Python | 3.11+ | Runtime |
| Backend | FastAPI | 0.104+ | API framework |
| Backend | SQLAlchemy | 2.0+ | ORM |
| Backend | Pydantic | 2.x | Validation |
| Backend | Celery | 5.x | Task queue |
| CAD | CadQuery | 2.4+ | CAD kernel |
| CAD | OpenCASCADE | 7.7+ | Geometry engine |
| AI | LangChain | 0.1+ | LLM orchestration |
| AI | OpenAI API | - | LLM provider |
| Database | PostgreSQL | 15+ | Primary DB |
| Cache | Redis | 7+ | Cache/Queue |
| Storage | S3/GCS/Azure Blob/MinIO | - | File storage (abstracted) |
| Infra | Terraform | 1.6+ | IaC |
| Infra | Docker | 24+ | Containers |
| Infra | Kubernetes | 1.28+ | Orchestration (EKS/GKE/AKS/k3s) |
| Observability | OpenTelemetry | 1.x | Metrics/traces/logs collection |
| Observability | Prometheus | 2.x | Metrics storage |
| Observability | Grafana | 10.x | Dashboards |

---

*End of Document*
