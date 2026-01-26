# Project Structure
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  

---

## Overview

This document defines the monorepo structure for AI Part Designer, organized for maintainability, clear separation of concerns, and efficient CI/CD pipelines.

---

## Repository Structure

```
ai-part-designer/
│
├── .github/                          # GitHub Actions & templates
│   ├── workflows/
│   │   ├── ci.yml                    # PR checks (lint, test, build)
│   │   ├── deploy-staging.yml        # Deploy to staging
│   │   ├── deploy-production.yml     # Deploy to production
│   │   └── dependency-review.yml     # Security scanning
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── config.yml
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── CODEOWNERS
│
├── docs/                             # Documentation
│   ├── adrs/                         # Architecture Decision Records
│   ├── api/                          # API documentation (generated)
│   ├── architecture/                 # Architecture diagrams
│   ├── runbooks/                     # Operations runbooks
│   └── *.md                          # Various docs
│
├── frontend/                         # React SPA
│   ├── public/
│   │   ├── favicon.ico
│   │   ├── robots.txt
│   │   └── manifest.json
│   ├── src/
│   │   ├── api/                      # API client
│   │   │   ├── client.ts             # Axios/fetch setup
│   │   │   ├── auth.ts               # Auth endpoints
│   │   │   ├── designs.ts            # Design endpoints
│   │   │   ├── templates.ts          # Template endpoints
│   │   │   ├── jobs.ts               # Job endpoints
│   │   │   └── types.ts              # API types (generated from OpenAPI)
│   │   │
│   │   ├── components/               # React components
│   │   │   ├── ui/                   # Base UI components (shadcn/ui)
│   │   │   │   ├── button.tsx
│   │   │   │   ├── input.tsx
│   │   │   │   ├── dialog.tsx
│   │   │   │   └── ...
│   │   │   ├── layout/               # Layout components
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Footer.tsx
│   │   │   │   └── MainLayout.tsx
│   │   │   ├── design/               # Design-specific components
│   │   │   │   ├── DesignCard.tsx
│   │   │   │   ├── DesignGrid.tsx
│   │   │   │   ├── ParameterForm.tsx
│   │   │   │   └── VersionHistory.tsx
│   │   │   ├── viewer/               # 3D viewer components
│   │   │   │   ├── ModelViewer.tsx
│   │   │   │   ├── ViewerControls.tsx
│   │   │   │   ├── MeasurementTool.tsx
│   │   │   │   └── ExportPanel.tsx
│   │   │   └── common/               # Shared components
│   │   │       ├── LoadingSpinner.tsx
│   │   │       ├── ErrorBoundary.tsx
│   │   │       └── ConfirmDialog.tsx
│   │   │
│   │   ├── features/                 # Feature modules
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   ├── RegisterForm.tsx
│   │   │   │   ├── ForgotPassword.tsx
│   │   │   │   └── useAuth.ts
│   │   │   ├── dashboard/
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── RecentDesigns.tsx
│   │   │   │   └── QuickActions.tsx
│   │   │   ├── templates/
│   │   │   │   ├── TemplateGallery.tsx
│   │   │   │   ├── TemplateDetail.tsx
│   │   │   │   └── TemplateCustomizer.tsx
│   │   │   ├── designs/
│   │   │   │   ├── DesignList.tsx
│   │   │   │   ├── DesignDetail.tsx
│   │   │   │   ├── DesignEditor.tsx
│   │   │   │   └── AIDescriptionInput.tsx
│   │   │   └── settings/
│   │   │       ├── SettingsPage.tsx
│   │   │       ├── ProfileSettings.tsx
│   │   │       └── SubscriptionSettings.tsx
│   │   │
│   │   ├── hooks/                    # Custom hooks
│   │   │   ├── useDesigns.ts
│   │   │   ├── useTemplates.ts
│   │   │   ├── useJobs.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── useLocalStorage.ts
│   │   │
│   │   ├── lib/                      # Utility libraries
│   │   │   ├── utils.ts              # General utilities
│   │   │   ├── validation.ts         # Form validation
│   │   │   ├── formatting.ts         # Date, number formatting
│   │   │   └── three-helpers.ts      # Three.js utilities
│   │   │
│   │   ├── stores/                   # Zustand stores
│   │   │   ├── authStore.ts
│   │   │   ├── designStore.ts
│   │   │   ├── uiStore.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── pages/                    # Page components (routes)
│   │   │   ├── Home.tsx
│   │   │   ├── Login.tsx
│   │   │   ├── Register.tsx
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Templates.tsx
│   │   │   ├── DesignEditor.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── NotFound.tsx
│   │   │
│   │   ├── types/                    # TypeScript types
│   │   │   ├── design.ts
│   │   │   ├── template.ts
│   │   │   ├── user.ts
│   │   │   └── index.ts
│   │   │
│   │   ├── styles/                   # Global styles
│   │   │   ├── globals.css
│   │   │   └── tailwind.css
│   │   │
│   │   ├── App.tsx                   # App component
│   │   ├── main.tsx                  # Entry point
│   │   └── router.tsx                # Route definitions
│   │
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
│
├── backend/                          # Python/FastAPI backend
│   ├── alembic/                      # Database migrations
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   │
│   ├── app/
│   │   ├── api/                      # API routes
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py         # Main v1 router
│   │   │   │   ├── auth.py           # Auth endpoints
│   │   │   │   ├── users.py          # User endpoints
│   │   │   │   ├── designs.py        # Design endpoints
│   │   │   │   ├── templates.py      # Template endpoints
│   │   │   │   ├── jobs.py           # Job endpoints
│   │   │   │   └── exports.py        # Export endpoints
│   │   │   └── deps.py               # Route dependencies
│   │   │
│   │   ├── core/                     # Core configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py             # Settings (pydantic-settings)
│   │   │   ├── security.py           # JWT, password hashing
│   │   │   ├── database.py           # DB connection
│   │   │   └── exceptions.py         # Custom exceptions
│   │   │
│   │   ├── models/                   # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── design.py
│   │   │   ├── template.py
│   │   │   ├── job.py
│   │   │   └── moderation.py
│   │   │
│   │   ├── schemas/                  # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── design.py
│   │   │   ├── template.py
│   │   │   ├── job.py
│   │   │   └── common.py
│   │   │
│   │   ├── services/                 # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── design.py
│   │   │   ├── template.py
│   │   │   ├── job.py
│   │   │   ├── storage.py
│   │   │   ├── ai.py
│   │   │   └── moderation.py
│   │   │
│   │   ├── repositories/             # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── user.py
│   │   │   ├── design.py
│   │   │   ├── template.py
│   │   │   └── job.py
│   │   │
│   │   ├── middleware/               # Custom middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── rate_limit.py
│   │   │   ├── logging.py
│   │   │   └── error_handler.py
│   │   │
│   │   ├── tasks/                    # Celery tasks (shared definitions)
│   │   │   ├── __init__.py
│   │   │   └── job_tasks.py
│   │   │
│   │   └── main.py                   # FastAPI app entry
│   │
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── services/
│   │   │   └── repositories/
│   │   ├── integration/
│   │   │   └── api/
│   │   ├── conftest.py
│   │   └── factories.py
│   │
│   ├── scripts/
│   │   ├── seed_templates.py
│   │   └── create_admin.py
│   │
│   ├── .env.example
│   ├── pyproject.toml
│   ├── poetry.lock
│   ├── Dockerfile
│   └── pytest.ini
│
├── worker/                           # Celery worker
│   ├── app/
│   │   ├── __init__.py
│   │   ├── celery.py                 # Celery app config
│   │   ├── config.py                 # Worker-specific config
│   │   │
│   │   ├── tasks/                    # Task definitions
│   │   │   ├── __init__.py
│   │   │   ├── generate.py           # Design generation tasks
│   │   │   ├── modify.py             # Modification tasks
│   │   │   ├── export.py             # Export tasks
│   │   │   └── thumbnail.py          # Thumbnail generation
│   │   │
│   │   ├── engines/                  # Processing engines
│   │   │   ├── __init__.py
│   │   │   ├── cad/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── generator.py      # CadQuery generation
│   │   │   │   ├── templates.py      # Template implementations
│   │   │   │   ├── validation.py     # Geometry validation
│   │   │   │   └── exporters.py      # Format exporters
│   │   │   ├── ai/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── parser.py         # NL → Operations
│   │   │   │   ├── optimizer.py      # Design optimization
│   │   │   │   └── prompts.py        # LLM prompts
│   │   │   └── moderation/
│   │   │       ├── __init__.py
│   │   │       └── classifier.py
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── storage.py
│   │       └── metrics.py
│   │
│   ├── tests/
│   │   └── ...
│   │
│   ├── pyproject.toml
│   ├── poetry.lock
│   └── Dockerfile
│
├── shared/                           # Shared Python code
│   ├── ai_part_designer_common/
│   │   ├── __init__.py
│   │   ├── models.py                 # Shared Pydantic models
│   │   ├── constants.py              # Shared constants
│   │   └── utils.py                  # Shared utilities
│   └── pyproject.toml
│
├── infrastructure/                   # Terraform IaC
│   ├── environments/
│   │   ├── production/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── terraform.tfvars
│   │   └── staging/
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── terraform.tfvars
│   │
│   ├── modules/
│   │   ├── vpc/
│   │   ├── ecs/
│   │   ├── rds/
│   │   ├── redis/
│   │   ├── s3/
│   │   ├── cloudfront/
│   │   └── monitoring/
│   │
│   └── scripts/
│       ├── apply.sh
│       └── plan.sh
│
├── scripts/                          # Dev & deployment scripts
│   ├── dev-setup.sh                  # Local dev environment setup
│   ├── generate-api-client.sh        # Generate TS types from OpenAPI
│   └── run-migrations.sh
│
├── .vscode/                          # VS Code workspace settings
│   ├── settings.json
│   ├── extensions.json
│   └── launch.json
│
├── docker-compose.yml                # Local development
├── docker-compose.test.yml           # Integration tests
├── Makefile                          # Common commands
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

---

## Directory Descriptions

### `/frontend`
React SPA with Vite bundler. Uses shadcn/ui for components, Tailwind for styling, and Three.js for 3D visualization.

**Key patterns:**
- Feature-based organization in `features/`
- API client auto-generated from OpenAPI spec
- Zustand for state management
- TanStack Query for server state

### `/backend`
FastAPI REST API application. Handles authentication, business logic, and database operations.

**Key patterns:**
- Repository pattern for data access
- Service layer for business logic
- Pydantic for validation
- Alembic for migrations

### `/worker`
Celery worker for async task processing. Contains CAD generation engines and AI integration.

**Key patterns:**
- Task-based organization
- Engine abstraction for CAD/AI
- Shared models via `/shared`

### `/shared`
Common Python code shared between backend and worker. Published as internal package.

### `/infrastructure`
Terraform modules for AWS infrastructure. Environment-specific configurations in `environments/`.

### `/docs`
All project documentation including ADRs, architecture diagrams, and runbooks.

---

## Configuration Files

### Root Configuration

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local development environment |
| `Makefile` | Common development commands |
| `.gitignore` | Git ignore patterns |
| `CONTRIBUTING.md` | Contribution guidelines |

### Frontend Configuration

| File | Purpose |
|------|---------|
| `vite.config.ts` | Vite bundler configuration |
| `tsconfig.json` | TypeScript configuration |
| `tailwind.config.js` | Tailwind CSS configuration |
| `.eslintrc.cjs` | ESLint rules |
| `.prettierrc` | Prettier formatting |

### Backend Configuration

| File | Purpose |
|------|---------|
| `pyproject.toml` | Poetry dependencies & config |
| `alembic.ini` | Database migration settings |
| `.env.example` | Environment variable template |
| `pytest.ini` | Test configuration |

---

## Naming Conventions

### Files
| Type | Convention | Example |
|------|------------|---------|
| React component | PascalCase | `DesignCard.tsx` |
| React hook | camelCase with `use` prefix | `useDesigns.ts` |
| Python module | snake_case | `design_service.py` |
| Test file | `test_` prefix or `.test.` | `test_auth.py`, `Auth.test.tsx` |
| Config file | lowercase with extension | `tailwind.config.js` |

### Code
| Language | Type | Convention | Example |
|----------|------|------------|---------|
| TypeScript | Component | PascalCase | `DesignEditor` |
| TypeScript | Function | camelCase | `fetchDesigns` |
| TypeScript | Type/Interface | PascalCase | `DesignResponse` |
| TypeScript | Constant | SCREAMING_SNAKE | `MAX_FILE_SIZE` |
| Python | Class | PascalCase | `DesignService` |
| Python | Function | snake_case | `get_design_by_id` |
| Python | Constant | SCREAMING_SNAKE | `DEFAULT_PAGE_SIZE` |
| Python | Private | `_` prefix | `_validate_input` |

---

## Import Guidelines

### Frontend (TypeScript)
```typescript
// 1. React & framework imports
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

