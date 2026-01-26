# Database Schema Design
# AI Part Designer

**Version:** 1.0  
**Date:** 2026-01-24  
**Database:** PostgreSQL 15+  

---

## Table of Contents
1. [Schema Overview](#1-schema-overview)
2. [Entity Relationship Diagram](#2-entity-relationship-diagram)
3. [Table Definitions](#3-table-definitions)
4. [Indexes](#4-indexes)
5. [Migrations Strategy](#5-migrations-strategy)

---

## 1. Schema Overview

### 1.1 Design Principles
- **Normalization**: 3NF for core entities, selective denormalization for performance
- **Soft Deletes**: Critical entities use `deleted_at` instead of hard deletes
- **Audit Trail**: `created_at` and `updated_at` on all tables
- **JSONB Usage**: Flexible metadata storage for CAD parameters
- **UUID Primary Keys**: Global uniqueness, no sequential ID exposure

### 1.2 Schema List
| Schema | Purpose |
|--------|---------|
| `public` | Core application tables |
| `audit` | Audit logs and history |

---

## 2. Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ENTITY RELATIONSHIP DIAGRAM                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│      users       │
├──────────────────┤
│ PK id            │
│    email         │
│    password_hash │
│    display_name  │
│    role          │
│    status        │
│    created_at    │
│    updated_at    │
│    deleted_at    │
└────────┬─────────┘
         │
         │ 1:1
         ▼
┌──────────────────┐       ┌──────────────────┐
│  subscriptions   │       │   user_settings  │
├──────────────────┤       ├──────────────────┤
│ PK id            │       │ PK id            │
│ FK user_id       │       │ FK user_id       │
│    tier          │       │    preferences   │
│    status        │       │    notifications │
│    stripe_id     │       └──────────────────┘
│    current_period│
│    created_at    │
└──────────────────┘

         │ 1:N
         ▼
┌──────────────────┐
│     projects     │
├──────────────────┤
│ PK id            │
│ FK user_id       │
│    name          │
│    description   │
│    created_at    │
│    updated_at    │
│    deleted_at    │
└────────┬─────────┘
         │
         │ 1:N
         ▼
┌──────────────────┐
│     designs      │
├──────────────────┤       ┌──────────────────┐
│ PK id            │       │    templates     │
│ FK project_id    │       ├──────────────────┤
│ FK template_id   │◄──────│ PK id            │
│    name          │       │    name          │
│    description   │       │    slug          │
│    source_type   │       │    category      │
│    status        │       │    parameters    │
│    metadata      │       │    tier_required │
│    created_at    │       │    preview_url   │
│    updated_at    │       │    is_active     │
│    deleted_at    │       └──────────────────┘
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    │ 1:N     │ 1:N
    ▼         ▼
┌──────────────────┐    ┌──────────────────┐
│ design_versions  │    │      jobs        │
├──────────────────┤    ├──────────────────┤
│ PK id            │    │ PK id            │
│ FK design_id     │    │ FK design_id     │
│    version_num   │    │ FK user_id       │
│    file_url      │    │    type          │
│    thumbnail_url │    │    status        │
│    file_formats  │    │    priority      │
│    parameters    │    │    input_data    │
│    change_desc   │    │    output_data   │
│    created_at    │    │    progress      │
└──────────────────┘    │    error_message │
                        │    started_at    │
                        │    completed_at  │
                        │    created_at    │
                        └──────────────────┘

┌──────────────────┐    ┌──────────────────┐
│ design_shares    │    │  moderation_logs │
├──────────────────┤    ├──────────────────┤
│ PK id            │    │ PK id            │
│ FK design_id     │    │ FK user_id       │
│ FK shared_with   │    │ FK job_id        │
│    permission    │    │    content_type  │
│    token         │    │    input_text    │
│    expires_at    │    │    result        │
│    created_at    │    │    flags         │
└──────────────────┘    │    reviewed_by   │
                        │    created_at    │
                        └──────────────────┘
```

---

## 3. Table Definitions

### 3.1 Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user'
        CHECK (role IN ('user', 'admin', 'moderator')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending_verification'
        CHECK (status IN ('pending_verification', 'active', 'suspended', 'deleted')),
    email_verified_at TIMESTAMPTZ,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_status ON users(status) WHERE deleted_at IS NULL;

-- Triggers
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 3.2 Subscriptions Table

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tier VARCHAR(20) NOT NULL DEFAULT 'free'
        CHECK (tier IN ('free', 'pro', 'enterprise')),
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'past_due', 'canceled', 'expired')),
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_subscription UNIQUE (user_id)
);

-- Indexes
CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
```

### 3.3 User Settings Table

```sql
CREATE TABLE user_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferences JSONB NOT NULL DEFAULT '{
        "defaultUnits": "mm",
        "defaultExportFormat": "stl",
        "theme": "system",
        "language": "en"
    }'::jsonb,
    notifications JSONB NOT NULL DEFAULT '{
        "email": {
            "jobComplete": true,
            "weeklyDigest": true,
            "marketing": false
        },
        "push": {
            "jobComplete": true
        }
    }'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_user_settings UNIQUE (user_id)
);
```

### 3.4 Projects Table

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_projects_user ON projects(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_projects_created ON projects(created_at DESC) WHERE deleted_at IS NULL;
```

### 3.5 Templates Table

```sql
CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL
        CHECK (category IN ('mechanical', 'enclosures', 'connectors', 
                           'hardware', 'organizational', 'decorative', 'custom')),
    description TEXT,
    parameters JSONB NOT NULL,
    -- Example parameters structure:
    -- {
    --   "length": {"type": "number", "min": 1, "max": 1000, "default": 50, "unit": "mm"},
    --   "width": {"type": "number", "min": 1, "max": 500, "default": 30, "unit": "mm"},
    --   "style": {"type": "enum", "options": ["rounded", "chamfered", "sharp"], "default": "rounded"}
    -- }
    tier_required VARCHAR(20) NOT NULL DEFAULT 'free'
        CHECK (tier_required IN ('free', 'pro', 'enterprise')),
    preview_url VARCHAR(500),
    thumbnail_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    usage_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_templates_category ON templates(category) WHERE is_active = TRUE;
CREATE INDEX idx_templates_tier ON templates(tier_required) WHERE is_active = TRUE;
CREATE INDEX idx_templates_slug ON templates(slug);
```

### 3.6 Designs Table

```sql
CREATE TABLE designs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    template_id UUID REFERENCES templates(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_type VARCHAR(20) NOT NULL
        CHECK (source_type IN ('template', 'ai_generated', 'imported', 'modified')),
    status VARCHAR(20) NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'processing', 'ready', 'failed', 'archived')),
    current_version_id UUID,  -- Will be set after first version created
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Metadata structure:
    -- {
    --   "parameters": {...},
    --   "aiPrompt": "original user description",
    --   "dimensions": {"x": 100, "y": 50, "z": 30, "unit": "mm"},
    --   "volume": 150000,
    --   "surfaceArea": 23000,
    --   "isPrintable": true,
    --   "printEstimate": {"time": 3600, "material": 15.5}
    -- }
    tags TEXT[] DEFAULT '{}',
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    view_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_designs_project ON designs(project_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_designs_template ON designs(template_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_designs_status ON designs(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_designs_public ON designs(is_public, created_at DESC) 
    WHERE deleted_at IS NULL AND is_public = TRUE;
CREATE INDEX idx_designs_tags ON designs USING GIN(tags) WHERE deleted_at IS NULL;
CREATE INDEX idx_designs_metadata ON designs USING GIN(metadata jsonb_path_ops);

-- Add foreign key after design_versions table exists
-- ALTER TABLE designs ADD CONSTRAINT fk_current_version 
--     FOREIGN KEY (current_version_id) REFERENCES design_versions(id);
```

### 3.7 Design Versions Table

```sql
CREATE TABLE design_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    file_url VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    file_formats JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- File formats structure:
    -- {
    --   "step": "s3://bucket/path/design.step",
    --   "stl": "s3://bucket/path/design.stl",
    --   "3mf": "s3://bucket/path/design.3mf",
    --   "obj": "s3://bucket/path/design.obj"
    -- }
    parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
    geometry_info JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Geometry info structure:
    -- {
    --   "boundingBox": {"x": 100, "y": 50, "z": 30},
    --   "volume": 150000,
    --   "surfaceArea": 23000,
    --   "triangleCount": 12500,
    --   "isManifold": true
    -- }
    change_description TEXT,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT unique_design_version UNIQUE (design_id, version_number)
);

-- Indexes
CREATE INDEX idx_design_versions_design ON design_versions(design_id);
CREATE INDEX idx_design_versions_created ON design_versions(design_id, created_at DESC);
```

### 3.8 Jobs Table

```sql
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    design_id UUID REFERENCES designs(id) ON DELETE SET NULL,
    type VARCHAR(30) NOT NULL
        CHECK (type IN ('generate', 'modify', 'export', 'import', 'thumbnail')),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'queued', 'processing', 'completed', 
                         'failed', 'cancelled', 'timeout')),
    priority INTEGER NOT NULL DEFAULT 5
        CHECK (priority BETWEEN 1 AND 10),  -- 1 = highest
    queue_name VARCHAR(50) NOT NULL DEFAULT 'default',
    input_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- Input data structure varies by type:
    -- generate: {"description": "...", "templateId": "...", "parameters": {...}}
    -- modify: {"designId": "...", "modifications": {...}}
    -- export: {"designId": "...", "format": "stl", "options": {...}}
    output_data JSONB,
    -- Output data structure:
    -- {"fileUrl": "...", "thumbnailUrl": "...", "metadata": {...}}
    progress INTEGER NOT NULL DEFAULT 0
        CHECK (progress BETWEEN 0 AND 100),
    progress_message VARCHAR(255),
    error_message TEXT,
    error_code VARCHAR(50),
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    celery_task_id VARCHAR(255),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    timeout_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_jobs_user ON jobs(user_id);
CREATE INDEX idx_jobs_design ON jobs(design_id);
CREATE INDEX idx_jobs_status ON jobs(status, priority, created_at);
CREATE INDEX idx_jobs_queue ON jobs(queue_name, status, priority, created_at)
    WHERE status IN ('pending', 'queued');
CREATE INDEX idx_jobs_celery ON jobs(celery_task_id);
CREATE INDEX idx_jobs_created ON jobs(created_at DESC);

-- Partial index for active jobs monitoring
CREATE INDEX idx_jobs_active ON jobs(user_id, status, created_at)
    WHERE status IN ('pending', 'queued', 'processing');
```

### 3.9 Design Shares Table

```sql
CREATE TABLE design_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    design_id UUID NOT NULL REFERENCES designs(id) ON DELETE CASCADE,
    shared_with_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    shared_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission VARCHAR(20) NOT NULL DEFAULT 'view'
        CHECK (permission IN ('view', 'comment', 'edit', 'admin')),
    share_token VARCHAR(64) UNIQUE,  -- For link-based sharing
    is_link_share BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash VARCHAR(255),  -- Optional password for link shares
    expires_at TIMESTAMPTZ,
    accessed_at TIMESTAMPTZ,
    access_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT share_type_check CHECK (
        (shared_with_user_id IS NOT NULL AND share_token IS NULL) OR
        (shared_with_user_id IS NULL AND share_token IS NOT NULL)
    )
);

-- Indexes
CREATE INDEX idx_shares_design ON design_shares(design_id);
CREATE INDEX idx_shares_user ON design_shares(shared_with_user_id);
CREATE INDEX idx_shares_token ON design_shares(share_token) WHERE share_token IS NOT NULL;
```

### 3.10 Moderation Logs Table

```sql
CREATE TABLE moderation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    job_id UUID REFERENCES jobs(id) ON DELETE SET NULL,
    content_type VARCHAR(30) NOT NULL
        CHECK (content_type IN ('text_input', 'file_upload', 'design_output', 
                                'user_profile', 'comment')),
    input_text TEXT,
    input_hash VARCHAR(64),  -- SHA-256 for deduplication
    result VARCHAR(20) NOT NULL
        CHECK (result IN ('approved', 'rejected', 'flagged', 'pending_review')),
    confidence_score DECIMAL(4,3),  -- 0.000 to 1.000
    flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Flags structure:
    -- [
    --   {"category": "weapons", "confidence": 0.95, "details": "..."},
    --   {"category": "inappropriate", "confidence": 0.3, "details": "..."}
    -- ]
    model_version VARCHAR(50),
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_notes TEXT,
    appeal_status VARCHAR(20)
        CHECK (appeal_status IN ('none', 'pending', 'approved', 'denied')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_moderation_user ON moderation_logs(user_id);
CREATE INDEX idx_moderation_result ON moderation_logs(result, created_at DESC);
CREATE INDEX idx_moderation_review ON moderation_logs(result, reviewed_by)
    WHERE result = 'flagged' AND reviewed_at IS NULL;
CREATE INDEX idx_moderation_hash ON moderation_logs(input_hash);
```

### 3.11 API Keys Table (for Enterprise)

```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,  -- bcrypt hash of the key
    key_prefix VARCHAR(8) NOT NULL,  -- First 8 chars for identification
    scopes TEXT[] NOT NULL DEFAULT '{read}'::text[],
    rate_limit_per_minute INTEGER NOT NULL DEFAULT 60,
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_api_keys_user ON api_keys(user_id) WHERE is_active = TRUE;
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix) WHERE is_active = TRUE;
```

### 3.12 Audit Logs Table

```sql
CREATE TABLE audit.logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Partitioning by month for performance
-- CREATE TABLE audit.logs_2024_01 PARTITION OF audit.logs
--     FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

-- Indexes
CREATE INDEX idx_audit_user ON audit.logs(user_id, created_at DESC);
CREATE INDEX idx_audit_entity ON audit.logs(entity_type, entity_id, created_at DESC);
CREATE INDEX idx_audit_action ON audit.logs(action, created_at DESC);
```

---

## 4. Indexes

### 4.1 Index Summary

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| users | idx_users_email | B-tree | Login lookup |
| designs | idx_designs_metadata | GIN | JSONB queries |
| designs | idx_designs_tags | GIN | Tag filtering |
| jobs | idx_jobs_queue | B-tree (partial) | Queue processing |
| moderation_logs | idx_moderation_hash | B-tree | Duplicate detection |

### 4.2 Full-Text Search Index

```sql
-- Add full-text search for designs
ALTER TABLE designs ADD COLUMN search_vector tsvector;

CREATE INDEX idx_designs_search ON designs USING GIN(search_vector);

-- Update trigger for search vector
CREATE OR REPLACE FUNCTION update_design_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(array_to_string(NEW.tags, ' '), '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_design_search
    BEFORE INSERT OR UPDATE OF name, description, tags ON designs
    FOR EACH ROW EXECUTE FUNCTION update_design_search_vector();
```

---

## 5. Migrations Strategy

### 5.1 Migration Tooling
- **Tool**: Alembic (Python/SQLAlchemy)
- **Naming**: `YYYYMMDD_HHMMSS_description.py`
- **Environments**: development, staging, production

### 5.2 Migration Workflow

```bash
# Create new migration
alembic revision --autogenerate -m "add_column_to_users"

# Review and edit generated migration
# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View migration history
alembic history
```

### 5.3 Migration Best Practices

1. **Always include rollback**: Every `upgrade()` must have a `downgrade()`
2. **Small, atomic changes**: One logical change per migration
3. **Non-blocking operations**: Use `CONCURRENTLY` for index creation in production
4. **Data migrations separate**: Keep schema and data migrations separate
5. **Test both directions**: Test upgrade AND downgrade before production

### 5.4 Initial Migration

```python
# migrations/versions/20240124_000001_initial_schema.py
"""Initial schema creation

Revision ID: 001
Create Date: 2024-01-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create updated_at trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # Create audit schema
    op.execute("CREATE SCHEMA IF NOT EXISTS audit;")
    
    # Create tables in dependency order
    # 1. users
    # 2. subscriptions, user_settings, projects, templates
    # 3. designs
    # 4. design_versions, jobs, design_shares, moderation_logs
    # 5. api_keys, audit.logs
    
    # ... (full table creation SQL)

def downgrade():
    # Drop in reverse order
    op.execute("DROP SCHEMA IF EXISTS audit CASCADE;")
    # ... (full table drops)
```

---

## Appendix A: Common Queries

### A.1 Get User's Designs with Latest Version
```sql
SELECT 
    d.id,
    d.name,
    d.status,
    dv.thumbnail_url,
    dv.version_number as current_version,
    d.created_at
FROM designs d
LEFT JOIN design_versions dv ON dv.id = d.current_version_id
JOIN projects p ON p.id = d.project_id
WHERE p.user_id = :user_id
    AND d.deleted_at IS NULL
ORDER BY d.updated_at DESC
LIMIT 20 OFFSET 0;
```

### A.2 Get Pending Jobs for Queue Processing
```sql
SELECT 
    j.id,
    j.type,
    j.priority,
    j.input_data,
    u.id as user_id,
    s.tier
FROM jobs j
JOIN users u ON u.id = j.user_id
LEFT JOIN subscriptions s ON s.user_id = u.id
WHERE j.queue_name = :queue_name
    AND j.status = 'pending'
ORDER BY j.priority ASC, j.created_at ASC
LIMIT 10
FOR UPDATE SKIP LOCKED;
```

### A.3 Design Search with Full-Text
```sql
SELECT 
    d.id,
    d.name,
    d.description,
    ts_rank(d.search_vector, query) as rank
FROM designs d,
    plainto_tsquery('english', :search_term) query
WHERE d.search_vector @@ query
    AND d.is_public = TRUE
    AND d.deleted_at IS NULL
ORDER BY rank DESC
LIMIT 20;
```

---

*End of Document*