// 2. Third-party libraries
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

// 3. Internal absolute imports (components, features, etc.)
import { Button } from '@/components/ui/button';
import { useAuth } from '@/features/auth/useAuth';

// 4. Relative imports
import { DesignCard } from './DesignCard';
import type { DesignProps } from './types';
```

### Backend (Python)
```python
# 1. Standard library
import os
from datetime import datetime
from typing import Optional

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# 3. Local application
from app.core.config import settings
from app.core.database import get_db
from app.services.design import DesignService
from app.schemas.design import DesignCreate, DesignResponse
```

---

## Development Commands

### Makefile Targets

```makefile
# Development
make dev              # Start all services locally
make dev-frontend     # Start frontend only
make dev-backend      # Start backend only
make dev-worker       # Start worker only

# Testing
make test             # Run all tests
make test-frontend    # Run frontend tests
make test-backend     # Run backend tests
make test-worker      # Run worker tests
make test-e2e         # Run end-to-end tests

# Code Quality
make lint             # Run all linters
make format           # Format all code
make typecheck        # Run type checking

# Database
make db-migrate       # Run migrations
make db-rollback      # Rollback last migration
make db-seed          # Seed test data

# Build
make build            # Build all containers
make build-frontend   # Build frontend for production

# Deployment
make deploy-staging   # Deploy to staging
make deploy-prod      # Deploy to production
```

---

*End of Document*
